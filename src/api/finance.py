import asyncio
import datetime as dt
import httpx
import io

import numpy as np
import pandas as pd
import pytz

from fastapi import APIRouter, BackgroundTasks, Query, HTTPException
from starlette.responses import JSONResponse, Response
import yfinance as yf

# from src.api.system import NodeIdentity # 之後 Log 可以用到
from src.api.gsheet_api import append_df_to_sheet, get_gsheet_df


class BOTRateManager:
    """台灣銀行 (Bank of Taiwan) 匯率管理器"""
    
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    @classmethod
    async def fetch_rates(cls, date: dt.date) -> pd.DataFrame:
        """
        抓取指定日期的台銀匯率
        """
        date_str = date.strftime("%Y-%m-%d")
        url = f'https://rate.bot.com.tw/xrt/all/{date_str}'
        
        try:
            # 1. 非同步抓取網頁內容 (verify=False 處理 SSL 問題)
            async with httpx.AsyncClient(headers=cls._headers, verify=False, timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.text

            # 2. 解析 HTML (pd.read_html 是同步阻塞，小表格可用，大表格建議放執行緒)
            # 使用 io.StringIO 避免警告
            dfs = pd.read_html(io.StringIO(content))
            if not dfs:
                return pd.DataFrame()
            
            df = dfs[0]
            if len(df) <= 1: # 只有標題或查無資料
                return pd.DataFrame()

            # 3. 資料清洗 (依據你原本的邏輯優化)
            df = df.iloc[:, :5]
            df.columns = ['幣別', '現金買入', '現金賣出', '即期買入', '即期賣出']
            
            # 正則提取：例如 "美金 (USD) 美金 (USD)" -> "美金 (USD)"
            df['幣別'] = df['幣別'].str.extract(r'(\w+ \(\w+\))', expand=False)
            
            # 轉換為數字，無法轉換的會變成 NaN            
            cols = ['現金買入', '現金賣出', '即期買入', '即期賣出']
            for col in cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].replace({np.nan: None})
                # df[col] = df[col].apply(lambda x: f'{x:.3f}')
            # 加上日期標籤
            df["日期"] = date_str
            
            print('DEBUG fetch_rates')
            print(df.dtypes)
            return df

        except Exception as e:
            print(f"   ❌ [BOT Rate] 抓取失敗 ({date_str}): {e}")
            return pd.DataFrame()

class TradingCalendar:
    """交易日曆管理器：負責判斷台股交易日期"""
    
    TZ = pytz.timezone('Asia/Taipei')
    
    @classmethod
    def get_now_taipei(cls):
        return dt.datetime.now(cls.TZ)
    
    @classmethod
    async def get_trading_days(cls, n: int = 1) -> list[str]:
        """
        取得最近 N 個交易日期 (最新的在索引 0)
        優先順序：TaiwanIndex API -> Yahoo Finance (備援)
        """
        try:
            # 優先嘗試 TaiwanIndex API (較穩定且格式標準)
            return await cls._fetch_from_taiwan_index(n)
        except Exception as e:
            print(f"   ⚠️ TaiwanIndex 抓取失敗: {e}，切換至 Yahoo Finance 備援")
            return await cls._fetch_from_yahoo(n)
    
    @classmethod
    async def _fetch_from_taiwan_index(cls, n: int) -> list[str]:
        """從台灣指數公司抓取日期
        
        Note:
        https://backend.taiwanindex.com.tw/api/indexes/t00/records?start=2022-02-01&end=2026-05-18
        """
        url = 'https://backend.taiwanindex.com.tw/api/indexes/t00/records'
        now = cls.get_now_taipei()
        
        # 參數設定
        params = {
            'start': '2022-02-01', # (now - dt.timedelta(days=60)).strftime('%Y-%m-%d'), # 抓兩個月保險
            'end': now.strftime('%Y-%m-%d')
        }
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # 原始資料是 [舊 -> 新]，我們反轉它 [新 -> 舊]
            all_dates = [pd.Timestamp(i).strftime('%Y-%m-%d') for i in data['data']['labels'][::-1]]
            if len(all_dates) > 0:
                latest_in_data = dt.datetime.strptime(all_dates[0], '%Y-%m-%d').date()
                if latest_in_data == now.date() and now.hour < 16:
                    all_dates = all_dates[1:]
            return all_dates[:n]
        
        @classmethod
        async def _fetch_from_yahoo(cls, n: int) -> list[str]:
            """從 Yahoo Finance 抓取 (使用 yfinance)"""
            # yfinance 是同步阻斷，需跑在線程中
            def sync_download():
                df = yf.download('2330.tw', period='1mo', progress=False)
                if df.empty:
                    print('yfinance 無結果，需用深度方法執行')
                    return []
                # 處理 Multi-index 欄位 (新版 yf)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                return df.index.strftime('%Y-%m-%d').tolist()[::-1]

            all_dates = await asyncio.to_thread(sync_download)
            
            now = cls.get_now_taipei()
            if len(all_dates) > 0:
                latest_in_data = dt.datetime.strptime(all_dates[0], '%Y-%m-%d').date()
                if latest_in_data == now.date() and now.hour < 16:
                    all_dates = all_dates[1:]
            return all_dates[:n]

