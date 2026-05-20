from io import BytesIO, StringIO
import time
import requests

import numpy as np
import pandas as pd

import streamlit as st

st.title("1. Custom API Routes")
st.caption("Bypassing FastAPI overhead with pure Starlette routes")

api_base_url = st.secrets["api"]["url"]
# 實務上應放 secrets.toml
HEADERS = {"X-API-Key": "super-secret-key-123"}

# --- 1.1a JSON Response ---
st.subheader("📦 JSON Response")
st.markdown("Fetch raw JSON data from `/api/raw-data`.")

if st.button("Fetch Raw Data", key="json"):
    res = requests.get(f"{api_base_url}/api/raw-data", headers=HEADERS)
    st.json(res.json())

st.divider()

# --- 1.1b HTML Response ---
st.subheader("🎨 HTML Response")
st.markdown("Fetch styled HTML from `/api/html-demo` and render with `st.html()`.")

if st.button("Fetch HTML", key="html"):
    res = requests.get(f"{api_base_url}/api/html-demo")
    st.html(res.text)

st.divider()

# --- 1.1c Plain Text Response ---
st.subheader("📝 Plain Text Response")
st.markdown("Fetch plain text from `/api/plain-text`.")

if st.button("Fetch Plain Text", key="plaintext"):
    res = requests.get(f"{api_base_url}/api/plain-text")
    st.code(res.text, language=None)

st.divider()

# --- 1.1d Redirect Response ---
st.subheader("🔀 Redirect Response")
st.markdown("Clicking the link below will trigger a **303 redirect** to my newsletter.")
st.link_button("Test Redirect →", f"{api_base_url}/api/redirect-demo")

st.divider()

# --- 1.1e Path Parameters ---
st.subheader("🔗 Path Parameters")
st.markdown("Starlette routes can extract dynamic segments from the URL.")

col1, col2 = st.columns(2)
with col1:
    user_id = st.text_input("User ID", value="42", key="user_id")
with col2:
    action = st.text_input("Action (optional)", value="profile", key="action")

if st.button("Fetch with Path Params", key="params"):
    if action:
        url = f"{api_base_url}/api/users/{user_id}/{action}"
    else:
        url = f"{api_base_url}/api/users/{user_id}"

    st.caption(f"Calling: `{url}`")
    res = requests.get(url)
    st.json(res.json())

st.divider()

# --- 1.1f DataFrame JSON ---
st.subheader("📊 DataFrame via JSON")
st.markdown("Fetch structured data and display as an interactive table using `st.dataframe()`.")

if st.button("Fetch DF as JSON", key="dfjson"):
    res = requests.get(f"{api_base_url}/api/df-json")
    if res.status_code == 200:
        data = res.json()
        # Streamlit 聰明到可以直接把 list of dict 轉回表格
        st.dataframe(data, width="stretch")
        with st.expander("View Raw JSON Payload"):
            st.json(data)

st.divider()


# --- 1.1g DataFrame CSV ---
st.subheader("📄 DataFrame via CSV")
st.markdown("Fetch raw CSV text from the API. Useful for legacy exports.")

if st.button("Fetch DF as CSV", key="dfcsv"):
    res = requests.get(f"{api_base_url}/api/df-csv")
    if res.status_code == 200:
        csv_text = res.text
        st.text_area("Raw CSV Output", csv_text, height=150)
        
        # 示範如何轉回 dataframe 顯示
        df_from_csv = pd.read_csv(StringIO(csv_text))
        st.table(df_from_csv) # 用 st.table 顯示靜態表格

st.divider()

# --- 1.1h Multi-sheet Excel ---
st.subheader("Excel with Multiple Sheets")
st.markdown("Fetch a binary Excel file and select which sheet to display.")


