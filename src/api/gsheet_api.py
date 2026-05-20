import asyncio
import io
import time

from gspread.exceptions import SpreadsheetNotFound
import numpy as np
import pandas as pd

from fastapi import APIRouter, Query, HTTPException
from starlette.responses import Response, JSONResponse
from src.api.lifecycle import gs_manager

# 處理從 Google Sheets 抓取資料並轉換格式的邏輯

# 簡單的 API 層級快取：{ (spreadsheet_key, sheet_name): (timestamp, dataframe) }
_GSHEET_CACHE = {}
CACHE_TTL = 6 * 3600  # 6 小時


async def get_gsheet_df(spreadsheet_key: str, sheet_name: str, ignore_format: list = []):
    """
    核心邏輯：從 gspread 抓取資料並轉為 DataFrame (帶快取)
    """
    # # 原始版本:
    # cache_key = (spreadsheet_key, sheet_name)
    # now = time.time()

    # # 1. 檢查快取
    # if cache_key in _GSHEET_CACHE:
    #     ts, df = _GSHEET_CACHE[cache_key]
    #     if now - ts < CACHE_TTL:
    #         print(f"   ⚡ [Cache Hit] 讀取 Google Sheet: {sheet_name}")
    #         return df

    # # 2. 抓取資料 (取代原本的 while 迴圈，改用帶上限的重試)
    # print(f"   🌐 [API Call] 正在從 Google Sheet 抓取資料: {sheet_name}")
    # retry_count = 0
    # max_retries = 3
    
    # while retry_count < max_retries:
    #     try:
    #         # gs_manager.client 已經在 lifecycle.py 的 lifespan 中初始化
    #         worksheet = gs_manager.client.open_by_key(spreadsheet_key).worksheet(sheet_name)
    #         data = worksheet.get_all_records(numericise_ignore=ignore_format)
    #         df = pd.DataFrame(data)
            
    #         if not df.empty:
    #             # 存入快取
    #             _GSHEET_CACHE[cache_key] = (now, df)
    #             return df
    #     except Exception as err:
    #         retry_count += 1
    #         print(f"   ⚠️ [Retry {retry_count}] GSheet Error: {err}")
    #         await asyncio.sleep(2) # 異步等待，不阻塞伺服器

    # return pd.DataFrame() # 若失敗回傳空 DF

    # 重構後只剩兩行
    _, df = await fetch_single_sheet_task(spreadsheet_key, sheet_name, ignore_format)
    return df


# --- API 端點 ---
router = APIRouter(prefix="/gsheet", tags=["Google Sheets 數據庫"])


@router.get("/parquet")
async def pull_sheet_as_parquet(
    sheet_id: str = Query("1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE", description="Spreadsheet ID"),
    sheet_name: str = Query("Rate", description="工作表名稱")
):
    """
    端點：將 Google Sheet 資料轉為高效 Parquet 格式回傳
    參數：
      - sheet_id(選填)
      - sheet_name(選填)
    """
    print(f'收到參數: {sheet_id=}, {sheet_name=}')
    df = await get_gsheet_df(sheet_id, sheet_name)
    
    if df.empty:
        raise HTTPException(status_code=500, detail="無法從 Google Sheets 取得資料")

    # --- [型別清洗邏輯] ---
    # 將所有空字串 '' 替換為真正的 np.nan (Parquet 接受浮點數欄位裡有 NaN)
    df = df.replace('', np.nan)

    # 轉為 Parquet 二進位流
    output = io.BytesIO()
    df.to_parquet(output, index=False, engine='pyarrow')
    
    return Response(
        output.getvalue(),
        media_type="application/x-parquet",
        headers={"Content-Disposition": f"attachment; filename={sheet_name}.parquet"}
    )

# --- 批次下載器 ---

