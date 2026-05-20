import streamlit as st

st.header("2. Real-time WebSockets")
st.caption("Control Plane (Streamlit) + Data Plane (Starlette)")

st.markdown("""
This demo showcases a powerful pattern:
- **Streamlit** acts as the **Control Plane**, managing configuration state (via the slider).
- **Starlette** acts as the **Data Plane**, streaming high-frequency data via WebSockets.
""")

# 1. Control Plane: Set the update interval
interval = st.slider("Update Interval (seconds)", 0.1, 2.0, 0.5)

st.divider()

# 2. Data Plane: Real-time visualization via WebSocket
# We use st.components.v2.component to inject HTML and JS that connects directly to the Starlette WebSocket endpoint.
# The 'interval' parameter is passed via query string to configure the server-side stream.

HTML_CONTENT = """
<div id="ws-status" style="margin-bottom: 10px; font-weight: bold; color: #555;">Connecting...</div>
<div id="ws-output" style="
    padding: 1.5rem; 
    background: #f0f2f6; 
    border-radius: 0.5rem; 
    border: 1px solid #ddd;
    font-family: monospace;
    font-size: 1.2rem;
    color: #31333F;
    text-align: center;
">
    Waiting for data...
</div>
"""

JS_CONTENT = """
export default function(component) {
    const { data, parentElement } = component;
    const interval = data;
    const statusEl = parentElement.querySelector("#ws-status");
    const outputEl = parentElement.querySelector("#ws-output");
    
    // Connect to the WebSocket endpoint on the same host
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/realtime?interval=${interval}`;
    
    console.log("Connecting to:", wsUrl);
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        if (statusEl) {
            statusEl.innerText = `✅ Connected (Interval: ${interval}s)`;
            statusEl.style.color = "green";
        }
    };
    
    ws.onmessage = (event) => {
        if (outputEl) {
            const wsData = JSON.parse(event.data);
            const date = new Date(wsData.ts * 1000);
            const timeStr = date.toLocaleTimeString();
            
            outputEl.innerHTML = `
                <div>Value: <span style="font-size: 2rem; color: #ff4b4b;">${wsData.value}</span></div>
                <div style="font-size: 0.8rem; color: #666; margin-top: 5px;">Timestamp: ${timeStr}</div>
            `;
        }
    };
    
    ws.onclose = () => {
        if (statusEl) {
            statusEl.innerText = "❌ Disconnected";
            statusEl.style.color = "red";
        }
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        if (statusEl) {
            statusEl.innerText = "⚠️ Error (Check Console)";
            statusEl.style.color = "orange";
        }
    };

    // Cleanup when component unmounts
    return () => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    };
};
"""

st.subheader("Live Data Stream")
ws_monitor = st.components.v2.component(
    name="ws_monitor", html=HTML_CONTENT, js=JS_CONTENT, isolate_styles=False
)
ws_monitor(data=interval)
