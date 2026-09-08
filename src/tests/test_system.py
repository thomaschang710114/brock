import pytest
from starlette.requests import Request

from src.api.framework.system import NodeIdentity

@pytest.mark.asyncio
async def test_server_info():
    """驗證伺服器端資訊是否正確生成且具備快取功能"""
    info1 = await NodeIdentity.get_server_info()
    assert "ip" in info1
    assert "mac" in info1
    
    info2 = await NodeIdentity.get_server_info()
    # 驗證快取：兩個物件應該內容完全相同
    assert info1 == info2
    print(f"\n   ✅ Server Info: {info1['node']} ({info1['ip']})")

def test_client_info_mock():
    """模擬一個 Request 來驗證用戶端資訊提取"""
    # 模擬 Starlette 的 Request 物件
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": [
            (b"user-agent", b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"),
            (b"x-forwarded-for", b"1.2.3.4"),
        ],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope=scope)
    
    client_info = NodeIdentity.get_client_info(request)
    assert client_info["client_ip"] == "1.2.3.4"
    assert "Macintosh" in client_info["user_agent"]
    print(f"\n   ✅ Client Info Mock 驗證成功")
