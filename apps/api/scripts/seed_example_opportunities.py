import httpx
import sys
from datetime import date, timedelta

BASE = 'http://localhost:8001/api/v1'
EMAIL = 'admin@dataservice.pe'
PASSWORD = 'Admin123!'


def main() -> int:
    r = httpx.post(f'{BASE}/auth/login', json={'email': EMAIL, 'password': PASSWORD})
    r.raise_for_status()
    tokens = r.json()
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}

    me = httpx.get(f'{BASE}/auth/me', headers=headers).json()
    owner_id = me['id']
    print('Usuario:', me['full_name'], me['id'])

    prospects = httpx.get(f'{BASE}/prospects', headers=headers, params={'page_size': 5}).json()['items']
    if len(prospects) < 2:
        print('Se necesitan al menos 2 prospectos para crear ejemplos.')
        return 1

    cats = httpx.get(
        f'{BASE}/catalogs/bundle', headers=headers, params={'codes': 'pipeline_stage,opportunity_type,loss_reason'}
    ).json()['catalogs']
    stage_by_code = {o['code']: o['id'] for o in cats['pipeline_stage']}
    type_by_code = {o['code']: o['id'] for o in cats['opportunity_type']}
    loss_by_code = {o['code']: o['id'] for o in cats['loss_reason']}

    today = date.today()

    opportunities = [
        {
            'prospect_id': prospects[0]['id'],
            'title': 'Venta de servicios cloud',
            'stage_id': stage_by_code['NUEVO'],
            'type_id': type_by_code['NUEVO'],
            'owner_id': owner_id,
            'estimated_amount': 25000,
            'probability': 30,
            'expected_close_date': (today + timedelta(days=30)).isoformat(),
        },
        {
            'prospect_id': prospects[0]['id'],
            'title': 'Renovación anual de licencias',
            'stage_id': stage_by_code['COTIZACION'],
            'type_id': type_by_code['ACTUALIZACION'],
            'owner_id': owner_id,
            'estimated_amount': 12000,
            'probability': 60,
            'expected_close_date': (today + timedelta(days=15)).isoformat(),
        },
        {
            'prospect_id': prospects[1]['id'],
            'title': 'Implementación de data center',
            'stage_id': stage_by_code['NEGOCIACION'],
            'type_id': type_by_code['NUEVO'],
            'owner_id': owner_id,
            'estimated_amount': 85000,
            'probability': 80,
            'expected_close_date': (today + timedelta(days=7)).isoformat(),
        },
        {
            'prospect_id': prospects[1]['id'],
            'title': 'Proyecto postergado por cliente',
            'stage_id': stage_by_code['CERRADO_PERDIDO'],
            'loss_reason_id': loss_by_code['POSTERGADO'],
            'owner_id': owner_id,
            'estimated_amount': 40000,
            'probability': 0,
            'expected_close_date': (today - timedelta(days=10)).isoformat(),
        },
    ]

    for i, o in enumerate(opportunities):
        r = httpx.post(f'{BASE}/opportunities', headers=headers, json=o)
        if r.status_code == 201:
            created = r.json()
            print(f'Creada oportunidad {i+1}: {created["title"]} ({created["stage"]["name"]})')
        else:
            print(f'Error oportunidad {i+1}: {r.status_code} {r.text}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
