import asyncio
import json
import os

from google.oauth2 import service_account
import gspread
import streamlit as st
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

# ==============================================================================
# SECTION 4: PERFORMANCE & LIFECYCLE
# ==============================================================================


# 4.1.1 Global Lifespan Resources (Simulated DB)
class FakeDBConnection:
    """Simulates a database connection pool for demo purposes."""

    async def connect(self):
        print("   ✅ [Lifespan] Database connection established")

    async def disconnect(self):
        print("   ✅ [Lifespan] Database connection closed")


db_connection = FakeDBConnection()


# 4.1.2 Cache Pre-warming
async def prewarm_ml_model():
    """Simulate loading a heavy ML model during startup."""
    print("   🔄 [Lifespan] Loading ML model...")
    await asyncio.sleep(0.1)
    print("   ✅ [Lifespan] ML model loaded and cached")


# 4.2 Background Tasks
async def send_email_task(email: str):
    print(f"📧 [Background] Starting email delivery to {email}...")
    await asyncio.sleep(2)  # Simulate delay
    print(f"✅ [Background] Email sent to {email}")


async def background_email(request):
    data = await request.json()
    email = data.get("email", "unknown@example.com")
    task = BackgroundTask(send_email_task, email=email)  # heavy task
    return JSONResponse(
        {"status": "queued", "message": f"Sending email to {email}"}, background=task
    )


class GoogleSheetManager:
    def __init__(self):
        self.client = None
        self._path = 'src/creds/service_account.json'

    async def connect(self):
        """在 Lifespan 啟動時建立連線"""
        # 優先從 Streamlit Secrets 讀取
        if "gsheets" in st.secrets:
            creds_dict = dict(st.secrets["gsheets"])
            self.client = gspread.service_account_from_dict(creds_dict)
            print("   ✅ [Lifecycle] 使用 Streamlit Secrets Google Sheets API 連線成功")
        else:
            try:
                scopes = [
                    # GMAIL
                    'https://mail.google.com/',
                    'https://www.googleapis.com/auth/gmail.modify',
                    'https://www.googleapis.com/auth/gmail.compose',
                    'https://www.googleapis.com/auth/gmail.send',
                    # SHEETS & DRIVE
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                service_account_file = os.path.expanduser(self._path)
                with open(service_account_file) as f:
                    info = json.load(f)
                
                creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
                self.client = gspread.authorize(creds)
                print("\n   ✅ [Lifecycle] Google Sheets API 連線成功")
            except Exception as e:
                print(f"   ❌ [Lifecycle] Google Sheets 連線失敗: {e}")


gs_manager = GoogleSheetManager()
