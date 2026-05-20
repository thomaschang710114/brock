import streamlit as st

st.title("1. Global Lifespan Resources")
st.caption("Startup/Shutdown Events & Cache Pre-warming")

st.subheader("Resource Management")
st.markdown("""
Resources like database connection pools are initialized once when the server starts and 
cleaned up when it shuts down.
""")

st.info("""
**Expected Terminal Output on Startup:**
```text
🚀 App starting: Initializing resources...
✅ [Lifespan] Database connection established
```
""")

st.divider()

st.subheader("Cache Pre-warming")
st.markdown("""
By loading heavy resources (like ML models) during the lifespan startup, we eliminate the 
"cold start" delay for the first user who visits the dashboard.
""")

st.info("""
**Expected Terminal Output on Startup:**
```text
🔄 [Lifespan] Loading ML model...
✅ [Lifespan] ML model loaded and cached
```
""")