async def fetch_single_sheet_task(spreadsheet_key: str, sheet_name: str, ignore_format: list = []):
    """
    內部的原子任務：抓取單一工作表，專供並發呼叫。
    """
    cache_key = (spreadsheet_key, sheet_name)
    now = time.time()
    
    # 1. 優先檢查快取
    if cache_key in _GSHEET_CACHE:
        ts, df = _GSHEET_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            print(f"   ⚡ [Cache Hit] 批次任務命中: {sheet_name}")
            return sheet_name, df
    
    # 2. 快取失效或不存在，才去抓取
    # 這裡使用 to_thread 是為了不阻塞主線程的 Event Loop, 因 gspread 本身是同步的函式庫, 在非同步環境要用 asyncio.to_thread 來跑它
    def sync_fetch():
        print(f"   🌐 [sync_fetch] 正在抓取工作表: {sheet_name}")
        worksheet = gs_manager.client.open_by_key(spreadsheet_key).worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records(numericise_ignore=ignore_format))

    try:
        # 使用 to_thread 避免同步 IO 卡住異步循環
        df = await asyncio.to_thread(sync_fetch)
        if not df.empty:
            _GSHEET_CACHE[cache_key] = (now, df)
        return sheet_name, df
    # except SpreadsheetNotFound:
    #     print(f"   ❌ [Error] 找不到該試算表 ID: {spreadsheet_key}")
    #     return sheet_name, pd.DataFrame() # 找不到就直接放棄，不用重試
    # except PermissionError:
    #     print(f"   ⛔ [Error] 權限不足，請將試算表分享給 Service Account")
    #     return sheet_name, pd.DataFrame() # 沒權限也直接放棄
    except Exception as e:
        print(f"   ❌ [Batch] 抓取 {sheet_name} 失敗: {e}")
        return sheet_name, pd.DataFrame()

async def get_sheets_batch(spreadsheet_key: str, sheet_names: list):
    """
    批次下載器：同時抓取多個工作表並存入快取預熱。
    """
    print(f"   🚀 [Batch] 開始並發下載: {sheet_names}")
    
    # 建立任務清單
    tasks = [fetch_single_sheet_task(spreadsheet_key, name) for name in sheet_names]
    
    # 使用 gather 同時執行所有任務
    results = await asyncio.gather(*tasks)
    
    # 轉成字典回傳 { 'Sheet1': df1, 'Sheet2': df2 }
    return {name: df for name, df in results}

# --- 批次下載器 API 端點 ---
@router.get("/batch-warmup")
async def trigger_batch_warmup(
    sheet_id: str = Query(..., description="要預熱的 Spreadsheet ID")
):
    """
    API 端點：手動觸發批次預熱，將常用數據一次載入快取。
    範例:
      - http://localhost:8501/api/gsheet/batch-warmup?sheet_id=你的ID
      - http://localhost:8501/api/gsheet/batch-warmup?sheet_id=1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE
    """
    # 假設我們預設要預熱這三個表
    target_sheets = []
    if sheet_id == '1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE':
        target_sheets = ["Rate", "blogs", "ETF買回清單", "ETF基本", "ETF基本累計", "ETF全市況累計"]
    
    start_time = time.time()
    results = await get_sheets_batch(sheet_id, target_sheets)
    duration = time.time() - start_time
    
    summary = {name: len(df) for name, df in results.items()}
    # 直接回傳 dict，FastAPI 會自動轉 JSON
    return {
        "status": "success",
        "duration_seconds": round(duration, 2),
        "sheets_loaded": summary
    }

# --- 寫入 google sheet ---
async def append_df_to_sheet(spreadsheet_key: str, sheet_name: str, df: pd.DataFrame):
    """
    將 DataFrame 的資料追加 (Append) 到指定的 Google Sheet 中
    """
    if df.empty:
        return False

    # 轉換為 list of lists (不含表頭，因為是追加)
    data_to_append = df.values.tolist()

    # --- [帶重試機制的寫入邏輯] ---
    retry_count = 0
    max_retries = 5

    def sync_append():
        print(f"   📝 [GSheet Write] 正在寫入 {len(data_to_append)} 筆資料到 {sheet_name}...")
        worksheet = gs_manager.client.open_by_key(spreadsheet_key).worksheet(sheet_name)
        # value_input_option='USER_ENTERED' 讓 GSheet 自動識別數字/日期格式
        return worksheet.append_rows(data_to_append, value_input_option='USER_ENTERED')

    while retry_count < max_retries:
        try:
            await asyncio.to_thread(sync_append)
            print(f"   ✅ [GSheet] 成功追加 {len(data_to_append)} 筆資料到 {sheet_name}")

            # 寫入成功後，建議清除該表的讀取快取，確保下次讀取到最新的
            cache_key = (spreadsheet_key, sheet_name)
            _GSHEET_CACHE.pop(cache_key, None)
            return True
        except Exception as err:
            retry_count += 1
            print(f"   ⚠️ [GSheet Retry {retry_count}] 發生錯誤: {err}")
            # 如果是 API 配額問題，等待時間加長 (指數退避)
            await asyncio.sleep(5 * retry_count) 
            continue

    print(f"   ❌ [GSheet] 寫入失敗，已達重試上限。")
    return False
    
