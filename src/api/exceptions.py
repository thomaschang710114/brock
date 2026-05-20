from starlette.responses import HTMLResponse
from starlette.responses import Response


# 4.3 Exception Handlers
HTML_404_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 40px;
        }
        h1 {
            font-size: 120px;
            margin: 0;
            background: linear-gradient(135deg, #ff6b6b, #feca57);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            font-size: 24px;
            color: #aaa;
        }
        a {
            color: #feca57;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>404</h1>
        <p>Oops! The page you're looking for doesn't exist.</p>
        <a href="/">← Back to Home</a>
    </div>
</body>
</html>
"""

HTML_500_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>500 - Server Error</title>
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #2d1b3d 0%, #1a1a2e 100%);
            color: #eee;
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 40px;
        }
        h1 {
            font-size: 120px;
            margin: 0;
            background: linear-gradient(135deg, #e74c3c, #9b59b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            font-size: 24px;
            color: #aaa;
        }
        a {
            color: #9b59b6;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>500</h1>
        <p>Something went wrong on our end. Please try again later.</p>
        <a href="/">← Back to Home</a>
    </div>
</body>
</html>
"""


async def not_found(request, exc):
    """Custom 404 handler with styled HTML page."""
    path = request.url.path
    print(f"🚫 [Exception Handler] 404 Not Found: {path}")
    return HTMLResponse(content=HTML_404_PAGE, status_code=404)


async def server_error(request, exc):
    """Custom 500 handler with styled HTML page."""
    print(f"💥 [Exception Handler] 500 Server Error: {request.url.path} - {exc}")
    return HTMLResponse(content=HTML_500_PAGE, status_code=500)


exception_handlers = {
    404: not_found,
    500: server_error,
}


# Test endpoint to trigger errors for demo
async def trigger_error(request):
    """Trigger a 500 error for testing exception handlers."""
    # 往上拋給調用它的框架, 即 Middleware, 框架自動將狀態判定為 500 (Server Error)
    raise Exception("This is a test error to demonstrate the 500 handler!")
