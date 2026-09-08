
import asyncio
import io
from unittest.mock import patch  # , MagicMock  # 模擬

import pandas as pd
import pytest
import pytest_asyncio

from starlette.testclient import TestClient
# from starlette.applications import Starlette
# from starlette.routing import Route

# 要測試的對象
from src.api.gsheet_api import (
    get_gsheet_df, _GSHEET_CACHE,
    get_sheets_batch,
    append_df_to_sheet
)
from src.api.framework.lifecycle import gs_manager

# 測試用的試算表資訊
TEST_SPREADSHEET_ID = '1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE'
TEST_SHEET_NAME = 'Rate'

# # --- 1. 配置測試用的 Starlette App ---
# # 這樣我們才能測試 pull_sheet_as_parquet 這個 Route Handler
# api_app = Starlette(routes=[
#     Route("/parquet", pull_sheet_as_parquet),
#     Route("/batch-warmup", trigger_batch_warmup),
# ])
from src.api.framework.interop import fastapi as api_app  # 直接拿 FastAPI 來測 # noqa: E402


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_gs_manager():
    """
    測試前的準備工作：確保 Google 連線已建立
    """
    print("\n   🚀 [Setup] 正在初始化 Google 連線...")
    if gs_manager.client is None:
        await gs_manager.connect()
    yield
    print("\n   🧹 [Teardown] 測試結束")

# --- 2. 測試底層函式 get_gsheet_df ---


@pytest.mark.asyncio
async def test_get_gsheet_df():
    """
    驗證是否能成功抓取資料並回傳 DataFrame，且快取機制運作正常
    """
    print(f"\n   🔍 測試 get_gsheet_df ({TEST_SHEET_NAME})...")

    df = await get_gsheet_df(TEST_SPREADSHEET_ID, "Rate_API")
    df = df.set_index(['日期', '幣別'])
    df = df.apply(pd.to_numeric, errors='coerce')  # 一次將四個欄位設成 float
    df.sort_index(ascending=False, inplace=True)  # 讓新的在上面

    print('取得 gsheet 匯率資料(全部)')
    print(df.head())

    assert isinstance(df, pd.DataFrame), "回傳應為 DataFrame"
    assert not df.empty, "DataFrame 不應為空"
    assert len(df.columns) > 0, "應包含資料欄位"
    print(f"   ✅ 成功抓取 {len(df)} 筆資料")

    with TestClient(api_app) as client:
        resp = client.get("/finance/latest-trading-day")
        date_str = resp.json()['date']
        # # 轉為 date 物件方便比較
        # trade_day = dt.datetime.strptime(date_str, "%Y-%m-%d").date()

        # 此時索引已是 Multi-Index
        df_today = df.xs(key=date_str, level=0, axis=0)
        assert not df_today.empty, "DataFrame 不應為空"

# --- 3. 測試 API 端點 pull_sheet_as_parquet ---


@pytest.mark.asyncio
async def test_pull_sheet_as_parquet_api():
    """
    使用 TestClient 模擬 HTTP 請求，驗證回傳是否為正確的 Parquet 格式
    """
    print("\n   🔍 測試 API 端點: /api/gsheet/parquet ...")
    # 注意：TestClient 內部會處理非同步 loop
    with TestClient(api_app) as client:
        # 帶入 Query Parameters
        params = {"sheet_id": TEST_SPREADSHEET_ID, "sheet_name": TEST_SHEET_NAME}
        response = client.get("/gsheet/parquet", params=params)

        # 驗證 HTTP 狀態碼
        assert response.status_code == 200

        # 驗證 Content-Type
        assert response.headers["content-type"] == "application/x-parquet"

        # 驗證內容是否能被 pandas 正確讀取為 Parquet
        df_received = pd.read_parquet(io.BytesIO(response.content))
        assert not df_received.empty, "還原後的 DataFrame 不應為空"
        print(f"   ✅ API 回傳值驗證成功，資料筆數: {len(df_received)}")

# --- 4. 測試錯誤處理 ---


@pytest.mark.asyncio
async def test_get_gsheet_df_invalid_id():
    """
    測試當 ID 錯誤時，函式是否能優雅處理 (回傳空 DF)
    """
    print("\n   🔍 測試無效 ID 的錯誤處理...")
    invalid_id = "this-is-a-wrong-id"
    df = await get_gsheet_df(invalid_id, TEST_SHEET_NAME)

    assert df.empty, "無效 ID 應回傳空 DataFrame"
    print("   ✅ 錯誤處理驗證成功")


@pytest.mark.asyncio
async def test_get_gsheet_df_permission_denied():
    """
    測試情境：當 Google Sheet 存在，但 Service Account 沒有讀取權限時 (403 Forbidden)
    """
    print("\n   🔍 測試權限不足 (PermissionError) 的處理...")

    # 用 patch 來「暫時」替換 gs_manager.client 的行為
    # 讓 open_by_key 被呼叫時，直接噴出 PermissionError
    with patch.object(gs_manager.client, 'open_by_key', side_effect=PermissionError("Mocked Permission Denied")):

        # 手動清空快取, 以免 get_gsheet_df 直接回傳它
        _GSHEET_CACHE.clear()
        # 呼叫你的函式
        df = await get_gsheet_df(TEST_SPREADSHEET_ID, TEST_SHEET_NAME)

        # 根據你目前的 gsheet_api.py 邏輯：
        # 遇到 Exception 會重試 3 次，最後回傳空的 DataFrame
        assert df.empty, "權限不足時應回傳空 DataFrame"
        print("   ✅ 權限不足捕捉成功，且已安全回傳空資料")


