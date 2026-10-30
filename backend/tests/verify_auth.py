import json
import urllib.error
import urllib.request

def api_call(url, method='GET', payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = str(e)
        return e.code, body
    except Exception as e:
        return 0, str(e)

def sanitize_response(body):
    if isinstance(body, dict):
        return {k: ('***REDACTED***' if k == 'access_token' else v) for k, v in body.items()}
    return body

print('=== 1. Health Endpoint ===')
st, res = api_call('http://127.0.0.1:8765/api/health')
print(f'Status: {st}, Body: {res}')

print('\n=== 2. Teacher Login (email) ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'email': 'teacher@attendx.ai', 'password': 'Teacher@123'})
teacher_token = res.get('access_token') if isinstance(res, dict) else None
print(f'Status: {st}, Body: {sanitize_response(res)}')

print('\n=== 3. Student Login (Sarah Chen email) ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'email': 'sarah.chen@student.attendx.ai', 'password': 'Student@123'})
print(f'Status: {st}, Body: {sanitize_response(res)}')

print('\n=== 4. Student Login (roll number in email field) ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'email': 'CS-2026-001', 'password': 'Student@123'})
print(f'Status: {st}, Body: {sanitize_response(res)}')

print('\n=== 5. Student Login (Demo Student email) ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'email': 'demo.student@example.com', 'password': 'Student@123'})
print(f'Status: {st}, Body: {sanitize_response(res)}')

print('\n=== 6. Student Login (username field with roll number DEMO001) ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'username': 'DEMO001', 'password': 'Student@123'})
student_token = res.get('access_token') if isinstance(res, dict) else None
print(f'Status: {st}, Body: {sanitize_response(res)}')

print('\n=== 7. Current User Profile (/api/auth/me) with Teacher Token ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/me', 'GET', token=teacher_token)
print(f'Status: {st}, Body: {res}')

print('\n=== 8. Current User Profile (/api/auth/me) with Student Token ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/me', 'GET', token=student_token)
print(f'Status: {st}, Body: {res}')

print('\n=== 9. Attendance Reports (/api/attendance/reports?page=1&page_size=20) with Teacher Token ===')
st, res = api_call('http://127.0.0.1:8765/api/attendance/reports?page=1&page_size=20', 'GET', token=teacher_token)
if isinstance(res, dict):
    print(f'Status: {st}, Total: {res.get("total")}, Page: {res.get("page")}, Summary: {res.get("summary")}')
else:
    print(f'Status: {st}, Body: {res}')

print('\n=== 10. Invalid Password Verification ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'email': 'teacher@attendx.ai', 'password': 'WrongPassword999!'})
print(f'Status: {st}, Body: {res}')

print('\n=== 11. Empty Identifier Validation ===')
st, res = api_call('http://127.0.0.1:8765/api/auth/login', 'POST', {'password': 'Password123!'})
print(f'Status: {st}, Body: {res}')
