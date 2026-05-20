import streamlit as st

st.title("3. SEO & Metadata Endpoints")
st.caption("Robots.txt & Sitemap")
st.markdown("Serving specialized files for search engines and PWA discovery.")

col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("🤖 robots.txt", "/robots.txt", use_container_width=True)
with col2:
    st.link_button("🗺️ sitemap.xml", "/sitemap.xml", use_container_width=True)
with col3:
    st.link_button("📱 manifest.json", "/manifest.json", use_container_width=True)

st.info("These files are served via custom Starlette `Route` definitions in `app.py`.")
