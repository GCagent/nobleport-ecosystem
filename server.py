#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = "."

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

if __name__ == '__main__':
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 NoblePort Systems Live at http://0.0.0.0:{PORT}")
        print(f"📊 Main Dashboard: http://0.0.0.0:{PORT}/")
        print(f"🎰 Viral Lottery: http://0.0.0.0:{PORT}/dashboards/lottery.html")
        print(f"💎 DeFi Analytics: http://0.0.0.0:{PORT}/dashboards/defi-dashboard.html")
        print(f"🏠 Properties: http://0.0.0.0:{PORT}/dashboards/essex-county.html")
        print(f"⚙️  Operations Monitor: http://0.0.0.0:{PORT}/operations-monitor/")
        httpd.serve_forever()
