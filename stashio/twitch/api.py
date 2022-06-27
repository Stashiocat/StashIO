import aiohttp
import asyncio

class TwitchApi():
    def __init__(self, in_auth):
        self.__auth = in_auth
        
    def __get_oauth_header(self):
        return {
            'client-id': self.__auth.get_client_id(),
            'authorization': f'Bearer {self.__auth.get_access_token()}'
        }
        
    async def __api_request(self, session, url):
        async with session.get(url) as r:
            return await r.json()
        
    async def GetUsers(self, users=None, ids=None):
        requests = []
        if users:
            requests = [f'login={user}' for user in users]
                
        if ids:
            requests += [f'id={id}' for id in ids]
        
        fetch_requests = []
        for i in range(0, len(requests), 100):
            fetch_requests.append(f'https://api.twitch.tv/helix/users?{"&".join(requests[i:i+100])}')

        async with aiohttp.ClientSession(headers=self.__get_oauth_header()) as session:
            results = await asyncio.gather(*[self.__api_request(session, url) for url in fetch_requests], return_exceptions=True)
            return results
            