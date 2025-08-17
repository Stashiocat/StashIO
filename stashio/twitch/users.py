import ujson
import aiofiles

class UserBank():
    def __init__(self, in_twitch_api, in_bank_path='stashio/data/userbank.dat'):
        self.__api = in_twitch_api
        self.__path = in_bank_path
        with open(in_bank_path, 'r') as f:
            self.__userbank = ujson.load(f)
            
        if not "idlookup" in self.__userbank:
            self.__userbank["idlookup"] = dict()
        if not "userlookup" in self.__userbank:
            self.__userbank["userlookup"] = dict()
            
    async def __save_bank(self):
        async with aiofiles.open(self.__path, 'w') as f:
            await f.write(ujson.dumps(self.__userbank, sort_keys=True, indent=2))
            await f.flush()

    async def __save_result(self, result):
        for user_data in result[0]["data"]:
            found_id = user_data["id"]
            found_user = user_data["login"]
            self.__userbank["idlookup"][found_user] = found_id
            self.__userbank["userlookup"][found_id] = found_user
        await self.__save_bank()

    async def refresh_user_bank(self):
        ids = self.__userbank["userlookup"].keys()
        self.__userbank["idlookup"] = dict()
        self.__userbank["userlookup"] = dict()
        result = await self.__api.GetUsers(ids=ids)
        await self.__save_result(result)
            
        
    async def get_channel_id(self, in_username):
        if in_username in self.__userbank["idlookup"]:
            return self.__userbank["idlookup"][in_username]
            
        result = await self.__api.GetUsers([in_username])
        
        if result:
            data = result[0]["data"]
            if len(data) > 0:
                await self.__save_result(result)
                found_id = result[0]["data"][0]["id"]
                return found_id
            
        return None
        
    async def get_username_from_id(self, in_id):
        if in_id in self.__userbank["userlookup"]:
            return self.__userbank["userlookup"][in_id]
            
        result = await self.__api.GetUsers(ids=[in_id])
        
        if result:
            await self.__save_result(result)
            found_user = result[0]["data"][0]["login"]
            return found_user
            
        return None
