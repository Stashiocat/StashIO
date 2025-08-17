import aiohttp
import asyncio
import datetime
from stashio.utils.data import DelayQueue

class BaseConnection():
    def __init__(self, in_server):
        # the eventsub server
        self.__server = in_server
        # the current active socket
        self.__ws = None
        # flag that will let our fibers stop
        self.__manual_shutdown_requested = False
        # the data we've read with recv() but haven't processed yet
        self.__data = ""
        # the data we want to send out but haven't processed yet
        self.__send_data = DelayQueue()
        # asyncio event loop
        self.__loop = asyncio.get_event_loop()
        # force a reconnect
        self.__force_reconnect = False
        
    async def shutdown_requested(self):
        return self.__manual_shutdown_requested
        
    async def stop(self):
        self.__manual_shutdown_requested = True
        await self.on_stop()

    async def force_reconnect(self):
        print("Marked force reconnect")
        self.__force_reconnect = True
    
    async def run(self):
        # task to process the data we read from the socket
        recv_event = self.__loop.create_task(self.process_recv_data())
        # task to process the data we want to send over the socket
        send_event = self.__loop.create_task(self.process_send_data())
        
        await self.on_run()
        
        while not self.__manual_shutdown_requested:
            async with aiohttp.ClientSession() as session:
                if not await self.is_connection_allowed():
                    await asyncio.sleep(0)
                    continue
                    
                try:
                    print("Connecting")
                    async with session.ws_connect(self.__server, timeout=1) as websocket:
                        self.__ws = websocket
                        await self.on_connect()
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
                                
                            if self.__force_reconnect:
                                break
                            if self.__manual_shutdown_requested:
                                break
                            
                        if self.__force_reconnect:
                            print("Forcing a reconnect")
                            self.__force_reconnect = False
                            continue
                        if self.__manual_shutdown_requested:
                            break
                        await asyncio.sleep(0)
                except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                    print("Failed to connect, trying again.")
                    await asyncio.sleep(5)
                    
        recv_event.cancel()
        send_event.cancel()
        
    async def process_recv_data(self):
        while not self.__manual_shutdown_requested:
            if len(self.__data) > 0:
                messages = self.__data.split('\r\n')
                self.__data = ""
                for m in messages:
                    if len(m) == 0:
                        continue
                    await self.on_receive(m)
            await asyncio.sleep(0)
        
            
    async def process_send_data(self):
        wait_queue = []
        
        while not self.__manual_shutdown_requested:
            try:
                data = self.__send_data.pop()
                if len(data) > 0:
                    items_to_check = wait_queue + data
                    wait_queue = []
                    out = []
                        
                    for p in items_to_check:
                        await self.__ws.send_str(p)
                        await asyncio.sleep(0)
                            
            except aiohttp.ClientDisconnectedError:
                continue
                
            await asyncio.sleep(0)
            
    async def send(self, in_data, in_delay = 0):
        self.__send_data.add(in_data, in_delay)
        
    async def on_run(self):
        pass
        
    async def on_stop(self):
        pass
        
    async def on_connect(self):
        pass
        
    async def on_receive(self, data):
        pass
        
    async def is_connection_allowed(self):
        return True