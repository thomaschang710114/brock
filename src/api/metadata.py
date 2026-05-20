from starlette.responses import JSONResponse
from starlette.responses import PlainTextResponse
from starlette.responses import Response

# robots.txt, sitemap.xml: 給搜尋引擎爬蟲看的
# manifest.json: 給作業系統看的


# 1.3 SEO & Metadata Endpoints
async def robots_txt(request):
    '''這是一個純文字檔，放在網站的根目錄。它的作用是告訴搜尋引擎的爬蟲哪些地方你可以進去抓資料，哪些地方你不准進去
    範例:
    User-agent: * # 針對所有的爬蟲
    Disallow: /api/      # 不准抓取 API 路徑
    Allow: /             # 允許抓取其他所有地方
    '''
    return PlainTextResponse("User-agent: *\nDisallow: /api/\nAllow: /\nSitemap: /sitemap.xml")


async def sitemap_xml(request):
    '''如果說 robots.txt 是告示牌，那 sitemap.xml 就是給爬蟲的一張詳盡地圖。它列出了你網站上所有希望被搜尋引擎索引的 URL'''
    base_url = str(request.base_url).rstrip("/")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/landing/</loc>
    <priority>0.8</priority>
  </url>
</urlset>"""
    return Response(sitemap, media_type="application/xml")


async def manifest_json(request):
    return JSONResponse(
        {
            "name": "GoodBuy Stock Analytics",
            "short_name": "GoodBuy",
            "start_url": "/",
            "display": "standalone",
            "theme_color": "#ff4b4b",
        }
    )


# async def manifest_json(request):
#     """
#     自動生成 manifest.json，圖示路徑透過 url_for 指向 static 掛載點。
#     圖示實體路徑：src/static/icons/
#     """
    
#     # 動態產生網址，這會對應到 /static/icons/...
#     try:
#         icon_192_url = str(request.url_for("static", path="icons/icon-192.png"))
#         icon_512_url = str(request.url_for("static", path="icons/icon-512.png"))
#         maskable_url = str(request.url_for("static", path="icons/maskable-icon-512.png"))
#     except Exception as e:
#         # 預防掛載點名稱寫錯的保險機制
#         return JSONResponse({"error": f"URL generation failed: {str(e)}"}, status_code=500)

#     return JSONResponse({
#         "name": "Brock Stock Analytics",
#         "short_name": "BrockStock",
#         "start_url": "/",
#         "display": "standalone",
#         "theme_color": "#ff4b4b",
#         "background_color": "#0E1117",
#         "icons": [
#             {
#                 "src": icon_192_url,
#                 "sizes": "192x192",
#                 "type": "image/png",
#                 "purpose": "any"
#             },
#             {
#                 "src": icon_512_url,
#                 "sizes": "512x512",
#                 "type": "image/png",
#                 "purpose": "any"
#             },
#             {
#                 "src": maskable_url,
#                 "sizes": "512x512",
#                 "type": "image/png",
#                 "purpose": "maskable"
#             }
#         ]
#     })
