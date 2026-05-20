import streamlit as st

st.title("2. Serving Static Assets")
st.caption("Hosting HTML/CSS/JS")
st.markdown(
    "Mounting a full directory of static files (e.g., a landing page) alongside your dashboard."
)

st.link_button(
    "🌐 View HTML Landing Page (/landing/)", "/landing/", use_container_width=True
)