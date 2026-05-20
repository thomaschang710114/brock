import uuid
import platform

import httpx
from starlette.requests import Request


class NodeIdentity:
    '''
    在 API 中的使用範例:
    async def some_api_endpoint(request: Request):
        client_ctx = NodeIdentity.get_client_info(request)
        server_ctx = await NodeIdentity.get_server_info()
        
        print(f"Log: User {client_ctx['client_ip']} called me, I am {server_ctx['node']}")
        # ... 執行你的邏輯 ...
    '''
    
    _server_info_cache = None
    
    @classmethod
    async def get_server_info(cls):
        """取得伺服器（Backend）端資訊，並進行快取"""
        if cls._server_info_cache:
            return cls._server_info_cache

        # 取得公網 IP (非同步呼叫)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get('https://api.ipify.org')
                my_ip = resp.text
        except Exception:
            my_ip = "127.0.0.1"

        # 整理平台資訊
        # 'macOS-13.5.1-arm64-arm-64bit' -> 'macOS-13.5.1'
        raw_platform = platform.platform()
        my_platform = raw_platform.rsplit('-', maxsplit=3)[0] if '-' in raw_platform else raw_platform
        
        my_node = platform.node()
        # 取得 MAC Address
        my_mac = uuid.uuid1().hex[-12:]

        cls._server_info_cache = {
            "ip": my_ip,
            "platform": my_platform,
            "node": my_node,
            "mac": my_mac
        }
        return cls._server_info_cache
    
    @staticmethod
    def get_client_info(request: Request):
        """
        從 Starlette Request 物件中提取用戶端資訊。
        這取代了原本需要透過 JavaScript 才能取得的大部分資訊。
        """
        # 優先取得 X-Forwarded-For (如果是在 Nginx/Proxy 後面)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0]
        else:
            client_ip = request.client.host if request.client else "unknown"

        user_agent = request.headers.get("user-agent", "unknown")
        
        # 解析 User-Agent 取得簡易平台資訊 (或是直接回傳原始字串供 Log 記錄)
        return {
            "client_ip": client_ip,
            "user_agent": user_agent,
            "path": request.url.path,
            "method": request.method
        }