# --- API 端點 ---
router = APIRouter(prefix="/finance", tags=["匯率相關"]) # 定義標籤方便在文件分類

@router.get("/bot-rates")
async def get_bot_rates_api(
    # 將 Query(...) 改成 Query(None)，代表選填
    date: str = Query(None, description="日期格式 YYYY-MM-DD"),
    format: str = Query("json", description="回傳格式: json 或 parquet")
):
    """
    API 端點：取得當日台銀匯率 (回傳 JSON 或 Parquet)
    參數：
      - date(選填)：如 2026-05-15
      - format(選填)：預設 json
    """
    if date is None:
        # date = dt.date.today()
        # tz_taipei = pytz.timezone('Asia/Taipei')
        # taipei_time = dt.datetime.now(tz_taipei)
        # if 7 < taipei_time.hour < 16 and taipei_time.weekday() < 5:
        #     # 平日, 未收盤
        #     date -= dt.timedelta(days=1)
        # date = date.strftime("%Y-%m-%d")  # 確保 date: str
        
        trading_dates = await TradingCalendar.get_trading_days(1) # list
        date = trading_dates[0]
    try:
        target_date = dt.datetime.strptime(date, "%Y-%m-%d").date()
    except Exception as err:
        print(f'[Error] {err=}')
        raise HTTPException(status_code=400, detail="Invalid date format")

    df = await BOTRateManager.fetch_rates(target_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"查無 {date} 的匯率資料")
    # 決定回傳格式 (預設 JSON)
    if format == "parquet":
        output = io.BytesIO()
        df.to_parquet(output, index=False) # # Parquet 本身支援 NaN，所以不用換
        # return Response(output.getvalue(), media_type="application/x-parquet")
        return Response(
            output.getvalue(),
            media_type="application/x-parquet",
            headers={"Content-Disposition": f"attachment; filename=taiwan_rate.parquet"}
        )

    # --- 處理 NaN 問題 ---
    # 若使用 df.to_dict() 要處理 NaN 的問題, 這份匯率表有不少地方 NaN
    # 將 NaN 替換為 None (在 JSON 中會變成 null)
    # clean_df = df.replace({float('nan'): None})
    # return JSONResponse(clean_df.to_dict(orient="records"))
    
    # 直接用 pandas 轉成 JSON 字串，它會自動處理 NaN -> null
    # orient="records" 會產生 [{col:val}, {col:val}] 的格式
    # force_ascii=False 確保中文字不會被轉成編碼碼位 (Unicode Escapes)
    # 可直接回傳 List[Dict]，FastAPI 會自動幫你轉 JSON (且處理好 NaN 為 null) 或者繼續用 df.to_json
    json_str = df.to_json(orient="records", force_ascii=False)
    return Response(content=json_str, media_type="application/json")

@router.get("/trading-days")
async def get_trading_days_api(
    n: int = Query(1, ge=1, le=1000, description="取得最近 N 個交易日")
):
    """取得台股交易日清單 (新到舊)"""
    dates = await TradingCalendar.get_trading_days(n)
    if not dates:
        raise HTTPException(status_code=500, detail="無法獲取交易日資訊")
    return {"count": len(dates), "dates": dates}

@router.get("/latest-trading-day")
async def get_latest_trading_day_api():
    """取得最新一個已收盤的交易日"""
    dates = await TradingCalendar.get_trading_days(1)
    if not dates:
        raise HTTPException(status_code=500, detail="無法獲取交易日資訊")
    return {"date": dates[0]}

