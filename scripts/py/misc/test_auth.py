import json
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://127.0.0.1:8443/auth/'
data = {
    'auth_task': '10',
    'iv_seed': '1234567890',
    'title_id': '0',
    'identity': 'test',
    'extra_data': '{"version": "0", "user_id": "123", "extended_data": true}'
}
data = json.dumps(data).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        print('Status:', resp.status)
        print('Response:', resp.read().decode())
except Exception as e:
    print('Error:', e)