# events-face

## Сервис для отображения мероприятий и регистрации пользователей на них.

### Стек

- Python
- Django
- Django REST Framework
- uv (пакетный менеджер)
- ruff (линтер и форматирование)
- Docker + docker-compose

### Установка и запуск

1. Клонировать репозиторий:

```bash
git clone https://github.com/MrRuzal/events-face.git
cd events-face
```

2. Запустить сервисы через Docker:

```bash
docker-compose up --build
```

### Проверка API

- Получение списка мероприятий (требуется Bearer токен):

```bash
curl -X GET http://localhost:8000/api/events/ -H "Authorization: Bearer <access_token>" -H "Accept: application/json"
```

- Регистрация пользователя:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "yourpassword"}'
```

- Логин пользователя:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "yourpassword"}'
```

- Обновление токена:

```bash
curl -X POST http://localhost:8000/api/auth/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

- Логаут:

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

### Админка

Для доступа к административной панели перейдите по адресу:

```
http://localhost:8000/admin/
```