# --- 更新匯率資訊 ---
async def update_historical_rates_task(start_date: dt.date, end_date: dt.date, sheet_id: str, sheet_name: str):
    """
    背景任務：迴圈抓取並寫入匯率
    """
    current = start_date
    success_count = 0
    
    while current <= end_date:
        # 1. 呼叫我們之前寫好的爬蟲
        df = await BOTRateManager.fetch_rates(current)
        
        if not df.empty:
            # 2. 呼叫 gsheet_api 的寫入功能
            success = await append_df_to_sheet(sheet_id, sheet_name, df)
            if success:
                success_count += 1
                print(f"   ✅ 已完成 {current} 的資料寫入")
        
        current += dt.timedelta(days=1)
        # 稍微停頓，避免被 Google API 或台銀封鎖 IP
        await asyncio.sleep(1) 
    
    print(f"   🏁 批次寫入結束，成功更新 {success_count} 天的資料")

# --- API 端點 ---

@router.post("/backfill-rates")
async def backfill_update_gsheet_rates(
    start_date: str = Query(..., description="開始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="結束日期 YYYY-MM-DD"),
    sheet_id: str = Query("1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE"),
    sheet_name: str = Query("Rate_API"),
    background_tasks: BackgroundTasks = None # FastAPI 自動注入
):
    """
    觸發歷史匯率更新至 Google Sheets
    Note:
      - 按給定的 start_date ~ end_date 日期抓資料並寫入
    """
    try:
        s_dt = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
        e_dt = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if s_dt > e_dt:
        raise HTTPException(status_code=400, detail="Start date cannot be later than end date")

    # 使用 BackgroundTasks 執行，立刻回傳給前端，不讓前端等
    background_tasks.add_task(update_historical_rates_task, s_dt, e_dt, sheet_id, sheet_name)
    
    return {
        "status": "accepted",
        "message": f"已啟動從 {start_date} 到 {end_date} 的更新任務，請稍後查看 Google Sheet。"
    }

@router.post("/cron-sync-rates")
async def cron_sync_rates_to_gsheet(
    background_tasks: BackgroundTasks,
    sheet_id: str = Query("1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE"),
    sheet_name: str = Query("Rate_API")
):
    """
    自動檢查機制：比對 GSheet 最新日期與市場交易日，視需要啟動同步
    
    Note:
      - 適合讓 scheduler 使用
    """
    # 1. 取得市場最新交易日 (由我們的大腦 TradingCalendar 提供)
    trading_dates = await TradingCalendar.get_trading_days(1)
    if not trading_dates:
        raise HTTPException(status_code=500, detail="無法取得市場交易日")

    # 轉為 date 物件方便比較
    trade_day = dt.datetime.strptime(trading_dates[0], "%Y-%m-%d").date()

    # 2. 取得 GSheet 現有資料 (利用 gsheet_api 的讀取功能)
    df_gsheet = await get_gsheet_df(sheet_id, sheet_name)

    if df_gsheet.empty:
        # # 如果是空的，預設補最近 7 天
        # start_date = trade_day - dt.timedelta(days=7)
        # print(f"⚠️ GSheet 為空，準備從 {start_date} 開始補齊")
        raise HTTPException(status_code=400, detail="gsheet 資料表為空")
    else:
        # 3. 實作你的舊專案邏輯：找出 GSheet 裡的最新日期
        # 確保 '日期' 欄位是字串且格式統一，取第一筆 (假設已排序)
        # 這裡我們用更穩健的寫法：直接找 max()
        gsheet_latest_str = df_gsheet['日期'].max()
        gsheet_date = dt.datetime.strptime(gsheet_latest_str, "%Y-%m-%d").date()

        # 4. 判斷是否需要更新
        diff_days = (trade_day - gsheet_date).days

        if diff_days >= 1:
            start_date = gsheet_date + dt.timedelta(days=1)
            print(f"🚀 [Auto Sync] 偵測到落後 {diff_days} 天，準備從 {start_date} 更新至 {trade_day}")
        else:
            return {
                "status": "up-to-date",
                "message": f"資料已是最新 (GSheet: {gsheet_date}, 市場: {trade_day})",
                "latest_date": str(gsheet_date)
            }

    # 5. 啟動背景更新任務 (複用我們之前寫好的 update_historical_rates_task)
    background_tasks.add_task(
        update_historical_rates_task, 
        start_date, 
        trade_day, 
        sheet_id, 
        sheet_name
    )

    return {
        "status": "syncing",
        "message": f"已啟動同步任務：從 {start_date} 至 {trade_day}",
        "diff_days": (trade_day - start_date).days + 1
    }
