"""Explicit outbound SMS requests with durable duplicate suppression."""
import base64
import hashlib
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

PHONE = re.compile(r'^\+[1-9][0-9]{7,14}$')
KEY = re.compile(r'^[A-Za-z0-9_-]{16,100}$')

def initialize(db_path):
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS sms_requests (request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL, provider_sid TEXT)')

def send(db_path, payload, transport=urllib.request.urlopen):
    if not isinstance(payload, dict) or set(payload) != {'request_id', 'to', 'message'}:
        return 400, {'error': 'request_id, to and message are required'}
    key, to, message = (payload[k] for k in ('request_id', 'to', 'message'))
    if not isinstance(key, str) or not KEY.fullmatch(key) or not isinstance(to, str) or not PHONE.fullmatch(to) or not isinstance(message, str) or not message.strip() or len(message) > 1000:
        return 400, {'error': 'invalid request'}
    if os.getenv('SMS_ENABLED', '').lower() != 'true':
        return 503, {'error': 'SMS is disabled'}
    sid, token, sender = (os.getenv(k, '') for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER'))
    allowed = {s.strip() for s in os.getenv('SMS_ALLOWED_RECIPIENTS', '').split(',') if s.strip()}
    if not re.fullmatch(r'AC[0-9a-fA-F]{32}', sid) or not token or not PHONE.fullmatch(sender):
        return 503, {'error': 'SMS configuration incomplete'}
    if to not in allowed:
        return 403, {'error': 'recipient is not authorized'}
    digest = hashlib.sha256(json.dumps([to, message], ensure_ascii=False).encode()).hexdigest()
    with sqlite3.connect(db_path, timeout=10) as db:
        try:
            db.execute('INSERT INTO sms_requests VALUES (?, ?, ?, NULL)', (key, digest, 'submitting'))
        except sqlite3.IntegrityError:
            row = db.execute('SELECT fingerprint, status, provider_sid FROM sms_requests WHERE request_id=?', (key,)).fetchone()
            if row[0] != digest:
                return 409, {'error': 'request_id already used for different content'}
            return 200, {'status': row[1], 'sid': row[2], 'duplicate': True}
    encoded = urllib.parse.urlencode({'To': to, 'From': sender, 'Body': message}).encode()
    auth = base64.b64encode((sid + ':' + token).encode()).decode()
    request = urllib.request.Request('https://api.twilio.com/2010-04-01/Accounts/' + sid + '/Messages.json', data=encoded, headers={'Authorization': 'Basic ' + auth}, method='POST')
    try:
        with transport(request, timeout=10) as response:
            result = json.load(response)
        if not isinstance(result, dict) or not isinstance(result.get('sid'), str):
            raise ValueError('invalid provider response')
        status, provider_sid, code = 'queued', result['sid'], 202
    except urllib.error.HTTPError as exc:
        status, provider_sid, code = ('rejected' if 400 <= exc.code < 500 else 'unknown'), None, 502
    except (OSError, ValueError, json.JSONDecodeError):
        status, provider_sid, code = 'unknown', None, 502
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute('UPDATE sms_requests SET status=?, provider_sid=? WHERE request_id=?', (status, provider_sid, key))
    return code, {'status': status, 'sid': provider_sid}
