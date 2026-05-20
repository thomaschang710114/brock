from starlette.responses import HTMLResponse
from starlette.responses import JSONResponse
from starlette.responses import PlainTextResponse
from starlette.responses import RedirectResponse

# ==============================================================================
# SECTION 1: BREAKING THE SANDBOX (Routing & Static Files)
# ==============================================================================


# 1.1a Custom API Routes (Pure Starlette)
async def custom_starlette_data(request):
    """Serve raw JSON data with minimal overhead."""
    print('custom_starlette_data')
    return JSONResponse({"type": "raw_starlette", "items": [10, 20, 30]})


# 1.1b HTML Response (for st.html display)
async def html_response_demo(request):
    """Return styled HTML content."""
    html_content = """
    <div style="font-family: sans-serif; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;">
        <h2 style="margin: 0;">🎨 HTML Response Demo</h2>
        <p>This HTML was served directly from a <code>Starlette Route</code>!</p>
        <ul>
            <li>No template engine required</li>
            <li>Inline styles work perfectly</li>
            <li>Great for dynamic HTML snippets</li>
        </ul>
    </div>
    """
    return HTMLResponse(html_content)


# 1.1c Plain Text Response
async def plain_text_demo(request):
    """Return plain text content."""
    return PlainTextResponse(
        "Hello from Starlette! This is plain text.\n\nNo formatting, just raw text."
    )


# 1.1d Redirect Response
async def redirect_demo(request):
    """Redirect to another page."""
    return RedirectResponse(url="https://andfanilo.com/newsletter", status_code=303)


# 1.1e Path Parameters
async def path_params_demo(request):
    """Demonstrate path parameters in Starlette routes."""
    # print(request.path_params)
    user_id = request.path_params["user_id"]
    action = request.path_params.get("action", "view")
    return JSONResponse(
        {
            "message": f"User {user_id} requested action: {action}",
            "params": {"user_id": user_id, "action": action},
            "tip": "Path params are extracted from the URL pattern!",
        }
    )
