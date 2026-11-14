import requests

# Test generate checklist
res1 = requests.post('http://127.0.0.1:8000/api/v1/chat/form-session/generate-checklist', json={
    'channel': 'paper',
    'taxpayer_type': 'juristic_thai',
    'location_type': 'rented',
    'is_power_of_attorney': True
})
print('STATUS 1:', res1.status_code)
d1 = res1.json()
print('Total docs:', d1['total_documents'])
for it in d1['items']:
    print(' -', it['title'], f"({it['legal_ref']})")

# Test evaluate checklist
items = d1['items']
for i, it in enumerate(items):
    it['status'] = 'received' if i != 2 else 'missing'

res2 = requests.post('http://127.0.0.1:8000/api/v1/chat/form-session/evaluate-checklist', json={
    'profile': d1['profile'],
    'items': items
})
print('\nSTATUS 2:', res2.status_code)
d2 = res2.json()
print('Is complete:', d2['is_complete'])
print('Verdict title:', d2['verdict_title'])
print('Verdict msg:\n', d2['verdict_message'][:200])
