import streamlit as st

st.title("2. Secure Cookies")
st.caption("Accessing Middleware Cookies")
st.markdown(
    "Streamlit can access cookies set by Starlette middleware via `st.context.cookies`."
)

cookies = st.context.cookies

if "session_id" in cookies:
    st.success(f"✅ Found `session_id`: `{cookies['session_id']}`")
    st.info("This cookie was set by `CookieMiddleware` in `app.py`.")
else:
    st.warning("`session_id` not found in cookies yet.")

with st.expander("Show all cookies"):
    st.write(cookies)
