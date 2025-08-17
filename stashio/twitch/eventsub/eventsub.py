import asyncio
import ujson
import stashio.twitch.eventsub.types as EventSubTypes
from stashio.utils.auth import Auth
from stashio.utils.data import DelayQueue
from stashio.connection.wss_connection import BaseConnection

class EventSubConnection(BaseConnection):
    def __init__(self, in_twitch_api, in_server='wss://eventsub.wss.twitch.tv/ws'):
        super().__init__(in_server)
        # asyncio event loop
        self.__loop = asyncio.get_event_loop()
        # the current subscribed subscriptions
        self.__subscriptions = dict()
        # pending api requests waiting to be processed by the pending api task
        self.__pending_api_requests = []
        # used to make api requests to twitch
        self.__twitch_api = in_twitch_api
        # our session that holds our session id
        self.__session = None
        # our running event for handling api requests
        self.__api_event = None
    
    #############################################################
    ## Start BaseConnection overrides
    #############################################################
    async def is_connection_allowed(self):
        return len(self.__subscriptions) > 0
        
    async def on_run(self):
        # task to execute api requests
        self.__api_event = self.__loop.create_task(self.process_api_requests())
        
    async def on_stop(self):
        self.__api_event.cancel()
        
    async def on_receive(self, data):
        json_data = ujson.loads(data)
        if json_data:
            metadata = json_data["metadata"]
            message_type = metadata["message_type"]
            payload = json_data["payload"]
            if message_type == "session_welcome":
                self.__session = EventSubTypes.Message_SessionWelcome(payload)
            elif message_type == "notification":
                subscription = payload["subscription"]
                event = payload["event"]
                await self.__subscriptions[subscription["type"]](event)
            elif message_type == "session_keepalive":
                pass
            else:
                print("Unknown:",json_data)
    #############################################################
    ## End BaseConnection overrides
    #############################################################
    
    async def eventsub_listen(self, obj, callback):
        if obj.type in self.__subscriptions:
            print("Already subscribed to this event")
            return False
            
        self.__subscriptions[obj.type] = callback
        await self.add_subscription(obj, callback)
        return True
        
    async def channel_subscribe(self, channel_id, subscriptions_and_callbacks):
        for sub, callback in subscriptions_and_callbacks:
            obj = sub(channel_id)
            await self.eventsub_listen(obj, callback)
        
    async def add_subscription(self, subscription_obj, callback):
        self.__pending_api_requests.append(subscription_obj)
        
    async def process_api_requests(self):
        while not await self.shutdown_requested():
            if self.__session:
                for apireq in self.__pending_api_requests:
                    await apireq.execute(self.__twitch_api, self.__session.id)
                self.__pending_api_requests = []
            await asyncio.sleep(0)
                