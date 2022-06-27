from stashio.bot.stashio_twitch_bot import StashioTwitchBot
import asyncio

class TestBot(StashioTwitchBot):
    def __init__(self):
        super().__init__('auth.json')
        
    async def event_message(self, message):
        if message.content == "!hi":
            await message.reply("Hello!")
            
    async def event_authenticated(self):
        print("Connected")
        
async def main():
    bot = TestBot()
    await bot.run()
    
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
except KeyboardInterrupt:
    print("Killed with Ctrl+C")