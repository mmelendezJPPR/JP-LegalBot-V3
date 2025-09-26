import requests
import sys

base = 'http://127.0.0.1:5000'
creds = {'username': 'melendez_ma@jp.pr.gov', 'password': 'admin123'}

s = requests.Session()
try:
    r = s.get(base + '/login', timeout=10)
    print('GET /login', r.status_code)
except Exception as e:
    print('GET failed:', e)
    sys.exit(1)

try:
    r = s.post(base + '/login', data=creds, allow_redirects=True, timeout=15)
    print('POST /login status:', r.status_code)
    print('Final URL:', r.url)
    print('Response headers:')
    for k,v in r.headers.items():
        print(f'{k}: {v}')
    print('\n--- Response body (first 4000 chars) ---')
    print(r.text[:4000])
except Exception as e:
    print('POST failed:', e)
    sys.exit(1)
