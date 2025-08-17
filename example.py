from stashio.bot.stashio_twitch_bot import StashioTwitchBot, EventSubSubscriptions
import asyncio

class TestBot(StashioTwitchBot):
    def __init__(self):
        super().__init__('auth.json', in_use_irc=False)
        
            
    # Async hook to run startup stuff for your bot (e.g. eventsub)
    async def event_initialize(self):
        
        print("Successfully authenticated")
        
        #subscriptions_and_callbacks = [
        #    (EventSubSubscriptions.ChannelPointRedemption, self.channel_point_redemption),
        #    (EventSubSubscriptions.ChannelChatMessage, self.channel_chat_message)
        #]
        
        #await self.channel_subscribe("stashiocat", subscriptions_and_callbacks)
        
    # Called when someone redeems channel poitns. Requires an event subscription. See commented out code in event_initialize.
    async def channel_point_redemption(self, event_data):
        print("GOT REDEEM!", event_data)
        
    # Called when someone chats. Requires an event subscription. See commented out code in event_initialize.
    async def channel_chat_message(self, event_data):
        print("GOT CHAT DATA:", event_data)
        
    #async def event_irc_connected(self):
    #    print("IRC CONNECTED")
    #    await self.join_channels(["stashiocat"])
        
    # Called when an irc message happens in a channel that the bot is in
    # You can check which channel it is with message.channel.name and who sent it with message.author.name
    #async def event_irc_message(self, message):
    #    if message.content == "!hi":
    #        await message.reply("Hello!")
        
async def main():
    bot = TestBot()
    await bot.run()
    
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
except KeyboardInterrupt:
    print("Killed with Ctrl+C")