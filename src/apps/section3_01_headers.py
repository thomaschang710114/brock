import streamlit as st

st.title("1. Security Headers")
st.caption("Middleware Inspection")
st.markdown(
    "Open your browser's DevTools (Network Tab) to see these headers in the response:"
)
st.code(
    """
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000
""",
    language="http",
)
