import os
from contextlib import asynccontextmanager

from starlette.middleware import Middleware
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from streamlit.starlette import App

# 匯入所有自定義功能模組
from src.api import (
    dataframe_demo, json_demo, security, 
    lifecycle, exceptions, metadata, 
    interop, realtime, gsheet_api, finance
)

# 1.2 Serving Static Assets (Handled by Mount in 'routes' list)


# ==============================================================================
# SECTION 4: PERFORMANCE & LIFECYCLE
# ==============================================================================


# --- 4.1 生命週期管理 ( wiring lifecycle and interop ) ---
@asynccontextmanager
async def lifespan(app):
    print("🚀 App starting: Initializing resources...")

    # 4.1 & 4.2: Initialize resources & warm cache
    await lifecycle.db_connection.connect()
    await lifecycle.prewarm_ml_model()
    await lifecycle.gs_manager.connect()  # 初始化 gspread

    # Initialize sub-apps (MCP)
    async with interop.mcp_app.lifespan(app):
        yield

    # Cleanup
    print("👋 App shutting down: Cleaning up resources...")
    await lifecycle.db_connection.disconnect()


# ==============================================================================
# UNIFIED APP ASSEMBLY
# ==============================================================================

routes = [
    # Section 1: Custom Routes & Dataframe
    Route("/api/raw-data", json_demo.custom_starlette_data),
    Route("/api/html-demo", json_demo.html_response_demo),
    Route("/api/plain-text", json_demo.plain_text_demo),
    Route("/api/redirect-demo", json_demo.redirect_demo),
    Route("/api/users/{user_id}", json_demo.path_params_demo),
    Route("/api/users/{user_id}/{action}", json_demo.path_params_demo),
    Route("/api/df-json", dataframe_demo.dataframe_json_demo),
    Route("/api/df-csv", dataframe_demo.dataframe_csv_demo),
    Route("/api/excel-demo", dataframe_demo.excel_response_demo),
    Route("/api/stock-parquet", dataframe_demo.stock_data_parquet_demo),

    # 1.2 Serving Static Assets
    Mount("/landing", app=StaticFiles(directory="src/landing", html=True), name="landing"),
    # Mount("/static", app=StaticFiles(directory="src/static"), name="static"),  # 存放靜態資料

    # 1.3 SEO & Metadata Endpoints
    Route("/robots.txt", metadata.robots_txt),
    Route("/sitemap.xml", metadata.sitemap_xml),
    Route("/manifest.json", metadata.manifest_json),

    # Section 3: Security Helpers (Moved up to avoid shadowing)
    Route("/api/security/simulate-ip", security.simulate_ip_policy),

    # Section 4: Performance (Moved up to avoid shadowing)
    Route("/api/background/email", lifecycle.background_email, methods=["POST"]),
    Route("/api/trigger-error", exceptions.trigger_error),
    
    # # 自定義, 新增 Google Sheet 轉 Parquet 的 API
    # Route("/api/gsheet/parquet", gsheet_api.pull_sheet_as_parquet),
    # Route("/api/gsheet/batch-warmup", gsheet_api.trigger_batch_warmup),
    # Route("/api/finance/bot-rates", finance.get_bot_rates_api),  # 整合進 FastAPI

    # Section 2: Framework Interop & WebSockets
    Mount("/api", app=interop.fastapi),  # 看到 /api 開頭的請求都交給 fastapi, docs/ 也會掛在 /api 下
    WebSocketRoute("/realtime", realtime.websocket_endpoint),
    Mount("/analytics", app=interop.mcp_app),  # mcp server 需在 Starlette 之前產生, 需借助 lifespan
]

middleware = [
    Middleware(security.CookieMiddleware),
    Middleware(security.IPWhitelistMiddleware),
    Middleware(security.SecurityHeadersMiddleware),
    # Middleware(security.APIKeyMiddleware),  # 需要時再打開
    # Middleware(security.RateLimitMiddleware),  # 需要時再打開
]

# 組合出 streamlit_app.py 的絕對路徑
current_dir = os.path.dirname(os.path.abspath(__file__)) 
st_app_path = os.path.join(current_dir, "src", "streamlit_app.py")
# 檢查檔案是否存在 (增加一點防錯機制，方便 Debug)
if not os.path.exists(st_app_path):
    print(f"❌ 找不到 Streamlit 檔案路徑: {st_app_path}")

app = App(
    st_app_path,
    routes=routes,
    middleware=middleware,
    lifespan=lifespan,
    exception_handlers=exceptions.exception_handlers,
)
