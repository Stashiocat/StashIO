import websockets
import asyncio
import aiohttp
import datetime
import traceback
from stashio.utils.auth import Auth
from stashio.irc.channel_manager import ChannelManager
from stashio.irc.user_manager import UserManager
from stashio.irc.irc import IRCData, IRCPackets
from stashio.irc.types import TwitchMessage
from stashio.utils.data import DelayQueue, TimedCountQueue, TimedCountDataQueue
from stashio.twitch.api import TwitchApi

class StashioTwitchBot():
    def __init__(self, in_auth, in_verified=False, in_server='wss://irc-ws.chat.twitch.tv:443'):
        # the irc server to connect to
        self.__server = in_server
        # whether or not this is a verified bot
        self.__verified = in_verified
        # the current active socket
        self.__ws = None
        # the data we've read with recv() but haven't processed yet
        self.__data = ""
        # the data we want to send out but haven't processed yet
        self.__send_data = DelayQueue()
        # auth data
        self.__auth = Auth(in_auth)
        # flag that will let our fibers stop
        self.__manual_shutdown_requested = False
        # asyncio event loop
        self.__loop = asyncio.get_event_loop()
        # object for interacting with the Twitch API
        self.__api = TwitchApi(self.__auth)
        # manages channel objects that contain info about the channel and the bot's roles in the channel
        self.__channel_manager = ChannelManager(self.__message_send_callback)
        # manages user objects that contain info about the user and its roles in channels
        self.__user_manager = UserManager()
        # force the socket to close and connect to IRC again
        self.__force_irc_reconnect = False
    
    @property
    def user(self):
        return self.__auth.get_user()
    
    def __get_join_rate_limits(self, is_verified=False):
        if is_verified:
            return { "amount": 2000, "seconds": 11 }
        return { "amount": 20, "seconds": 11 }
    
    def __get_global_privmsg_rate_limits(self):
        return { "amount": 7500, "seconds": 31 }
    
    def __get_privmsg_rate_limits(self, is_mod=False, is_verified=False):
        if is_verified:
            if is_mod:
                return { "amount": 1000, "seconds": 31 }
            return { "amount": 20, "seconds": 31 }
        elif is_mod:
            return { "amount": 100, "seconds": 31 }
        return { "amount": 20, "seconds": 31 }
        
    async def RefreshIRCAccessToken(self):
        await self.__api.RefreshIRCAccessToken()
        self.__force_irc_reconnect = True
        
    async def stop(self):
        self.__manual_shutdown_requested = True
        
    async def run(self):
        # task to process the data we read from the socket
        self.__loop.create_task(self.process_recv_data())
        # task to process the data we want to send over the socket
        self.__loop.create_task(self.process_send_data())
        
        while not self.__manual_shutdown_requested:
            async with aiohttp.ClientSession(read_timeout=1) as session:
                try:
                    async with session.ws_connect(self.__server) as websocket:
                        self.__ws = websocket
                        await self.__ws.send_str(f"CAP REQ :twitch.tv/commands twitch.tv/tags")
                        await self.__ws.send_str(f"PASS {self.__auth.get_irc_token()}")
                        await self.__ws.send_str(f"NICK {self.__auth.get_user()}")
                        async for rec in websocket:
                            now = datetime.datetime.now()
                            timestamp = now.strftime("%m/%d/%Y %H:%M:%S")
                            if rec.type == aiohttp.WSMsgType.TEXT:
                                self.__data += rec.data
                            elif rec.type == aiohttp.WSMsgType.ERROR:
                                print("Received error")
                                break
                            else:
                                print("========================")
                                print("Unexpected data type:",rec.type)
                                print(rec.data)
                                print("========================")
                                
                            if self.__force_irc_reconnect:
                                self.__force_irc_reconnect = False
                                continue
                                
                            if self.__manual_shutdown_requested:
                                break
                        if self.__manual_shutdown_requested:
                            break
                except aiohttp.ClientConnectorError:
                    print("Failed to connect, trying again.")
                    await asyncio.sleep(5)

    async def is_follower_only(self, user_obj):
        settings = await self.__api.GetChannelSettings(user_obj.channel_id)
        return 'follower_mode' in settings and settings['follower_mode']
        
    async def get_live_streams(self, in_users):
        results = await self.__api.GetStreamsInfo(in_users)
        live = []
        for res in results:
            live.append(res['user_login'])
        return live
        
    async def get_user_info(self, users):
        results = await self.__api.GetUsers(users)
        return results
        
    async def get_follower_count(self, user):
        return await self.__api.GetFollowerCount(user)
        
    async def process_recv_data(self):
        while not self.__manual_shutdown_requested:
            if len(self.__data) > 0:
                messages = self.__data.split('\r\n')
                # if the last message doesn't end in \r\n, we might not have all the data, so we need to put that back to check later
                # if it does end in it, the last message will be empty anyway, so we'll be clearing __data
                self.__data = messages[-1]
                for i in range(len(messages) - 1):
                    try:
                        m = IRCData(messages[i])
                    except Exception as e:
                        print("==================================")
                        print("EXCEPTION CREATING IRC DATA!")
                        print("Exception:",str(e))
                        print("Message:",messages[i])
                        print("==================================")
                        
                    try:
                        #await self.process_irc_packet(m)
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.process_irc_packet(m))
                    except Exception as e:
                        print("==================================")
                        print("EXCEPTION PROCESSING IRC PACKET!")
                        print("Exception:",str(e))
                        print("Message:",messages[i])
                        print("Message object:",m)
                        print("==================================")
                        
            await asyncio.sleep(0)
            
    async def process_send_data(self):
        wait_queue = []
        msg_rate_queue = TimedCountDataQueue()
        join_rate_queue = TimedCountQueue()
        
        global_privmsg_rates = self.__get_global_privmsg_rate_limits()
        join_rates = self.__get_join_rate_limits(self.__verified)
        
        while not self.__manual_shutdown_requested:
            try:
                data = self.__send_data.pop()
                if len(data) > 0:
                    items_to_check = wait_queue + data
                    wait_queue = []
                    out = []
                    
                    for item in items_to_check:
                        #if item.queue_type() == IRCPackets.QueueType.PRIVMSG:
                        #    global_count = msg_rate_queue.get_count()
                        #    
                        #    if global_count >= global_privmsg_rates["amount"]:
                        #        wait_queue.append(item)
                        #        continue
                        #    channel_count = msg_rate_queue.get_count(item.channel)
                        #    
                        #    #if channel_count >= __get_privmsg_rate_limits
                        i = item.get()
                        out.append(item.get())
                        
                    for p in out:
                        await self.__ws.send_str(p)
                        await asyncio.sleep(0)
                            
            except aiohttp.ClientDisconnectedError:
                continue
                
            await asyncio.sleep(0)
    
    async def process_irc_packet(self, message):
        if message.command == "001":
            await self.event_authenticated()
        elif message.command == "PING":
            await self.__ws.send_str(f"PONG :{message.content}")
        elif message.command == "PRIVMSG":
            await self.__user_manager.set_user_data(message)
            user = await self.__user_manager.get_user(message.user_id)
            channel = await self.__channel_manager.get_channel(message.channel_id)
            await self.event_message(TwitchMessage(channel, user, message, self.__message_reply_callback))
        elif message.command == "JOIN":
            # TODO: Right now joins only give a channel name, so need a lookup by name for user and channel
            #await self.event_join(TwitchChannel(message))
            pass
        elif message.command == "USERSTATE":
            updated_channel = await self.__channel_manager.set_channel_user_state(message)
            await self.event_userstate(updated_channel)
        elif message.command == "ROOMSTATE":
            updated_channel = await self.__channel_manager.set_channel_room_state(message)
            await self.event_roomstate(updated_channel)
        elif message.command == "NOTICE":
            await self.event_notice(message.channel, message.content)
            
    async def __message_reply_callback(self, in_message_id, in_channel, in_message, in_delay = 0):
        self.__send_data.add(IRCPackets.Message(in_channel, in_message, in_message_id), in_delay)
        
    async def __message_send_callback(self, in_channel, in_message, in_delay = 0):
        self.__send_data.add(IRCPackets.Message(in_channel, in_message), in_delay)

    async def join_channels(self, channels):
        try:
            for channel in channels:
                self.__send_data.add(IRCPackets.Join(channel), 0)
        except Exception as e:
            traceback.print_exc()
            
    async def leave_channels(self, channels):
        for channel in channels:
            self.__send_data.add(IRCPackets.Part(channel), 0)
    
    ##################################################################################
    ## Overridable interfaces
    ##################################################################################
    # This event gets called when a message is posted in the channel
    async def event_message(self, message):
        pass
        
    # This event gets called when the bot successfully authenticates to twitch
    async def event_authenticated(self):
        pass
        
    # This event gets called when a user joins the channel
    async def event_join(self, channel, user):
        pass
        
    # This event gets called when a user leaves the channel
    async def event_part(self, channel, user):
        pass
        
    # This event gets called when the state of a room gets changed (emote only, sub only, etc)
    async def event_roomstate(self, updated_channel):
        pass
        
    # This event gets called when we have a USERSTATE message. Contains info about roles and badges in the channel.
    async def event_userstate(self, updated_channel):
        pass
        
    # This event gets called with a notice message for a channel
    async def event_notice(self, channel, notice):
        pass
        
    # This event gets called when twitch is going to go down for maintenance
    async def event_reconnect(self):
        pass
