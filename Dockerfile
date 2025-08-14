FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc libpq-dev python3-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/

RUN pip install --upgrade pip uv && \
    uv pip install --system -e .

COPY . /app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]