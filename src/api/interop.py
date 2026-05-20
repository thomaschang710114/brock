from fastapi import FastAPI
from fastmcp import FastMCP

from src.api import finance , gsheet_api # 載入其他模組掛入 APIRouter


# ==============================================================================
# SECTION 2: FRAMEWORK INTEROP (FastAPI & MCP)
# ==============================================================================

# 2.1 Mounting FastAPI
fastapi = FastAPI(title="GoodBuy Data Hub", version="0.1.0")


@fastapi.get("/health")
async def health():
    return {"status": "healthy", "service": "streamlit-integrated-api"}


@fastapi.post("/predict")
async def predict(data: dict):
    return {"result": data.get("value", 0) * 2}


# TODO: fastapi.include_router 把其它檔案定義的 APIRouter 註冊進來
fastapi.include_router(finance.router)
fastapi.include_router(gsheet_api.router)


# 2.3 MCP Server Integration - 需透過 lifespan 告知 MCP 伺服器啟動
mcp = FastMCP("Streamlit Integration 🚀")


@mcp.tool
def greet(name: str) -> str:
    """Greet a user. Perfect for demoing MCP calls."""
    return f"Hello {name}! This response came from the MCP server running inside Streamlit."

# transform this mcp app into a Starlette app
mcp_app = mcp.http_app()
