import asyncio
import traceback
from stashio.irc.irc import IRC
from stashio.utils.auth import Auth
from stashio.utils.data import DelayQueue, TimedCountQueue, TimedCountDataQueue
from stashio.twitch.api import TwitchApi
from stashio.twitch.users import UserBank
from stashio.twitch.eventsub.eventsub import EventSubConnection
import stashio.twitch.eventsub.types as EventSubTypes

class EventSubSubscriptions():
    ChannelPointRedemption = EventSubTypes.EventSub_ChannelPointRedemption
    ChannelChatMessage = EventSubTypes.EventSub_ChannelChatMessage

class StashioTwitchBot():
    def __init__(self, in_auth, in_use_irc=False):
        # auth data
        self.__auth = Auth(in_auth)
        # flag that will let our fibers stop
        self.__manual_shutdown_requested = False
        # asyncio event loop
        self.__loop = asyncio.get_event_loop()
        # object for interacting with the Twitch API
        self.__api = TwitchApi(self.__auth)
        # conversion between twitch username <==> channel id
        self.__user_bank = UserBank(self.__api)
        # object that is managing the eventsub connection
        self.__eventsub = EventSubConnection(in_twitch_api=self.__api)
        # object that is managing the irc connection
        self.__irc = IRC(in_bot=self, in_auth=self.__auth, in_twitch_api=self.__api) if in_use_irc else None
    
    @property
    def user(self):
        return self.__auth.get_user()
        
    async def RefreshIRCAccessToken(self):
        await self.__irc.RefreshIRCAccessToken()
        
    async def channel_subscribe(self, in_channel_name, subscriptions_and_callbacks):
        id = await self.__get_channel_id(in_channel_name)
        if id:
            await self.__eventsub.channel_subscribe(id, subscriptions_and_callbacks)
    
    async def __get_channel_id(self, in_username):
        return await self.__user_bank.get_channel_id(in_username)
        
    async def stop(self):
        self.__manual_shutdown_requested = True
        await self.__eventsub.stop()
        if self.__irc:
            await self.__irc.stop()
        
    async def run(self):
        # task to process eventsub websocket data
        self.__loop.create_task(self.eventsub_loop())
        
        # task to process the irc connection
        if self.__irc:
            self.__loop.create_task(self.irc_loop())
        
        await self.event_initialize()
        
        while not self.__manual_shutdown_requested:
            await asyncio.sleep(0)
        
    async def eventsub_loop(self):
        while not self.__manual_shutdown_requested:
            await self.__eventsub.run()
        
    async def irc_loop(self):
        while not self.__manual_shutdown_requested:
            await self.__irc.run()

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

    async def join_channels(self, channels):
        await self.__irc.join_channels(channels)
            
    async def leave_channels(self, channels):
        await self.__irc.leave_channels(channels)
    
    ##################################################################################
    ## Overridable interfaces
    ##################################################################################
    # Run initialization
    async def event_initialize(self):
        pass
        
    # This event gets called when a message is posted in the channel
    async def event_irc_message(self, message):
        pass
        
    # This event gets called when the bot successfully authenticates to twitch
    async def event_irc_connected(self):
        pass
        
    # This event gets called when a user joins the channel
    async def event_irc_join(self, channel, user):
        pass
        
    # This event gets called when a user leaves the channel
    async def event_irc_part(self, channel, user):
        pass
        
    # This event gets called when the state of a room gets changed (emote only, sub only, etc)
    async def event_irc_roomstate(self, updated_channel):
        pass
        
    # This event gets called when we have a USERSTATE message. Contains info about roles and badges in the channel.
    async def event_irc_userstate(self, updated_channel):
        pass
        
    # This event gets called with a notice message for a channel
    async def event_irc_notice(self, channel, notice):
        pass
        
    # This event gets called when twitch is going to go down for maintenance
    async def event_irc_reconnect(self):
        pass
