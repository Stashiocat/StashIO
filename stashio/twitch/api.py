import aiohttp
import asyncio
import ujson

class TwitchApi():
    def __init__(self, in_auth):
        self.__auth = in_auth
        
    def __get_oauth_header(self, content_type=None):
        out = {
            'client-id': self.__auth.get_client_id(),
            'authorization': f'Bearer {self.__auth.get_access_token()}'
        }
        
        if content_type:
            out['content-type'] = content_type
            
        return out
        
    async def __api_request(self, session, url):
        async with session.get(url) as r:
            return await r.json()
            
    async def __api_request_post_json(self, session, url, data):
        async with session.post(url, json=data) as r:
            return await r.json()
            
    async def RefreshIRCAccessToken(self):
        await self.__auth.refresh_irc_access_token()
        
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
            
    async def ExecuteTwitchAPIRequest(self, url, all_results=False, data_only=True):
        refresh=2
        while refresh > 0:
            refresh = refresh - 1
            async with aiohttp.ClientSession(headers=self.__get_oauth_header()) as session:
                result = await self.__api_request(session, url)
                
                if 'error' in result:
                    if result['status'] == 401:
                        await self.__auth.refresh_access_token()
                        continue
                elif not 'data' in result:
                    print("BAD RESULT DURING API REQUEST:",result)
                    return None
                    
                if data_only:
                    if len(result['data']) == 0 or all_results:
                        return result['data']
                    else:
                        return result['data'][0]
                else:
                    return result
                    
    async def GetFollowerCount(self, in_user):
        channel_id = await self.GetChannelID(in_user)
        if channel_id:
            url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={channel_id}'
            res = await self.ExecuteTwitchAPIRequest(url, data_only=False)
            return res
        return None
            
    async def GetChannelID(self, in_user):
        res = await self.GetUsers(users=[in_user])
        return res[0]["data"][0]["id"] if len(res[0]["data"]) > 0 else None
    
    async def GetChannelSettings(self, channel_id):
        url = f'https://api.twitch.tv/helix/chat/settings?broadcaster_id={channel_id}'
        return await self.ExecuteTwitchAPIRequest(url)
            
    async def GetChannelInformation(self, channel_id):
        url = f'https://api.twitch.tv/helix/channels?broadcaster_id={channel_id}'
        return await self.ExecuteTwitchAPIRequest(url)
            
    async def GetStreamsInfo(self, channel_names):
        channel_names_string = "&user_login=".join(channel_names)
        url = f'https://api.twitch.tv/helix/streams?type=all&first=100&user_login={channel_names_string}'
        return await self.ExecuteTwitchAPIRequest(url, all_results=True)

    async def EventSub_CreateSubscription(self, in_sub_object, in_session_id):
        async with aiohttp.ClientSession(headers=self.__get_oauth_header(content_type="application/json")) as session:
            url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
            result = await self.__api_request_post_json(session, url, data=in_sub_object.GetJson(in_session_id))
            return result["data"][0]
            