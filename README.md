# Install

- python -V 列出 3.10.4, 但我們已安裝最新 3.13.3
  - ~/.pyenv/versions/3.13.3/bin/python -m venv .venv
- source .venv/bin/activate
- python -m pip install --upgrade pip
- pip install -U streamlit
- pip freeze > requirements.txt

# Streamlit 版本

- 當遇到 `streamlit --version` 顯示的版本不是你安裝的版號時先
  - `which streamlit` 顯示目前抓到的版本
  - `python -m streamlit --version` 確認當前虛擬環境使用的版本
- 重新啟動虛擬環境
  - `deactivate`
  - `source .venv/bin/activate`
  - `streamlit --version`

# 準備工作

- `.streamlit/config.toml` 新增 `useStarlette = true`
- 將 streamlit 專案拆成兩個檔案
  - `streamlit_app.py` 原本的前端, 裡面有 st.Page, ...
  - `app.py` 後端
- 啟動後端
  - `streamlit run src/app.py` -> http://localhost:8501/
  - `uvicorn src.app:app --reload`
  - `PYTHONPATH=. streamlit run src/app.py`
  - `PYTHONPATH=. pytest src/tests/test_lifecycle.py -s`

# 照影片學習每一條範例

- `1. Custom API Routes`
  - 1.1a JSON Response
    - Route `/api/raw-data` to `custom_starlette_data`
  - 1.1b HTML Response
    - Route `/api/html-demo` to `html_response_demo`
  - 1.1c Plain Text Response
    - Route `/api/plain-text` to `plain_text_demo`
  - 1.1d Redirect Response
    - Route `/api/redirect-demo` to `redirect_demo`
  - 1.1e Path Parameters
    - Route `/api/users/{user_id}` to `path_params_demo`
    - Route `/api/users/{user_id}/{action}` to `path_params_demo`
  - 1.1f DataFrame as JSON
    - Route `/api/df-json` to `dataframe_json_demo`
  - 1.1g DataFrame CSV
    - Route `/api/df-csv` to `dataframe_csv_demo`
  - 1.1h Multi-sheet Excel
    - Route `/api/excel-demo` to `excel_response_demo`
  - 1.1i Parquet / Arrow
    - Route `/api/stock-parquet` to `stock_data_parquet_demo`

# 套件安裝

- gspread
- pytest pytest-asyncio

# GitHub

- 在 GitHub 上建立一個私有 Repo.
- 編輯 .gitignore
- `git init`
