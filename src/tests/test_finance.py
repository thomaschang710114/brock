import datetime as dt
import io
import re
import pandas as pd
import pytest
import pytest_asyncio
import pytz

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from src.api.finance import BOTRateManager, TradingCalendar
from src.api.gsheet_api import get_gsheet_df

# # 建立測試用的 Starlette App (避免與正式 App 耦合)
# api_app = Starlette(routes=[
#     Route("/bot-rates", get_bot_rates_api)
# ])
from src.api.framework.interop import fastapi as api_app # 直接拿 FastAPI 來測
from src.api.framework.lifecycle import gs_manager


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_gs_manager():
    """
    測試前的準備工作：確保 Google 連線已建立
    """
    print("\n   🚀 [Test Setup] 正在初始化 Finance 測試所需的 Google 連線...")
    if gs_manager.client is None:
        await gs_manager.connect()
    yield
    print("\n   🧹 [Teardown] Finance 測試結束")

@pytest.mark.asyncio
async def test_backfill_update_gsheet_rates_api():
    """
    測試 POST /finance/backfill-rates 端點
    驗證日期參數校驗與背景任務觸發邏輯
    """
    print("\n   🔍 測試更新匯率到 GSheet 的 API 端點 (POST)...")
    with TestClient(api_app) as client:
        resp = client.get("/finance/latest-trading-day")
        date_str = resp.json()['date']
        # 轉為 date 物件方便比較
        trade_day = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        df_gsheet = await get_gsheet_df("1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE", "Rate_API")
        gsheet_latest_str = df_gsheet['日期'].max()
        gsheet_date = dt.datetime.strptime(gsheet_latest_str, "%Y-%m-%d").date()
        
        diff_days = (trade_day - gsheet_date).days
        if diff_days >= 1:
            test_start = gsheet_date + dt.timedelta(days=1)
            print(f"🚀 [Auto Sync] 偵測到落後 {diff_days} 天，準備從 {test_start} 更新至 {trade_day}")
        
            # 1. 測試成功受理情境
            # 我們測試一天的範圍，這會觸發爬蟲與寫入
            test_start = test_start.strftime("%Y-%m-%d") # "2026-05-18"
            test_end = date_str # "2026-05-18"
            
            response = client.post(
                "/finance/backfill-rates",
                params={
                    "start_date": test_start,
                    "end_date": test_end,
                    "sheet_id": "1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE",
                    "sheet_name": "Rate_API"
                }
            )
            
            # 驗證回傳狀態與訊息
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "已啟動" in data["message"]
            print(f"   ✅ API 成功受理更新任務: {data['message']}")
        else:
            print(f"🚀 [Auto Sync] 資料已是最新 {date_str}")

        # 2. 測試日期格式錯誤 (400 HTTPException)
        res_bad_date = client.post(
            "/finance/backfill-rates", 
            params={"start_date": "2026/05/14", "end_date": "2026-05-14"}
        )
        assert res_bad_date.status_code == 400
        assert "Invalid date format" in res_bad_date.json()["detail"]
        print("   ✅ 錯誤格式攔截驗證成功 (400)")

        # 3. 測試日期範圍邏輯錯誤 (開始 > 結束)
        res_range_error = client.post(
            "/finance/backfill-rates", 
            params={"start_date": "2026-05-15", "end_date": "2026-05-04"}
        )
        assert res_range_error.status_code == 400
        assert "Start date cannot be later" in res_range_error.json()["detail"]
        print("   ✅ 日期範圍邏輯錯誤攔截驗證成功 (400)")

