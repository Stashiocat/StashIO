import re

class IRCData():
    def __init__(self, in_raw_message):
        #initialization
        self.message = dict()
        
        #parse
        pattern = "^(?P<tags>@[^ ]+)? ?(?P<source>:[^ ]+)? ?(?P<command>[^:]+):?(?P<params>.+?)?$"
        m = re.fullmatch(pattern, in_raw_message)
        if not m:
            print("==============================================")
            print("Failed to parse message")
            print(in_raw_message)
            print("==============================================")
        else:
            tags = m.group("tags")
            source = m.group("source")
            cmd = m.group("command")
            params = m.group("params")
            
            if tags:
                self.__parse_tags(tags[1:])
                
            if source:
                splitSource = source[1:].split('!')
                self.message["source"] = dict()
                self.message["source"]["nick"] = splitSource[0] if len(splitSource) > 1 else None
                self.message["source"]["host"] = splitSource[1] if len(splitSource) > 1 else splitSource[0]

            self.__parse_command(cmd, params)
            if self.command == "PRIVMSG":
                m2 = re.fullmatch("^\x01ACTION (?P<message>.+)\x01$", self.content)
                if m2:
                    self.message["content"] = "/me " + m2.group("message")
            
    def __repr__(self):
        return str(self.message)
            
    def __get_property(self, prop_name):
        return self.message[prop_name] if prop_name in self.message else None
            
    @property
    def command(self):
        return self.__get_property("command")
            
    @property
    def name(self):
        return self.message["source"]["nick"]
        
    @property
    def display_name(self):
        return self.__get_property("display-name")
            
    @property
    def channel(self):
        return self.__get_property("channel")
        
    @property
    def channel_id(self):
        id = self.__get_property("room-id")
        return int(id) if id else 0
        
    @property
    def user_id(self):
        id = self.__get_property("user-id")
        return int(id) if id else 0
            
    @property
    def content(self):
        return self.__get_property("content")
        
    @property
    def badges(self):
        return self.__get_property("badges")
        
    @property
    def is_mod(self):
        return (self.__get_property("mod") not in [None, '0']) or self.is_broadcaster
        
    @property
    def is_vip(self):
        badges = self.badges
        if badges:
            if 'vip' in badges:
                return True
        return False
        
    @property
    def is_broadcaster(self):
        badges = self.badges
        if badges:
            if 'broadcaster' in badges:
                return True
        return False
        
    @property
    def is_subscriber(self):
        return (self.__get_property("subscriber") not in [None, '0']) or self.is_broadcaster
            
    def __parse_command(self, command, params):
        splitCommand = command.split(' ')
        
        cmd = splitCommand[0]
        self.message["command"] = cmd
        
        if cmd in ["JOIN", "PART", "NOTICE", "CLEARCHAT", "HOSTTARGET", "PRIVMSG", "USERSTATE", "ROOMSTATE", "001"]:
            if splitCommand[1][0] == '#':
                splitCommand[1] = splitCommand[1][1:]
            self.message["channel"] = splitCommand[1]
            self.message["content"] = params
        elif cmd in ["CAP"]:
            self.message["ack"] = splitCommand[1] == "ACK"
            self.message["capabilities"] = self.__parse_capabilities(params)
        elif cmd in ["PING", "GLOBALUSERSTATE", "RECONNECT"]:
            self.message["content"] = params
        
    def __parse_tags(self, raw_tags):
        tags = raw_tags.split(";")
        
        for tag in tags:
            key, val = tag.split('=', 1)
            
            if len(val) == 0:
                val = None
                
            if val is not None and key in ["badge-info", "badges"]:
                if not "badges" in self.message:
                    self.message["badges"] = dict()
                    
                badges = val.split(',')
                
                for badge in badges:
                    badge_name, metadata = badge.split('/', 1)
                    
                    if not badge_name in self.message["badges"]:
                        self.message["badges"][badge_name] = dict()
                        
                    if key == "badge-info" and badge_name == "subscriber":
                        self.message["badges"][badge_name]["months"] = metadata
                    elif key == "badge-info" and badge_name == "predictions":
                        self.message["badges"][badge_name]["prediction_name"] = metadata
                    else:
                        self.message["badges"][badge_name]["version"] = metadata
            elif val is not None and key == "emotes":
                self.message["emotes"] = self.__parse_emotes(val)
            elif val is not None and key == "emote-sets":
                self.message["emote-sets"] = val.split(',')
            else:
                self.message[key] = val
                
    def __parse_emotes(self, raw_emotes):
        emotes = raw_emotes.split('/')
        out_emotes = dict()
        
        for emote in emotes:
            id, all_ranges = emote.split(':', 1)
            
            if not id in out_emotes:
                out_emotes[id] = []
                
            ranges = all_ranges.split(',')
            
            for range in ranges:
                start, end = range.split('-', 1)
                out_emotes[id].append({'start': start, 'end': end})
                
        return out_emotes
        
    def __parse_capabilities(self, raw_capabilities):
        #twitch.tv/commands twitch.tv/tags twitch.tv/membership
        #todo: maybe get rid of the twitch.tv/ part
        return raw_capabilities.split(' ')
        
        
