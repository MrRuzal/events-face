FROM python:3.12-alpine

WORKDIR /app
COPY . /app

RUN apk add --no-cache redis
RUN pip install --upgrade pip
RUN pip install "django>=4.2" djangorestframework django-filter djangorestframework-simplejwt celery redis ruff

ENV PYTHONPATH=/app/src

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]