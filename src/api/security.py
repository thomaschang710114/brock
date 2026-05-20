from collections import defaultdict
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response

# ==============================================================================
# SECTION 3: PRODUCTION SECURITY & MIDDLEWARE
# ==============================================================================

ALLOWED_IPS = {"127.0.0.1", "::1"}


# 3.1 Security Headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    '''攔截 inbound request / outgoing response 並注入 security headers'''
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response


# 3.2 Secure Cookie Management
class CookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.set_cookie(
            key="session_id",
            value="abc123_demo",
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
        )
        return response


# 3.3 IP Whitelisting
class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        client_ip = request.client.host
        # print(f'IPWhitelistMiddleware.dispatch {client_ip=}')
        # Allow localhost for demo
        if client_ip not in ALLOWED_IPS:
            return Response("Forbidden (IP Whitelist Demo)", status_code=403)
        return await call_next(request)


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
