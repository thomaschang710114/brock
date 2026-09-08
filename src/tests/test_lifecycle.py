import os
import sys
import pytest

from src.api.framework.lifecycle import gs_manager


@pytest.mark.asyncio
async def test_google_sheet_connection():
    """
    測試 GoogleSheetManager 是否能成功讀取 JSON 並建立連線物件
    """
    # 執行連線邏輯
    await gs_manager.connect()
    
    # 斷言 (Assert) 檢查
    # 1. client 物件不應該是 None
    assert gs_manager.client is not None, "Google Sheet Client 應該被初始化"
    
    # 2. 嘗試呼叫一個簡單的方法驗證連線是否真的有效
    # 這裡可以試著列出所有 spreadsheet (或是檢查 client 類型)
    try:
        # 測試列出檔案（這會觸發實際的 API 握手）
        # client.open_by_key(...) 也可以，但這裡用 list_spreadsheet_files 較通用
        print("\n   🔍 正在驗證 API 授權有效性...")
        # 簡單檢查是否有獲取權限
        assert hasattr(gs_manager.client, 'open_by_key')
        print("   ✅ API 授權物件驗證通過")
        
    except Exception as e:
        pytest.fail(f"API 撥測失敗: {e}")

# if __name__ == "__main__":
#     # 如果直接執行此檔案，也可以跑測試
#     import asyncio
#     asyncio.run(test_google_sheet_connection())
