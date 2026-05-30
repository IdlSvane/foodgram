# Foodgram

Foodgram - сервис публикации рецептов. Пользователи могут создавать рецепты,
подписываться на авторов, добавлять рецепты в избранное и список покупок, а
также скачивать сводный список ингредиентов.

Проект доступен по адресу [https://cyghost.ddns.net](https://cyghost.ddns.net).
Документация API доступна по адресу
[https://cyghost.ddns.net/api/docs/](https://cyghost.ddns.net/api/docs/).

## Стек

- Python, Django, Django REST Framework
- PostgreSQL
- Docker, Nginx, Gunicorn
- React

## Запуск в Docker

1. Перейдите в папку инфраструктуры:

```bash
cd infra
```

2. Создайте файл `.env` в папке `infra` и заполните переменные окружения:

```env
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,cyghost.ddns.net,158.160.214.187
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,https://cyghost.ddns.net
DOCKER_USERNAME=your_dockerhub_username
```

3. Запустите проект:

```bash
docker compose up --build
```

Backend автоматически применит миграции, создаст стандартные теги и загрузит
ингредиенты из `data/ingredients.csv`.

После запуска приложение доступно по адресу [http://localhost](http://localhost),
а документация API - по адресу
[http://localhost/api/docs/](http://localhost/api/docs/).

## Полезные команды

Создать администратора:

```bash
docker compose exec backend python manage.py createsuperuser
```

Загрузить ингредиенты вручную:

```bash
docker compose exec backend python manage.py load_ingredients /app/data/ingredients.csv
```

Создать стандартные теги:

```bash
docker compose exec backend python manage.py load_tags
```

## CI/CD

В проект добавлен workflow `.github/workflows/main.yml`. При push в ветку
`main` он проверяет backend, собирает Docker-образы backend и frontend,
публикует их в Docker Hub и обновляет контейнеры на сервере.

Для работы workflow в настройках GitHub Actions нужны repository secrets:

- `DOCKER_USERNAME` - логин Docker Hub.
- `DOCKER_PASSWORD` - пароль или access token Docker Hub.
- `HOST` - домен сервера: `cyghost.ddns.net`.
- `USER` - пользователь для SSH-подключения.
- `SSH_KEY` - приватный SSH-ключ пользователя.

На сервер копируются `infra/docker-compose.production.yml`, `infra/nginx.conf`,
`infra/nginx.production.conf`, `docs` и `data`. Compose-файл использует опубликованные образы
`${DOCKER_USERNAME}/foodgram_backend:latest` и
`${DOCKER_USERNAME}/foodgram_frontend:latest`.

## HTTPS

Production-конфигурация использует сертификаты Let's Encrypt из
`/etc/letsencrypt/live/cyghost.ddns.net/`. Перед первым запуском HTTPS на
сервере нужно выпустить сертификат:

```bash
cd ~/foodgram/infra
sudo docker compose -f docker-compose.production.yml stop nginx
sudo certbot certonly --standalone -d cyghost.ddns.net
sudo docker compose -f docker-compose.production.yml up -d
```

Для автообновления сертификата можно добавить deploy hook:

```bash
sudo certbot renew --dry-run
```

## Автор

Роман Лебедев - [GitHub](https://github.com/IdlSvane),
[email](mailto:Rlebedev02@yandex.ru).
