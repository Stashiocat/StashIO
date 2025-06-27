from stashio.bot.stashio_twitch_bot import StashioTwitchBot
import asyncio

class TestBot(StashioTwitchBot):
    def __init__(self):
        super().__init__('auth.json')
        
    # Called when a message happens in a channel that the bot is in
    # You can check which channel it is with message.channel.name and who sent it with message.author.name
    async def event_message(self, message):
        if message.content == "!hi":
            await message.reply("Hello!")
            
    # Called after you've successfully authenticated
    async def event_authenticated(self):
        print("Successfully authenticated")
        await self.join_channels(["stashiocat"])
        
async def main():
    bot = TestBot()
    await bot.run()
    
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
except KeyboardInterrupt:
    print("Killed with Ctrl+C")