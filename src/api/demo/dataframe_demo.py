import io
import numpy as np
import pandas as pd
from starlette.responses import JSONResponse, Response

# 1.1f DataFrame as JSON
async def dataframe_json_demo(request):
    """Return a DataFrame serialized as JSON."""
    df = pd.DataFrame({
        "Ticker": ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"],
        "Price": [189.5, 145.8, 402.1, 785.2, 195.4],
        "Market Cap": ["2.95T", "1.79T", "3.01T", "1.94T", "617.5B"],
        "Rating": ["Buy", "Hold", "Buy", "Strong Buy", "Hold"]
    })
    # 將 DF 轉為 records 格式的 list [{}, {}, {}]
    data = df.to_dict(orient="records")
    return JSONResponse(data)


# 1.1g DataFrame as CSV (For Raw Export)
async def dataframe_csv_demo(request):
    """Return a DataFrame serialized as CSV."""
    df = pd.DataFrame({
        "Date": ["2026-05-01", "2026-05-02"],
        "Value": [100, 200]
    })
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    return Response(stream.getvalue(), media_type="text/csv")


# 1.1h Multi-sheet Excel Response
async def excel_response_demo(request):
    """Generate an Excel file with multiple sheets in memory."""
    # 建立第一份數據：科技股
    df_tech = pd.DataFrame({
        "Company": ["Apple", "Microsoft", "Google"],
        "Sector": ["Hardware", "Software", "Search"],
        "Revenue": [383, 211, 282]
    })
    
    # 建立第二份數據：加密貨幣
    df_crypto = pd.DataFrame({
        "Asset": ["Bitcoin", "Ethereum", "Solana"],
        "Price": [65000, 3500, 140],
        "Trend": ["Bullish", "Neutral", "Bullish"]
    })

    # 使用 BytesIO 作為二進位緩衝區 (因 Excel 不是純文字)
    output = io.BytesIO()
    
    # 使用 pd.ExcelWriter 將多個 DF 寫入同一個檔案的不同 Sheet
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_tech.to_excel(writer, sheet_name='Tech_Stocks', index=False)
        df_crypto.to_excel(writer, sheet_name='Crypto_Assets', index=False)
    
    # 取得二進位數據
    excel_data = output.getvalue()
    
    # 回傳 Response，注意 media_type 必須是 Excel 的標準格式
    return Response(
        excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=report.xlsx"}
    )


# 1.1i Large Parquet/Arrow Response
async def stock_data_parquet_demo(request):
    """Generate 100k rows of mock stock data and return as Parquet.
    
    Apache Arrow 是 Streamlit 內部底層使用的資料格式，而 Parquet 則是這種格式的磁碟存儲版本。它們最大的優點是
    列式存儲 (Columnar Storage)
    """
    # 模擬大量資料：10萬筆成交紀錄
    num_rows = 100000
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2026-04-01", periods=num_rows, freq="s"),
        "symbol": np.random.choice(["AAPL", "NVDA", "TSLA", "MSFT"], num_rows),
        "price": np.random.uniform(100, 800, num_rows).round(2),
        "volume": np.random.randint(1, 1000, num_rows)
    })

    # 使用 BytesIO 作為二進位緩衝
    output = io.BytesIO()
    
    # 將 DataFrame 寫入 Parquet 格式 (預設使用 pyarrow 引擎)
    # compression='snappy' 可以讓體積變小但速度依然很快
    df.to_parquet(output, index=False, engine='pyarrow', compression='snappy')
    
    parquet_data = output.getvalue()
    
    # 回傳二進位流，MIME type 通常使用 application/octet-stream 或專用的 parquet 型別
    return Response(
        parquet_data,
        media_type="application/x-parquet",
        headers={"Content-Disposition": "attachment; filename=stock_data.parquet"}
    )
