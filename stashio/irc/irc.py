import asyncio
import traceback
from stashio.utils.auth import Auth
from stashio.irc.channel_manager import ChannelManager
from stashio.irc.user_manager import UserManager
from stashio.irc.types import TwitchMessage, IRCData, IRCPackets
from stashio.connection.wss_connection import BaseConnection
from stashio.twitch.api import TwitchApi

class IRC(BaseConnection):
    def __init__(self, in_bot, in_auth, in_twitch_api: TwitchApi, in_server='wss://irc-ws.chat.twitch.tv:443'):
        super().__init__(in_server)
        # auth data
        self.__auth = in_auth
        # twitch api interface
        self.__api = in_twitch_api
        # manages user objects that contain info about the user and its roles in channels
        self.__user_manager = UserManager()
        # manages channel objects that contain info about the channel and the bot's roles in the channel
        self.__channel_manager = ChannelManager(self.__message_send_callback)
        # asyncio event loop
        self.__loop = asyncio.get_event_loop()
        # the bot, for calling events
        self.__bot = in_bot
        
    #############################################################
    ## Start BaseConnection overrides
    #############################################################        
    async def on_connect(self):
        await self.send(f"CAP REQ :twitch.tv/commands twitch.tv/tags")
        await self.send(f"PASS {self.__auth.get_irc_token()}")
        await asyncio.sleep(0.1)
        await self.send(f"NICK {self.__auth.get_user()}")
        
    async def on_receive(self, data):
        try:
            m = IRCData(data)
        except Exception as e:
            print("==================================")
            print("EXCEPTION CREATING IRC DATA!")
            print("Exception:",str(e))
            print("Message:",data)
            print("==================================")
            
        try:
            #await self.process_irc_packet(m)
            self.__loop.create_task(self.process_irc_packet(m))
        except Exception as e:
            print("==================================")
            print("EXCEPTION PROCESSING IRC PACKET!")
            print("Exception:",str(e))
            print("Message:",data)
            print("Message object:",m)
            print("==================================")
            
    #############################################################
    ## End BaseConnection overrides
    #############################################################

    async def process_irc_packet(self, message):
        if message.command == "001":
            await self.__bot.event_irc_connected()
        elif message.command == "PING":
            await self.send(f"PONG :{message.content}")
        elif message.command == "PRIVMSG":
            await self.__user_manager.set_user_data(message)
            user = await self.__user_manager.get_user(message.user_id)
            channel = await self.__channel_manager.get_channel(message.channel_id)
            await self.__bot.event_irc_message(TwitchMessage(channel, user, message, self.__message_reply_callback))
        elif message.command == "JOIN":
            # TODO: Right now joins only give a channel name, so need a lookup by name for user and channel
            #await self.event_irc_join(TwitchChannel(message))
            pass
        elif message.command == "USERSTATE":
            updated_channel = await self.__channel_manager.set_channel_user_state(message)
            await self.__bot.event_irc_userstate(updated_channel)
        elif message.command == "ROOMSTATE":
            updated_channel = await self.__channel_manager.set_channel_room_state(message)
            await self.__bot.event_irc_roomstate(updated_channel)
        elif message.command == "NOTICE":
            await self.__bot.event_irc_notice(message.channel, message.content)
            
    async def __message_reply_callback(self, in_message_id, in_channel, in_message, in_delay = 0):
        await self.send(IRCPackets.Message(in_channel, in_message, in_message_id).get(), in_delay)
        
    async def __message_send_callback(self, in_channel, in_message, in_delay = 0):
        await self.send(IRCPackets.Message(in_channel, in_message).get(), in_delay)

    async def join_channels(self, channels):
        try:
            for channel in channels:
                await self.send(IRCPackets.Join(channel).get(), 0)
        except Exception as e:
            traceback.print_exc()
            
    async def leave_channels(self, channels):
        for channel in channels:
            await self.send(IRCPackets.Part(channel).get(), 0)
        
    async def RefreshIRCAccessToken(self):
        await self.__api.RefreshIRCAccessToken()
        await self.force_reconnect()