class IRCPackets():
    class QueueType():
        NONE = 0
        PRIVMSG = 1
        JOIN = 2
        PART = 3
        
    class Packet():
        def queue_type(self):
            return IRCPackets.QueueType.NONE
            
    class Message(Packet):
        def __init__(self, channel, message, reply_id=None):
            self.__channel = channel
            if message[0] == '/':
                if message[0:3] == '/me':
                    message = '\x01ACTION ' + message[3:] + '\x01'
                else:
                    message = re.sub("^(/\s*)+", "", message)
            if message[0] == '.':
                message = re.sub("^(\.\s*)+", "", message)
            reply = f"@reply-parent-msg-id={reply_id}" if reply_id else ""
            self.__packet = f"{reply} PRIVMSG #{channel.name} :{message}".strip()
            
        def __lt__(self, other):
            return self.get() < other.get()
            
        def __le__(self, other):
            return self.get() <= other.get()
            
        def get(self):
            return self.__packet
            
        @property
        def channel(self):
            return self.__channel

        def queue_type(self):
            return IRCPackets.QueueType.PRIVMSG
        
    class Join(Packet):
        def __init__(self, channel):
            self.__packet = f"JOIN #{channel}"
            
        def __lt__(self, other):
            return self.get() < other.get()
            
        def __le__(self, other):
            return self.get() <= other.get()
            
        def get(self):
            return self.__packet
            
        def queue_type(self):
            return IRCPackets.QueueType.JOIN
        
    class Part(Packet):
        def __init__(self, channel):
            self.__packet = f"PART #{channel}"
            
        def __lt__(self, other):
            return self.get() < other.get()
            
        def __le__(self, other):
            return self.get() <= other.get()
            
        def get(self):
            return self.__packet
            
        def queue_type(self):
            return IRCPackets.QueueType.PART
        
    class ChangeColor(Packet):
        def __init__(self, color):
            self.__packet = f"PRIVMSG #jtv :.color {color}"
            
        def __lt__(self, other):
            return self.get() < other.get()
            
        def __le__(self, other):
            return self.get() <= other.get()
            
        def get(self):
            return self.__packet

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
        self.__first_msg = in_irc_data.message["first-msg"] if "first-msg" in in_irc_data.message else '0'
        self.__message_id = in_irc_data.message["id"]
        self.__mod = in_irc_data.message["mod"]
        self.__returning_chatter = in_irc_data.message["returning-chatter"] if "returning-chatter" in in_irc_data.message else '0'
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
    def display_name(self):
        return self.__display_name
        
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
        
    async def reply(self, in_reply_message, in_delay = 0):
        if self.__reply_callback:
            await self.__reply_callback(self.__message_id, self.channel, in_reply_message, in_delay)
        
class TwitchChannel():
    def __init__(self, in_irc_data):
        self.__channel = in_irc_data.message["channel"]