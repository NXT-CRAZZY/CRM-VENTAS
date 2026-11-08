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

    prospects = httpx.get(f'{BASE}/prospects', headers=headers, params={'page_size': 5}).json()['items']
    if len(prospects) < 2:
        print('Se necesitan al menos 2 prospectos para crear ejemplos.')
        return 1

    products = httpx.get(f'{BASE}/products', headers=headers, params={'page_size': 5}).json()['items']
    if len(products) < 2:
        print('Se necesitan al menos 2 productos para crear ejemplos.')
        return 1

    today = date.today()

    quotes = [
        {
            'prospect_id': prospects[0]['id'],
            'issue_date': today.isoformat(),
            'expiration_date': (today + timedelta(days=7)).isoformat(),
            'notes': 'Cotización inicial de servicios.',
            'items': [
                {
                    'product_id': products[0]['id'],
                    'description': products[0]['name'],
                    'quantity': 2,
                    'unit_price': float(products[0]['list_price']),
                }
            ],
        },
        {
            'prospect_id': prospects[1]['id'],
            'issue_date': today.isoformat(),
            'expiration_date': (today + timedelta(days=15)).isoformat(),
            'notes': 'Propuesta con dos líneas.',
            'items': [
                {
                    'product_id': products[0]['id'],
                    'description': products[0]['name'],
                    'quantity': 1,
                    'unit_price': float(products[0]['list_price']),
                },
                {
                    'product_id': products[1]['id'],
                    'description': products[1]['name'],
                    'quantity': 3,
                    'unit_price': float(products[1]['list_price']),
                },
            ],
        },
    ]

    for i, q in enumerate(quotes):
        r = httpx.post(f'{BASE}/quotes', headers=headers, json=q)
        if r.status_code == 201:
            created = r.json()
            print(f'Creada cotización {i+1}: {created["prospect"]["display_name"]} - {created["total"]}')
        else:
            print(f'Error cotización {i+1}: {r.status_code} {r.text}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
