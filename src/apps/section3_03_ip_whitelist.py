import requests
import streamlit as st

st.title("3. IP Whitelisting")
st.caption("Middleware Blocking")
st.markdown("""
The `IPWhitelistMiddleware` restricts access to allowed IP addresses. 
In this demo, **only `127.0.0.1` is whitelisted**.
""")

st.info("""
**💡 How to demo:**
- Enter `127.0.0.1` to see a **Success** case.
- Enter `8.8.8.8` to see a **Blocked** case.
""")
api_base_url = st.secrets["api"]["url"]
col1, col2 = st.columns([2, 1])

with col1:
    test_ip = st.text_input("Simulate Visitor IP", value="192.168.1.100")
with col2:
    st.write("")  # spacing
    st.write("")  # spacing
    if st.button("Test Access Policy"):
        try:
            # Call the simulation endpoint
            res = requests.get(
                f"{api_base_url}/api/security/simulate-ip",
                params={"ip": test_ip},
            )

            if res.status_code == 200:
                st.success(f"✅ {test_ip} is **ALLOWED**")
                st.json(res.json())
            else:
                st.error(f"⛔ {test_ip} is **BLOCKED** ({res.status_code})")
                try:
                    st.json(res.json())
                except:
                    st.write(res.text)

        except Exception as e:
            st.error(f"Failed to check policy: {e}")
st.info("""
**Real-world Behavior:**  
If a user from a blocked IP (e.g., `192.168.1.100`) attempts to access ANY page of this app, 
they will receive a `403 Forbidden` error immediately, before Streamlit even loads.
""")

# if st.button("🚀 快速連點測試 (API Spam)"):
#     res = requests.get(f"{api_base_url}/api/raw-data")
    
#     if res.status_code == 200:
#         st.success("請求成功！")
#     elif res.status_code == 429:
#         st.error("🚫 你點太快了！伺服器拒絕服務（429 Too Many Requests）")
#         st.info(f"後端回傳訊息: {res.json()['detail']}")
