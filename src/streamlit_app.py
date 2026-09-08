from pathlib import Path
import sys
# 取得專案根目錄並加入 sys.path
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st  # noqa: E402

# Define pages
home_page = st.Page("apps/home.py", title="Home", icon="🏠", default=True)

# Section 1: Routes & Static
sec1_pages = [
    st.Page(
        "apps/section1_01_custom_routes.py",
        title="1. Custom API Routes",
        icon="🔌",
    ),
    st.Page(
        "apps/section1_02_static_assets.py",
        title="2. Serving Static Assets",
        icon="🌐",
    ),
    st.Page("apps/section1_03_seo_metadata.py", title="3. SEO & Metadata", icon="🤖"),
]

# Section 2: Framework Interop
sec2_pages = [
    st.Page(
        "apps/section2_01_fastapi.py",
        title="1. FastAPI Mounting",
        icon="⚡",
    ),
    st.Page(
        "apps/section2_02_websockets.py", title="2. Real-time WebSockets", icon="📡"
    ),
    st.Page(
        "apps/section2_03_mcp.py",
        title="3. MCP Integration",
        icon="🧠",
    ),
]

# Section 3: Production Security
sec3_pages = [
    st.Page(
        "apps/section3_01_headers.py",
        title="1. Security Headers",
        icon="🛡️",
    ),
    st.Page("apps/section3_02_cookies.py", title="2. Secure Cookies", icon="🍪"),
    st.Page(
        "apps/section3_03_ip_whitelist.py",
        title="3. IP Whitelisting",
        icon="🚫",
    ),
]

# Section 4: Performance
sec4_pages = [
    st.Page(
        "apps/section4_01_lifespan.py",
        title="1. Lifespan & Cache",
        icon="♻️",
    ),
    st.Page(
        "apps/section4_02_background_tasks.py",
        title="2. Background Tasks",
        icon="⏳",
    ),
    st.Page(
        "apps/section4_03_exception_handler.py",
        title="3. Exception Handlers",
        icon="🚨",
    ),
]

# # Section 5: Demo Apps
# sec5_pages = [
#     st.Page(
#         "apps/section5_01_rate.py",
#         title="Rate",
#         icon="♻️",
#     ),
# ]

# Navigation setup
pg = st.navigation(
    {
        "Overview": [home_page],
        "1. Routes & Static": sec1_pages,
        "2. Framework Interop": sec2_pages,
        "3. Production Security": sec3_pages,
        "4. Performance": sec4_pages,
    }
)

# Run navigation
pg.run()