# 定義一個 fragment，這讓內部的互動（如 selectbox）只會觸發這個區塊的重新整理
@st.fragment
def excel_demo_fragment():
    # 檢查 session_state 中是否已經有抓好的數據
    if "excel_sheets" not in st.session_state:
        st.session_state.excel_sheets = None
        st.session_state.excel_binary = None

    if st.button("Fetch Excel File", key="excel_btn"):
        with st.spinner("Fetching data from Starlette API..."):
            res = requests.get(f"{api_base_url}/api/excel-demo")
            if res.status_code == 200:
                # 存入 session_state，這樣下次 Rerun 數據還會在
                st.session_state.excel_binary = res.content
                st.session_state.excel_sheets = pd.read_excel(
                    BytesIO(res.content), sheet_name=None
                )
            else:
                st.error("Failed to fetch Excel file.")

    # 如果已經抓到數據了，就顯示選單與表格
    if st.session_state.excel_sheets is not None:
        sheets = st.session_state.excel_sheets
        selected = st.selectbox("Select a sheet:", list(sheets.keys()), key="sheet_sel")
        
        st.success(f"Showing: {selected}")
        st.dataframe(sheets[selected], width="stretch")
        
        st.download_button(
            "Download Excel",
            data=st.session_state.excel_binary,
            file_name="report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# 執行這個片段
excel_demo_fragment()

st.divider()

# --- 1.1i Parquet / Arrow ---
st.subheader("🚀 High-Performance Parquet Data")
st.markdown("模擬從後端抓取 10 萬筆成交資料。Parquet 是處理大數據量時的首選格式。")

@st.fragment
def parquet_demo_fragment():
    if "parquet_df" not in st.session_state:
        st.session_state.parquet_df = None

    if st.button("Fetch 100,000 Rows (Parquet)", key="parquet_btn"):
        start_time = time.time()
        
        with st.spinner("Downloading and parsing binary Parquet..."):
            res = requests.get(f"{api_base_url}/api/stock-parquet")
            
            if res.status_code == 200:
                df = pd.read_parquet(BytesIO(res.content))
                # 把 "object" 轉為 Arrow 喜歡的 "datetime64[ns]"
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # 關鍵：直接用 BytesIO 包裝二進位內容並讀取
                st.session_state.parquet_df = df
                
                duration = time.time() - start_time
                st.success(f"Successfully loaded {len(st.session_state.parquet_df):,} rows in {duration:.2f} seconds!")
            else:
                st.error("Failed to fetch Parquet data.")

    if st.session_state.parquet_df is not None:
        df = st.session_state.parquet_df
        
        # # # 顯示統計資訊( .dexcribe 會有其它警告, 改用下面方式分開呼叫)
        # # st.write("Data Statistics:")
        # # st.dataframe(df.describe(), width="stretch")
        # st.write("📊 數值欄位統計 (Numeric Stats):")
        # # 只挑選數值型別的欄位進行統計
        # numeric_stats = df.select_dtypes(include=['number']).describe()
        # st.dataframe(numeric_stats, width="stretch")
        
        # st.write("🔠 類別欄位統計 (Categorical Stats):")
        # # 如果你也想看 symbol 的統計（次數、不重複數等）
        # categorical_stats = df.select_dtypes(include=['object', 'str']).describe().T
        # st.dataframe(categorical_stats, width="stretch")
        
        # 顯示前幾筆資料
        st.text(df.dtypes)
        st.write("Last 10 records:")
        st.dataframe(df.tail(10), width="stretch")

parquet_demo_fragment()

st.divider()

# --- 1.1j Google Sheet Reader ---
st.subheader("🚀 Parquet Data - Google Sheet")
st.markdown("從 Google Sheet 讀取資料。")
# 測試用的試算表資訊
TEST_SPREADSHEET_ID = '1uJ4hZES1KaVkK94rgpmy25rrx86I768ix-00bpj4myE'
TEST_SHEET_NAME = 'Rate'

@st.fragment
def parquet_demo_fragment_gsheet():
    if "parquet_df_gsheet" not in st.session_state:
        st.session_state.parquet_df_gsheet = None
    
    if st.button("Read Google Sheet", key="parquet_gsheet_btn"):
        start_time = time.time()
        with st.spinner("Downloading and parsing binary Parquet..."):
            params = {"id": TEST_SPREADSHEET_ID, "sheet": TEST_SHEET_NAME}
            res = requests.get(f"{api_base_url}/api/gsheet/parquet", params=params)
            
            if res.status_code == 200:
                df = pd.read_parquet(BytesIO(res.content))
                # # 把 "object" 轉為 Arrow 喜歡的 "datetime64[ns]"
                # df['日期'] = pd.to_datetime(df['日期'])
                
                # 關鍵：直接用 BytesIO 包裝二進位內容並讀取
                st.session_state.parquet_df_gsheet = df
                
                duration = time.time() - start_time
                st.success(f"Successfully loaded {len(st.session_state.parquet_df_gsheet):,} rows in {duration:.2f} seconds!")
            else:
                st.error("Failed to fetch Parquet data.")
    
    if st.session_state.parquet_df_gsheet is not None:
        df = st.session_state.parquet_df_gsheet
        
        # 顯示前幾筆資料
        st.text(df.dtypes)
        st.write("Last 10 records:")
        st.dataframe(df.tail(10), width="stretch")


parquet_demo_fragment_gsheet()
