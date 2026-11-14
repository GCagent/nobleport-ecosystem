"""Stephanie decision intake: authenticated, local-first review queue."""
import hmac
import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get('STEPHANIE_API_TOKEN', '')
DB = os.environ.get('STEPHANIE_DB', '/data/decisions.sqlite3')
MAX_BODY = 16384
if len(TOKEN.encode()) < 32:
    raise SystemExit('STEPHANIE_API_TOKEN must contain at least 32 bytes')
os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)
with sqlite3.connect(DB) as db:
    db.execute('CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY, project TEXT NOT NULL, decision_type TEXT NOT NULL, summary TEXT NOT NULL, created_at INTEGER NOT NULL, status TEXT NOT NULL)')

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        supplied = self.headers.get('Authorization', '')
        return hmac.compare_digest(supplied.encode(), ('Bearer ' + TOKEN).encode())

    def do_GET(self):
        if self.path == '/health':
            return self.reply(200, {'status': 'ok'})
        if not self.authorized():
            return self.reply(401, {'error': 'unauthorized'})
        if self.path != '/decisions':
            return self.reply(404, {'error': 'not found'})
        with sqlite3.connect(DB) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute('SELECT * FROM decisions ORDER BY id DESC LIMIT 100').fetchall()
        self.reply(200, {'decisions': [dict(row) for row in rows]})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'unauthorized'})
        if self.path != '/decisions':
            return self.reply(404, {'error': 'not found'})
        try:
            n = int(self.headers.get('Content-Length', '-1'))
            if not 0 < n <= MAX_BODY:
                raise ValueError('invalid length')
            payload = json.loads(self.rfile.read(n))
            if not isinstance(payload, dict) or set(payload) != {'project', 'decision_type', 'summary'}:
                raise ValueError('invalid fields')
            values = [payload[k].strip() if isinstance(payload[k], str) else '' for k in ('project', 'decision_type', 'summary')]
            if any(not v or len(v) > limit for v, limit in zip(values, (200, 100, 4000))):
                raise ValueError('invalid values')
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return self.reply(400, {'error': 'invalid request'})
        with sqlite3.connect(DB, timeout=10) as db:
            cur = db.execute('INSERT INTO decisions (project,decision_type,summary,created_at,status) VALUES (?,?,?,?,?)', (*values, int(time.time()), 'PENDING_REVIEW'))
            decision_id = cur.lastrowid
        self.reply(201, {'id': decision_id, 'status': 'PENDING_REVIEW'})

    def log_message(self, fmt, *args):
        # Avoid writing request paths or authorization information into logs.
        pass

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
