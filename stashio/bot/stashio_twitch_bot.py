import websockets
import asyncio
import aiohttp
from stashio.utils.auth import Auth
from stashio.irc.channel_manager import ChannelManager
from stashio.irc.user_manager import UserManager
from stashio.irc.irc import IRCData, IRCPackets
from stashio.irc.types import TwitchMessage
from stashio.utils.data import TimedCountQueue, TimedCountDataQueue
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
        self.__send_data = []
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
        
    async def stop(self):
        self.__manual_shutdown_requested = True
        
    async def run(self):
        # task to process the data we read from the socket
        self.__loop.create_task(self.process_recv_data())
        # task to process the data we want to send over the socket
        self.__loop.create_task(self.process_send_data())
        
        while not self.__manual_shutdown_requested:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.__server) as websocket:
                    self.__ws = websocket
                    await self.__ws.send_str(f"CAP REQ :twitch.tv/commands twitch.tv/tags twitch.tv/membership")
                    await self.__ws.send_str(f"PASS {self.__auth.get_irc_token()}")
                    await self.__ws.send_str(f"NICK {self.__auth.get_user()}")
                    async for rec in websocket:
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
                            
                        if self.__manual_shutdown_requested:
                            break
                    if self.__manual_shutdown_requested:
                        break

    async def process_recv_data(self):
        while not self.__manual_shutdown_requested:
            if len(self.__data) > 0:
                messages = self.__data.split('\r\n')
                # if the last message doesn't end in \r\n, we might not have all the data, so we need to put that back to check later
                # if it does end in it, the last message will be empty anyway, so we'll be clearing __data
                self.__data = messages[-1]
                for i in range(len(messages) - 1):
                    m = IRCData(messages[i])
                    await self.process_irc_packet(m)
            await asyncio.sleep(0.01)
            
    async def process_send_data(self):
        wait_queue = []
        msg_rate_queue = TimedCountDataQueue()
        join_rate_queue = TimedCountQueue()
        
        global_privmsg_rates = self.__get_global_privmsg_rate_limits()
        join_rates = self.__get_join_rate_limits(self.__verified)
        
        while not self.__manual_shutdown_requested:
            try:
                items_to_check = wait_queue + self.__send_data
                self.__send_data = []
                wait_queue = []
                out = []
                
                for item in items_to_check:
                    # TODO: Need to finish message rate stuff
                    #if item.queue_type() == IRCPackets.QueueType.PRIVMSG:
                    #    global_count = msg_rate_queue.get_count()
                    #    
                    #    if global_count >= global_privmsg_rates["amount"]:
                    #        wait_queue.append(item)
                    #        continue
                    #    channel_count = msg_rate_queue.get_count(item.channel)
                    #    
                    #    #if channel_count >= __get_privmsg_rate_limits
                    out.append(item.get())
                    
                for p in out:
                    await self.__ws.send_str(p)
                            
            except aiohttp.ClientDisconnectedError:
                continue
            await asyncio.sleep(0.01)
            
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
            await self.__channel_manager.set_channel_user_state(message)
        elif message.command == "ROOMSTATE":
            await self.__channel_manager.set_channel_room_state(message)
        elif message.command == "NOTICE":
            await self.event_notice(message.channel, message.content)
            
    async def __message_reply_callback(self, in_message_id, in_channel, in_message):
        self.__send_data.append(IRCPackets.Message(in_channel, in_message, in_message_id))
        
    async def __message_send_callback(self, in_channel, in_message):
        self.__send_data.append(IRCPackets.Message(in_channel, in_message))

    async def join_channels(self, channels):
        for channel in channels:
            self.__send_data.append(IRCPackets.Join(channel))
            
    async def leave_channels(self, channels):
        for channel in channels:
            self.__send_data.append(IRCPackets.Part(channel))
    
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
    async def event_roomstate(self, channel, state):
        pass
        
    # This event gets called with some state about a user in a channel
    async def event_userstate(self, channel, user, state):
        pass
        
    # This event gets called with a notice message for a channel
    async def event_notice(self, channel, notice):
        pass
        
    # This event gets called when twitch is going to go down for maintenance
    async def event_reconnect(self):
        pass