@pytest.mark.asyncio
async def test_get_sheets_batch():
    """
    測試批次下載器：一次抓取多個工作表並驗證結果
    """
    print("\n   🔍 測試批次下載器 (Batch Fetcher)...")

    # 定義要抓取的多個工作表 (假設你的試算表有這兩個表)
    target_sheets = ["Rate", "ETF基本", "ETF基本累計"]

    # 執行批次抓取
    results = await get_sheets_batch(TEST_SPREADSHEET_ID, target_sheets)

    # 檢查結果
    assert isinstance(results, dict), "回傳結果應為字典"
    assert len(results) == len(target_sheets), f"回傳數量應為 {len(target_sheets)}"

    for name in target_sheets:
        assert name in results, f"字典中應包含 {name}"
        assert isinstance(results[name], pd.DataFrame), f"{name} 應為 DataFrame"
        print(f"   ✅ 工作表 [{name}] 驗證成功，筆數: {len(results[name])}")


@pytest.mark.asyncio
async def test_get_sheets_batch_with_cache():
    """
    驗證批次下載器是否能正確觸發快取 (不重複抓取)
    """
    print("\n   🔍 測試批次下載器的快取機制...")

    # 1. 先確保快取中有資料 (單次抓取)
    await get_gsheet_df(TEST_SPREADSHEET_ID, "Rate")

    cache_key = (TEST_SPREADSHEET_ID, "Rate")
    assert cache_key in _GSHEET_CACHE, f"{cache_key} 應該要在 _GSHEET_CACHE 中"

    # 2. 執行批次抓取，觀察終端機是否印出 "⚡ [Cache Hit]"
    # 這裡我們觀察回傳時間是否極短即可
    start_time = asyncio.get_event_loop().time()
    results = await get_sheets_batch(TEST_SPREADSHEET_ID, ["Rate"])
    duration = asyncio.get_event_loop().time() - start_time

    assert not results["Rate"].empty
    assert duration < 0.1, "快取命中時，反應時間應小於 0.1 秒"
    print(f"   ✅ 快取命中驗證成功，耗時: {duration:.4f}s")


@pytest.mark.asyncio
async def test_trigger_batch_warmup_api():
    """
    測試 API 端點: /api/gsheet/batch-warmup
    驗證批次預熱是否能正確回傳 JSON 統計資訊
    """
    print("\n   🔍 測試 API 端點: /api/gsheet/batch-warmup ...")

    with TestClient(api_app) as client:
        # 傳入 ID 進行測試
        params = {"sheet_id": TEST_SPREADSHEET_ID}
        response = client.get("/gsheet/batch-warmup", params=params)

        # 1. 驗證狀態碼
        assert response.status_code == 200

        # 2. 驗證 JSON 內容
        data = response.json()
        assert data["status"] == "success"
        assert "duration_seconds" in data
        assert isinstance(data["sheets_loaded"], dict)

        # 3. 驗證指定的 Sheet 是否出現在回傳清單中
        loaded_sheets = data["sheets_loaded"]
        assert "Rate" in loaded_sheets

        print(f"   ✅ 批次預熱 API 驗證成功，耗時: {data['duration_seconds']}s")
        print(f"   📊 載入統計: {loaded_sheets}")


@pytest.mark.asyncio
async def test_append_df_to_sheet():
    """
    測試寫入功能：建立一個小 DF 並寫入試算表
    """
    print("\n   🔍 測試 GSheet 追加寫入功能...")
    # 建立測試資料
    test_df = pd.DataFrame([
        {"幣別": "測試美金 (USD)",
         "現金買入": 31.26, "現金賣出": 31.93,
         "即期買入": 31.61, "即期賣出": 31.71,
         "日期": "2026-04-30"}
    ])

    success = await append_df_to_sheet(TEST_SPREADSHEET_ID, "Rate_API_TEST", test_df)

    assert success is True
    print("   ✅ 寫入測試成功，請檢查 Google Sheet 末尾是否有 '測試美金' 資料。")

# # --- X. 補上你要求的 if __name__ == "__main__" ---
# if __name__ == "__main__":
#     # 執行 python src/tests/test_gsheet_api.py 此時 __name__ == '__main__'
#     # 執行 pytest ... 時, pytest import 此檔案, 此時 __name__ == 'src.tests.test_gsheet_api'
#     async def run_manual_test():
#         print("🛠️ 開始手動撥測...")
#         await gs_manager.connect()
#         df = await get_gsheet_df(TEST_SPREADSHEET_ID, TEST_SHEET_NAME)
#         print(f"結果：抓到 {len(df)} 筆資料")
#     asyncio.run(run_manual_test())
