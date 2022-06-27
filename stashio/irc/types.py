
class User():
    def __init__(self, in_id, in_nick, in_display_name):
        self.__id = in_id
        self.__nick = in_nick
        self.__display_name = in_display_name
        
    @property
    def nick(self):
        return self.__nick
        
    @property
    def display_name(self):
        return self.__display_name
        
    @property
    def id(self):
        return self.__id

class TwitchMessage():
    def __init__(self, in_channel, in_user, in_irc_data, in_reply_callback=None):
        self.__channel = in_channel
        self.__user = in_user
        self.__badge_data = in_irc_data.badges
        self.__color = in_irc_data.message["color"]
        self.__content = in_irc_data.message["content"]
        self.__emote_data = in_irc_data.message["emotes"]
        self.__first_msg = in_irc_data.message["first-msg"]
        self.__message_id = in_irc_data.message["id"]
        self.__mod = in_irc_data.message["mod"]
        self.__returning_chatter = in_irc_data.message["returning-chatter"]
        self.__time_sent = in_irc_data.message["tmi-sent-ts"]
        self.__turbo = in_irc_data.message["turbo"]
        self.__user_type = in_irc_data.message["user-type"]
        self.__reply_callback = in_reply_callback
        
    def __repr__(self):
        return str(self.__dict__)
        
    @property
    def author(self):
        return self.__user
        
    @property
    def badges(self):
        # TODO: return TwitchBadges(self.__badge_data)
        return self.__badge_data
        
    @property
    def channel(self):
        return self.__channel
        
    @property
    def color(self):
        # TODO: return TwitchColor(self.__color)
        return self.__color
        
    @property
    def content(self):
        return self.__content
        
    @property
    def emote_data(self):
        return self.__emote_data
        
    @property
    def is_first_message(self):
        return self.__first_msg
        
    @property
    def is_mod(self):
        return self.__mod
        
    @property
    def is_returning_chatter(self):
        return self.__returning_chatter
        
    @property
    def is_turbo(self):
        return self.__turbo
        
    @property
    def message_id(self):
        return self.__message_id
        
    @property
    def user_type(self):
        return self.__user_type
        
    @property
    def time_sent(self):
        return self.__time_sent
        
    async def reply(self, in_reply_message):
        if self.__reply_callback:
            await self.__reply_callback(self.__message_id, self.channel, in_reply_message)
        
class TwitchChannel():
    def __init__(self, in_irc_data):
        self.__channel = in_irc_data.message["channel"]