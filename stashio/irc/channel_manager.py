
class RoomState():
    def __init__(self, in_room_state_packet):
        self.update_state(in_room_state_packet)
        
    def __repr__(self):
        return "Room State (" + self.channel + "):\n  channel_id: " + str(self.channel_id) + "\n  is_emote_only:" + str(self.is_emote_only) + "\n  is_followers_only:" + str(self.is_followers_only) + "\n  slow_mode:" + str(self.slow_mode) + "\n  is_subs_only:" + str(self.is_subs_only)
        
    def update_state(self, in_room_state_packet):
        if in_room_state_packet.channel:
            self.__channel = in_room_state_packet.channel
        if in_room_state_packet.channel_id:
            self.__channel_id = in_room_state_packet.channel_id
        if "emote-only" in in_room_state_packet.message:
            self.__is_emote_only = in_room_state_packet.message["emote-only"] == '1'
        if "followers-only" in in_room_state_packet.message:
            self.__is_followers_only = in_room_state_packet.message["followers-only"] == '1'
        if "slow" in in_room_state_packet.message:
            self.__slow_mode = int(in_room_state_packet.message["slow"])
        if "subs-only" in in_room_state_packet.message:
            self.__is_subs_only = in_room_state_packet.message["subs-only"] == '1'
        
    @property
    def channel(self):
        return self.__channel
        
    @property
    def channel_id(self):
        return self.__channel_id
        
    @property
    def is_emote_only(self):
        return self.__is_emote_only
        
    @property
    def is_followers_only(self):
        return self.__is_followers_only
        
    @property
    def slow_mode(self):
        return self.__slow_mode
        
    @property
    def is_subs_only(self):
        return self.__is_subs_only

class UserState():
    def __init__(self, in_user_state_packet):
        self.update_state(in_user_state_packet)
        
    def __repr__(self):
        return "User State (" + self.channel + "):\n  is_mod: " + str(self.is_mod) + "\n  is_subscriber:" + str(self.is_subscriber)
        
    def update_state(self, in_user_state_packet):
        if in_user_state_packet.channel:
            self.__channel = in_user_state_packet.channel
        if in_user_state_packet.badges:
            self.__badges = in_user_state_packet.badges
        self.__is_mod = in_user_state_packet.is_mod
        self.__is_subscriber = in_user_state_packet.is_subscriber

    @property
    def is_mod(self):
        return self.__is_mod
    
    @property
    def is_subscriber(self):
        return self.__is_subscriber
    
    @property
    def channel(self):
        return self.__channel
        
    @property
    def badges(self):
        return self.__badges
        
class Channel():
    def __init__(self, in_channel_id, in_send_callback):
        self.__channel_id = in_channel_id
        self.__send_callback = in_send_callback
        self.__user_state = None
        self.__room_state = None
        
    def __repr__(self):
        return str(self.__user_state) + "\n" + str(self.__room_state)
        
    def update_user_state(self, in_user_state):
        if not self.__user_state:
            self.__user_state = UserState(in_user_state)
        else:
            self.__user_state.update_state(in_user_state)
        return self
        
    def update_room_state(self, in_room_state):
        if not self.__room_state:
            self.__room_state = RoomState(in_room_state)
        else:
            self.__room_state.update_state(in_room_state)
        return self
        
    async def send(self, in_message, in_delay = 0):
        await self.__send_callback(self, in_message, in_delay)
        
    @property
    def name(self):
        if self.__room_state:
            return self.__room_state.channel
        if self.__user_state:
            return self.__user_state.channel
        return None
        
    @property
    def is_mod(self):
        return self.__user_state.is_mod if self.__user_state else False
        
    @property
    def is_subscriber(self):
        return self.__user_state.is_subscriber if self.__user_state else False
        
    @property
    def badges(self):
        return self.__user_state.badges if self.__user_state else None
        
    @property
    def channel_id(self):
        return self.__room_state.channel_id if self.__room_state else 0
        
    @property
    def is_emote_only(self):
        return self.__room_state.is_emote_only if self.__room_state else False
        
    @property
    def is_followers_only(self):
        return self.__room_state.is_followers_only if self.__room_state else False
        
    @property
    def slow_mode(self):
        return self.__room_state.slow_mode if self.__room_state else False
        
    @property
    def is_subs_only(self):
        return self.__room_state.is_subs_only if self.__room_state else False

class ChannelManager():
    def __init__(self, in_send_callback):
        self.__channel_cache = dict()
        self.__send_callback = in_send_callback
        
    def __add_or_find_channel(self, in_channel_id):
        if not in_channel_id in self.__channel_cache:
            self.__channel_cache[in_channel_id] = Channel(in_channel_id, self.__send_callback)
        return self.__channel_cache[in_channel_id]
        
    async def set_channel_user_state(self, in_user_state):
        chan = self.__add_or_find_channel(in_user_state.channel_id)
        return chan.update_user_state(in_user_state)
        
    async def set_channel_room_state(self, in_room_state):
        chan = self.__add_or_find_channel(in_room_state.channel_id)
        return chan.update_room_state(in_room_state)
        
    async def get_channel(self, in_channel_id):
        return self.__channel_cache[in_channel_id] if in_channel_id in self.__channel_cache else None

    def is_mod(self, in_channel_id):
        return self.__channel_cache[in_channel_id].is_mod if in_channel_id in self.__channel_cache else False
