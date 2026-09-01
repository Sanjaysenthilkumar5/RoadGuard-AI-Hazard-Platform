import httpx

def run_verification():
    base = 'http://127.0.0.1:8008'
    client = httpx.Client(base_url=base, timeout=10.0)

    print('1. Checking Health...')
    r = client.get('/health')
    assert r.status_code == 200, f'Health failed: {r.status_code}'
    print('   => OK:', r.json())

    print('2. Testing Demo Role Switch...')
    r = client.post('/api/v1/auth/demo-switch', json={'role': 'ADMIN'})
    assert r.status_code == 200, f'Auth switch failed: {r.status_code}'
    token = r.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print('   => OK: Role switched to ADMIN, token received')

    print('3. Testing Hazards API...')
    r = client.get('/api/v1/hazards', headers=headers)
    assert r.status_code == 200
    hazards = r.json()
    print(f'   => OK: Total hazards in DB = {hazards["total"]}')

    print('4. Testing Map GeoJSON...')
    r = client.get('/api/v1/map/hazards', headers=headers)
    assert r.status_code == 200
    features = r.json()['features']
    print(f'   => OK: Map features count = {len(features)}')

    print('5. Testing Maintenance Prioritizer...')
    r = client.get('/api/v1/maintenance/queue', headers=headers)
    assert r.status_code == 200
    queue = r.json()['queue']
    print(f'   => OK: Maintenance queue length = {len(queue)}, Top rank #1 = {queue[0]["hazard_id"]} ({queue[0]["priority_score"]} pts)')

    print('6. Testing AI Assistant Chat...')
    r = client.post('/api/v1/ai/chat', json={'query': 'Show critical road hazards'}, headers=headers)
    assert r.status_code == 200
    ai_res = r.json()
    print(f'   => OK: AI Tool called = {ai_res["tool_called"]}')
    print(f'   => AI Response snippet: {ai_res["response"][:100]}...')

    print('7. Testing Executive Report Generator...')
    r = client.post('/api/v1/ai/reports/generate?days_back=7', headers=headers)
    assert r.status_code == 200
    rep = r.json()
    print(f'   => OK: Report ID = {rep["report_id"]}, Total Anomalies = {rep["metrics"]["total_hazards"]}')

    print('8. Testing Static Web Assets & Index...')
    r = client.get('/')
    assert r.status_code == 200
    assert 'RoadGuard AI' in r.text
    print('   => OK: Frontend index.html served successfully')

    print('ALL 8 SYSTEM VERIFICATIONS PASSED 100% SUCCESSFUL!')
    print('=============================================')

if __name__ == '__main__':
    run_verification()
