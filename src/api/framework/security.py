from collections import defaultdict
import time

# from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.routing import WebSocketRoute, Match
from starlette.types import ASGIApp, Scope, Receive, Send

# ==============================================================================
# SECTION 3: PRODUCTION SECURITY & MIDDLEWARE
# ==============================================================================

ALLOWED_IPS = {"127.0.0.1", "::1"}


# 3.1 Security Headers
# class SecurityHeadersMiddleware(BaseHTTPMiddleware):
#     '''攔截 inbound request / outgoing response 並注入 security headers'''
#     async def dispatch(self, request, call_next):
#         response = await call_next(request)
#         response.headers["X-Frame-Options"] = "SAMEORIGIN"
#         response.headers["X-Content-Type-Options"] = "nosniff"
#         response.headers["Strict-Transport-Security"] = "max-age=31536000"
#         return response
class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"X-Frame-Options"] = b"SAMEORIGIN"
                headers[b"X-Content-Type-Options"] = b"nosniff"
                headers[b"Strict-Transport-Security"] = b"max-age=31536000"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)

# 3.2 Secure Cookie Management
# class CookieMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         response = await call_next(request)
#         response.set_cookie(
#             key="session_id",
#             value="abc123_demo",
#             httponly=True,
#             secure=False,  # Set to True in production
#             samesite="lax",
#         )
#         return response
class CookieMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # 注入 Set-Cookie header
                cookie_value = b"session_id=abc123_demo; HttpOnly; SameSite=Lax"
                headers.append((b"Set-Cookie", cookie_value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


# 3.3 IP Whitelisting
# class IPWhitelistMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         client_ip = request.client.host
#         # print(f'IPWhitelistMiddleware.dispatch {client_ip=}')
#         # Allow localhost for demo
#         if client_ip not in ALLOWED_IPS:
#             return Response("Forbidden (IP Whitelist Demo)", status_code=403)
#         return await call_next(request)
class IPWhitelistMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # 關鍵：非 HTTP 請求 (如 WebSocket) 直接放行，交給後面的 Shield 處理
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ["", 0])[0]
        if client_ip not in ALLOWED_IPS:
            response = Response("Forbidden (IP Whitelist Demo)", status_code=403)
            await response(scope, receive, send)
            return
            
        await self.app(scope, receive, send)


# --- 3.4 API Key 驗證 (新增) ---
API_KEY_CREDENTIALS = {"super-secret-key-123", "engineer-team-key-999"}

class APIKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 只針對 /api/ 開頭的請求進行驗證
        if scope["type"] == "http" and scope["path"].startswith("/api/"):
            # 從 Header 抓取 X-API-Key
            headers = dict(scope.get("headers", []))
            api_key = headers.get(b"x-api-key", b"").decode("utf-8")

            if api_key not in API_KEY_CREDENTIALS:
                # 沒帶鑰匙或鑰匙錯了，直接擋掉回傳 401
                response = JSONResponse(
                    {"detail": "Invalid or missing API Key"}, 
                    status_code=401
                )
                await response(scope, receive, send)
                return

        # 驗證通過，或是非 API 請求 (如 UI)，直接放行
        await self.app(scope, receive, send)


# --- 3.5 流量限制 (Rate Limiting) ---
# 儲存結構: { "IP": [timestamp1, timestamp2, ...] }
call_history = defaultdict(list)
LIMIT_PER_MINUTE = 10  # 每分鐘最多 10 次

class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/api/"):
            client_ip = scope.get("client", ["", 0])[0]
            current_time = time.time()
            
            # 1. 取得該 IP 的紀錄，並過濾掉超過 60 秒之前的舊紀錄
            timestamps = call_history[client_ip]
            timestamps = [t for t in timestamps if current_time - t < 60]
            
            # 2. 檢查是否超過門檻
            if len(timestamps) >= LIMIT_PER_MINUTE:
                response = JSONResponse(
                    {
                        "detail": "Too Many Requests", 
                        "retry_after": 60,
                        "ip": client_ip
                    }, 
                    status_code=429  # 標準的「請求過多」狀態碼
                )
                await response(scope, receive, send)
                return
            
            # 3. 驗證通過，紀錄本次時間，並更新回全域變數
            timestamps.append(current_time)
            call_history[client_ip] = timestamps

        await self.app(scope, receive, send)


# 3.6 終極防護盾牌：處理 Streamlit 的 WebSocket (取代 WebSocketGuardMiddleware)
class WSProtocolShield:
    def __init__(self, app: ASGIApp, raw_app: ASGIApp):
        self.app = app
        self.raw_app = raw_app # 傳入未經包裝的 raw_app (App 實例)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # 1. 攔截 WebSocket 請求
        if scope["type"] == "websocket":
            # 取得 Streamlit 內部的 Starlette 實例
            # 注意：這裡我們穿透層層包裝，直接找最底層的 _starlette_app
            target_app = self.raw_app
            while hasattr(target_app, "app") and not hasattr(target_app, "_starlette_app"):
                target_app = target_app.app
            
            internal_starlette = getattr(target_app, "_starlette_app", None)
            
            if internal_starlette:
                # 2. 遍歷所有路由，找出匹配這個 WebSocket 的處理器
                for route in internal_starlette.routes:
                    if isinstance(route, WebSocketRoute):
                        match, _ = route.matches(scope)
                        if match == Match.FULL:
                            # 🎯 找到了！直接執行這個路由的 handler，
                            # 完全跳過中間件列表和可能會崩潰的路由器搜尋
                            await route.handle(scope, receive, send)
                            return
            
            # 3. 如果找不到匹配的 WS 路由，直接關閉，防止它掉進 StaticFiles
            await send({"type": "websocket.close", "code": 1000})
            return

        # 4. 一般 HTTP 請求，正常走原本的流程
        await self.app(scope, receive, send)

# (Helper for Demo)
async def simulate_ip_policy(request):
    """用於前端測試 Middleware 邏輯的 API"""
    print('simulate_ip_policy')
    ip_to_test = request.query_params.get("ip", "0.0.0.0")
    if ip_to_test in ALLOWED_IPS:
        return JSONResponse(
            {"status": "allowed", "ip": ip_to_test, "message": "Access Granted ✅"}
        )
    else:
        return JSONResponse(
            {"status": "blocked", "ip": ip_to_test, "message": "403 Forbidden ⛔"},
            status_code=403,
        )


# 與其在外面寫 Route，不如直接寫在 fastapi 實例裡
# @fastapi.get("/security/simulate-ip")
# async def simulate_ip_policy_fastapi(ip: str = "0.0.0.0"):
#     # same logic
#     pass
