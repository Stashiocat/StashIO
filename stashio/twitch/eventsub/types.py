import ujson

class Message_SessionWelcome():
    def __init__(self, in_payload):
        session = in_payload["session"]
        self.__id = session["id"]
        self.__status = session["status"]
        self.__connected_at = session["connected_at"]
        self.__keepalive_timeout_seconds = int(session["keepalive_timeout_seconds"]) + 3
        self.__reconnect_url = session["reconnect_url"]
        
    @property
    def id(self):
        return self.__id
        
    @property
    def status(self):
        return self.__status
        
    @property
    def connected_at(self):
        return self.__connected_at
        
    @property
    def keepalive_timeout(self):
        return self.__keepalive_timeout_seconds
        
class Message_ChannelRewardRedemption():
    def __init__(self, in_payload):
        pass

class EventSubMessage():
    def __init__(self, in_message):
        if not "metadata" in in_message or not "payload" in in_message:
            print("Malformed message:")
            print(in_message)
            return
            
        metadata = in_message["metadata"]
        self.__message_id = metadata["message_id"]
        self.__message_type = metadata["message_type"]
        self.__message_timestamp = metadata["message_timestamp"]
        self.__payload = in_message["payload"]
        
    def __str__(self):
        return f"Message ID: {self.__message_id}\nMessage Type: {self.__message_type}\nPayload: {str(self.__payload)}"
        
    @property
    def id(self):
        return self.__message_id
        
    @property
    def type(self):
        return self.__message_type
        
    @property
    def timestamp(self):
        return self.__message_timestamp
        
    @property
    def payload(self):
        return self.__payload
    
class EventSubscriptionType():    
    def __init__(self, in_type, in_version):
        self.__type = in_type
        self.__version = in_version
        
    @property
    def type(self):
        return self.__type
        
    def GetJson(self, session_id):
        packet = {
            "type": self.__type,
            "version": self.__version,
            "condition": self.GetCondition(),
            "transport": {
                "method": "websocket",
                "session_id": session_id
            }
        }
        return packet
        
    async def execute(self, twitch_api, session_id):
        await twitch_api.EventSub_CreateSubscription(self.GetJson(session_id))
        
    # override in child class with proper condition for the subscription type
    def GetCondition(self):
        pass
        
# For subscriptions that only take in a channel id
class EventSub_BaseChannelID(EventSubscriptionType):
    def __init__(self, in_type, in_version, in_channel_id, in_conditions = []):
        super().__init__(in_type, in_version)
        self.__channel_id = in_channel_id
        self.__conditions = in_conditions
        
    def GetCondition(self):
        out = {
            "broadcaster_user_id": self.__channel_id,
            "user_id": self.__channel_id
        }
        
        for name, val in self.__conditions:
            out[name] = val
            
        return out

##################################################################################
## These are passed to interfaces when subscribing to something
##################################################################################
# A broadcaster updates their channel properties e.g., category, title, content classification labels, broadcast, or language.
class EventSub_ChannelUpdate(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.update", "2", in_channel_id)

# A notification when a specified channel receives a subscriber. This does not include resubscribes.
class EventSub_ChannelChatMessage(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.chat.message", "1", in_channel_id)

# A notification when a specified channel receives a subscriber. This does not include resubscribes.
class EventSub_ChannelSubscribe(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.subscribe", "1", in_channel_id)

# A notification when a subscription to the specified channel ends.
class EventSub_ChannelSubscriptionEnds(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.subscription.end", "1", in_channel_id)

# A notification when a viewer gives a gift subscription to one or more users in the specified channel.
class EventSub_ChannelSubscriptionGift(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.subscription.gift", "1", in_channel_id)

# A notification when a user sends a resubscription chat message in a specific channel.
class EventSub_ChannelSubscriptionMessage(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.subscription.message", "1", in_channel_id)

# A user cheers on the specified channel.
class EventSub_ChannelCheer(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.cheer", "1", in_channel_id)

# A viewer has redeemed a custom channel points reward on the specified channel.
class EventSub_ChannelPointRedemption(EventSub_BaseChannelID):
    def __init__(self, in_channel_id, in_reward_id = None):
        conditions = []
        if in_reward_id:
            conditions = [("reward_id", in_reward_id)]
        super().__init__("channel.channel_points_custom_reward_redemption.add", "1", in_channel_id, conditions)

# A Hype Train begins on the specified channel.
class EventSub_HypeTrainBegin(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.hype_train.begin", "1", in_channel_id)

# A Hype Train makes progress on the specified channel.
class EventSub_HypeTrainUpdate(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.hype_train.progress", "1", in_channel_id)

# A Hype Train ends on the specified channel.
class EventSub_HypeTrainEnd(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.hype_train.end", "1", in_channel_id)

# A poll started on a specified channel.
class EventSub_PollBegin(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.poll.begin", "1", in_channel_id)

# Users respond to a poll on a specified channel.
class EventSub_PollUpdate(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.poll.progress", "1", in_channel_id)

# A poll ended on a specified channel.
class EventSub_PollEnd(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.poll.end", "1", in_channel_id)

# A Prediction started on a specified channel.
class EventSub_PredictionBegin(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.prediction.begin", "1", in_channel_id)

# Users participated in a Prediction on a specified channel.
class EventSub_PredictionUpdate(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.prediction.progress", "1", in_channel_id)

# A Prediction was locked on a specified channel.
class EventSub_PredictionLock(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.prediction.lock", "1", in_channel_id)

# A Prediction ended on a specified channel.
class EventSub_PredictionEnd(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("channel.prediction.end", "1", in_channel_id)

# The specified broadcaster starts a stream.
class EventSub_StreamOnline(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("stream.online", "1", in_channel_id)

# The specified broadcaster stops a stream.
class EventSub_StreamOffline(EventSub_BaseChannelID):
    def __init__(self, in_channel_id):
        super().__init__("stream.offline", "1", in_channel_id)