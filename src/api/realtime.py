import asyncio
import random
import time

from starlette.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect

# ==============================================================================
# SECTION 2: FRAMEWORK INTEROP (FastAPI & MCP)
# ==============================================================================


# 2.2 Real-time WebSockets
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 取得前端傳來的更新頻率
    interval = float(websocket.query_params.get("interval", 1.0))
    try:
        while True:
            # 透過任意方式取得並更新前端資料
            data = {"value": random.randint(0, 100), "ts": time.time()}
            await websocket.send_json(data)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        print("Client disconnected")