@pytest.mark.asyncio
async def test_cron_sync_rates_to_gsheet_api():
    """驗證自動同步邏輯 (不帶日期，由系統自判)"""
    print("\n   🔍 測試自動同步 API (/cron-sync-rates)...")
    with TestClient(api_app) as client:
        response = client.post(
            "/finance/cron-sync-rates",
            params={
                "sheet_id": "1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE",
                "sheet_name": "Rate_API"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 這裡會有兩種結果：
        if data["status"] == "up-to-date":
            print(f"   ✅ 無需同步: {data['message']}")
        elif data["status"] == "syncing":
            print(f"   🚀 需要同步: {data['message']}")
            assert "diff_days" in data

@pytest.mark.asyncio
async def test_fetch_bot_rates_success():
    """測試成功抓取最近一天的匯率
    https://rate.bot.com.tw/xrt/all/2026-05-14
    """
    trading_dates = await TradingCalendar.get_trading_days(1) # list
    trading_date = pd.Timestamp(trading_dates[0])
    df = await BOTRateManager.fetch_rates(trading_date)
    print(f'DEBUG {trading_date=}')
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "幣別" in df.columns
        assert "日期" in df.columns
        # assert df["現金買入"].dtype == 'float64'
        print(f"\n   ✅ 成功抓取台銀匯率: {len(df)} 筆幣別資訊")
    else:
        print("\n   ⚠️ 今日無資料 (可能是非營業日且無存檔)")

@pytest.mark.asyncio
async def test_fetch_bot_rates_invalid_date():
    """測試未來日期的邊界情況"""
    future_date = dt.date.today() + dt.timedelta(days=365)
    df = await BOTRateManager.fetch_rates(future_date)
    assert df.empty
    print("\n   ✅ 未來日期回傳空表，驗證成功")

@pytest.mark.asyncio
async def test_get_bot_rates_api():
    """
    測試 API 端點：驗證 JSON 回傳結構與自動日期邏輯
    """
    print("\n   🔍 測試台銀匯率 API 端點: /api/finance/bot-rates ...")
    
    with TestClient(api_app) as client:
        # 測試不帶日期 (觸發自動判斷)，預設回傳 json
        response = client.get("/finance/bot-rates")
        
        # 如果當天是假日或剛好沒資料，可能會回傳 404，這也是正常的測試路徑
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert "幣別" in data[0]
            assert "現金買入" in data[0]
            # 驗證資料型別是否為數字 (float/int)
            assert isinstance(data[0]["現金買入"], (float, int))
            print(f"   ✅ API JSON 結構驗證通過，範例幣別: {data[0]['幣別']}")
        else:
            # 如果還是 404，這裡會印出來方便除錯
            print(f"   ❌ 測試失敗！狀態碼: {response.status_code}")
            if response.status_code == 404:
                print("   💡 提示：請檢查 finance.py 裡的 router prefix 是否為 '/finance'")

@pytest.mark.asyncio
async def test_get_bot_rates_api_with_params():
    """驗證 API 是否能正確處理 date 參數"""
    print("\n   🔍 測試帶參數的台銀匯率 API...")
    
    with TestClient(api_app) as client:
        # 1. 測試沒帶參數 (會觸發自動日期判斷)
        res_no_param = client.get("/finance/bot-rates")
        if res_no_param.status_code == 200:
            data = res_no_param.json() # list of dicts
            assert "幣別" in data[0]
            print(f"   ✅ 自動日期抓取成功，狀態碼: 200")
        else:
            # 加入的 404 判斷邏輯 (例如測試當天剛好是假日，台銀沒開門)
            assert res_no_param.status_code == 404, f"預期為 200 或 404，但收到: {res_no_param.status_code}"
            error_data = res_no_param.json() # dict
            assert "detail" in error_data, "FastAPI 的 HTTPException 應包含 'detail' 欄位"
            print(f"   ⚠️ 自動日期因假日無資料回傳 404，錯誤訊息: {error_data['detail']}")

        # 2. 測試帶入正確日期 (假設找一個過去的營業日，必有資料)
        test_date = "2026-05-14" 
        res_with_date = client.get("/finance/bot-rates", params={"date": test_date})
        
        # 這裡不一定會 200 (除非台銀那天有開)，但我們要驗證的是邏輯
        if res_with_date.status_code == 200:
            assert res_with_date.json()[0]["日期"] == test_date
            print(f"   ✅ 成功抓取指定日期 {test_date} 的資料")

@pytest.mark.asyncio
async def test_get_bot_rates_parquet_format():
    """
    測試 API 端點：驗證 Parquet 回傳格式
    """
    print("\n   🔍 測試台銀匯率 API 的 Parquet 格式輸出...")

    with TestClient(api_app) as client:
        # 指定格式為 parquet
        params = {
            "date": "2026-05-14", 
            "format": "parquet"
        }
        response = client.get("/finance/bot-rates", params=params)

        # 2. 嚴格斷言：必須是 2026-05-14 且 Content-Type 正確
        assert response.status_code == 200, f"預期回傳 200，但收到 {response.status_code}"
        assert response.headers["content-type"] == "application/x-parquet", "Content-Type 必須為 application/x-parquet"

        # 3. 驗證內容是否能被 pandas 正確讀取為 Parquet
        df_received = pd.read_parquet(io.BytesIO(response.content)) # response.content 內容為二進位資料，因參數接收路徑或 File-like 物件，故用 BytesIO 包裝
        assert isinstance(df_received, pd.DataFrame), "還原後的物件應為 DataFrame"
        assert not df_received.empty, "還原後的 DataFrame 不應為空"
        assert "幣別" in df_received.columns, "DataFrame 應包含 '幣別' 欄位"
        assert "日期" in df_received.columns, "DataFrame 應包含 '日期' 欄位"
        print(f"   ✅ Parquet 格式驗證成功，資料筆數: {len(df_received)}")
        print(f"   📊 欄位清單: {list(df_received.columns)}")

@pytest.mark.asyncio
async def test_get_trading_days_api():
    """驗證交易日 API"""
    with TestClient(api_app) as client:
        # 1. 測試取 5 天
        resp = client.get("/finance/trading-days", params={"n": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dates"]) == 5

        # 驗證日期格式 YYYY-MM-DD
        assert re.match(r"\d{4}-\d{2}-\d{2}", data["dates"][0])
        print(f"   ✅ 交易日 API 測試成功: {data['dates']}")

@pytest.mark.asyncio
async def test_latest_trading_day_api():
    """驗證最新交易日 API"""
    with TestClient(api_app) as client:
        resp = client.get("/finance/latest-trading-day")
        assert resp.status_code == 200
        assert "date" in resp.json()
        
        date_str = resp.json()['date']
        print(f"   📥 收到 API 原始字串: {date_str}")
        # 測試還原為 pd.Timestamp (這是你程式中常用的邏輯)
        ts = pd.Timestamp(date_str)
        assert isinstance(ts, pd.Timestamp), "還原失敗，型別不符"
        assert ts.year >= 2026, "年份解析錯誤"
        
        # 模擬帶 T 的格式: 2026-05-15T00:00:00
        iso_str = f"{date_str}T00:00:00"
        ts_iso = pd.Timestamp(iso_str)
        assert ts_iso.date() == ts.date(), "ISO 格式與日期格式還原不一致"

        print(f"   ✅ 最新交易日: {date_str}")
