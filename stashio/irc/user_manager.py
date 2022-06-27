class UserRoles():
    def __init__(self, in_privmsg_packet):
        self.update_roles(in_privmsg_packet)
        
    def __repr__(self):
        return str({"Mod": self.__is_mod, "VIP": self.__is_vip, "Sub": self.__is_subscriber, "Broadcaster": self.__is_broadcaster})
        
    def update_roles(self, in_privmsg_packet):
        self.__is_mod = in_privmsg_packet.is_mod
        self.__is_vip = in_privmsg_packet.is_vip
        self.__is_subscriber = in_privmsg_packet.is_vip
        self.__is_broadcaster = in_privmsg_packet.is_broadcaster
        
    @property
    def is_mod(self):
        return self.__is_mod
        
    @property
    def is_vip(self):
        return self.__is_vip
        
    @property
    def is_subscriber(self):
        return self.__is_subscriber
        
    @property
    def is_broadcaster(self):
        return self.__is_broadcaster

class User():
    def __init__(self, in_privmsg_packet):
        self.__role_cache = dict()
        self.__name = in_privmsg_packet.name
        self.__display_name = in_privmsg_packet.display_name
        self.__user_id = in_privmsg_packet.user_id
        self.update_user_data(in_privmsg_packet)
        
    def __repr__(self):
        return str({"Role": str(self.__role_cache), "Name": self.__name, "Display Name": self.__display_name, "User ID": self.__user_id})
        
    def update_user_data(self, in_privmsg_packet):
        current_channel_id = in_privmsg_packet.channel_id
        if not current_channel_id in self.__role_cache:
            self.__role_cache[current_channel_id] = UserRoles(in_privmsg_packet)
        
        self.__role_cache[current_channel_id].update_roles(in_privmsg_packet)

    @property
    def name(self):
        return self.__name

    @property
    def display_name(self):
        return self.__display_name
        
    @property
    def is_mod(self, in_channel_object):
        return in_channel_object.channel_id in self.__role_cache and self.__role_cache[in_channel_object.channel_id].is_mod
        
    @property
    def is_subscriber(self, in_channel_object):
        return in_channel_object.channel_id in self.__role_cache and self.__role_cache[in_channel_object.channel_id].is_subscriber
        
    @property
    def is_vip(self, in_channel_object):
        return in_channel_object.channel_id in self.__role_cache and self.__role_cache[in_channel_object.channel_id].is_vip
        
    @property
    def is_broadcaster(self, in_channel_object):
        return in_channel_object.channel_id in self.__role_cache and self.__role_cache[in_channel_object.channel_id].is_broadcaster

class UserManager():
    def __init__(self):
        self.__user_cache = dict()
        
    def __repr__(self):
        return str(self.__user_cache)
        
    def __add_or_find_user(self, in_privmsg_data):
        user_id = in_privmsg_data.user_id
        if not user_id in self.__user_cache:
            self.__user_cache[user_id] = User(in_privmsg_data)
        return self.__user_cache[user_id]
        
    async def set_user_data(self, in_privmsg_data):
        user = self.__add_or_find_user(in_privmsg_data)
        user.update_user_data(in_privmsg_data)
        
    async def get_user(self, in_user_id):
        return self.__user_cache[in_user_id] if in_user_id in self.__user_cache else None
        