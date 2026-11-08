import httpx
import sys
from datetime import datetime, timedelta, timezone

BASE = 'http://localhost:8000/api/v1'
EMAIL = 'admin@dataservice.pe'
PASSWORD = 'Admin123!'


def main() -> int:
    r = httpx.post(f'{BASE}/auth/login', json={'email': EMAIL, 'password': PASSWORD})
    r.raise_for_status()
    tokens = r.json()
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}

    me = httpx.get(f'{BASE}/auth/me', headers=headers).json()
    assignee_id = me['id']
    print('Usuario:', me['full_name'], me['id'])

    prospects = httpx.get(f'{BASE}/prospects', headers=headers, params={'page_size': 5}).json()['items']
    if len(prospects) < 2:
        print('Se necesitan al menos 2 prospectos para crear ejemplos.')
        return 1

    cats = httpx.get(
        f'{BASE}/catalogs/bundle', headers=headers, params={'codes': 'task_type,priority'}
    ).json()['catalogs']
    type_by_code = {o['code']: o['id'] for o in cats['task_type']}
    priority_by_code = {o['code']: o['id'] for o in cats['priority']}

    now = datetime.now(timezone.utc)

    tasks = [
        {
            'prospect_id': prospects[0]['id'],
            'title': 'Llamar para confirmar interés',
            'description': 'Recordarle la reunión de la próxima semana y confirmar asistencia.',
            'assignee_id': assignee_id,
            'type_id': type_by_code.get('LLAMAR'),
            'priority_id': priority_by_code.get('ALTA'),
            'due_at': (now + timedelta(hours=3)).isoformat(),
        },
        {
            'prospect_id': prospects[0]['id'],
            'title': 'Enviar cotización de servicios',
            'description': 'Preparar propuesta con los 3 paquetes discutidos.',
            'assignee_id': assignee_id,
            'type_id': type_by_code.get('COTIZACION'),
            'priority_id': priority_by_code.get('MEDIA'),
            'due_at': (now + timedelta(days=2)).isoformat(),
        },
        {
            'prospect_id': prospects[1]['id'],
            'title': 'Realizar demostración',
            'description': 'Agendar demo de 30 minutos con el equipo comercial.',
            'assignee_id': assignee_id,
            'type_id': type_by_code.get('DEMO'),
            'priority_id': priority_by_code.get('ALTA'),
            'due_at': (now - timedelta(days=1)).isoformat(),
        },
        {
            'prospect_id': prospects[1]['id'],
            'title': 'Consultar decisión',
            'description': 'Seguimiento post-cotización.',
            'assignee_id': assignee_id,
            'type_id': type_by_code.get('CONSULTAR_DECISION'),
            'priority_id': priority_by_code.get('BAJA'),
            'due_at': (now - timedelta(hours=5)).isoformat(),
        },
    ]

    for i, t in enumerate(tasks):
        r = httpx.post(f'{BASE}/tasks', headers=headers, json=t)
        if r.status_code == 201:
            created = r.json()
            print(f'Creada tarea {i+1}: {created["title"]} ({created["id"][:8]}...) - {created["status"]}')
        else:
            print(f'Error tarea {i+1}: {r.status_code} {r.text}')

    last = httpx.post(
        f'{BASE}/tasks',
        headers=headers,
        json={
            'prospect_id': prospects[0]['id'],
            'title': 'Tarea completada de ejemplo',
            'assignee_id': assignee_id,
            'due_at': (now - timedelta(days=2)).isoformat(),
        },
    ).json()
    r = httpx.patch(f'{BASE}/tasks/{last["id"]}/status', headers=headers, json={'status': 'DONE'})
    if r.status_code == 200:
        print('Marcada como DONE:', last['title'])
    else:
        print('Error al marcar DONE:', r.status_code, r.text)

    return 0


if __name__ == '__main__':
    sys.exit(main())
