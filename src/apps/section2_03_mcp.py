import asyncio
import streamlit as st
from fastmcp import Client

st.title("3. MCP Server Integration")
st.caption("Model Context Protocol")
st.markdown("""
This demo uses `fastmcp.Client` to talk to the MCP server mounted at `/analytics` (in the same process!).
""")

name = st.text_input("Enter your name for the MCP greet tool", value="Ford Prefect")
api_base_url = st.secrets["api"]["url"]
client = Client(f"{api_base_url}/analytics/mcp")

async def call_greet(name: str):
    async with client:
        result = await client.call_tool("greet", {"name": name})
        return result


if st.button("Ping MCP Server"):
    with st.spinner("Calling MCP tool..."):
        try:
            result = asyncio.run(call_greet(name))
            st.success(f"Response from MCP: {result.content[0].text}")
        except Exception as e:
            st.error(f"MCP Call Failed: {e}")
