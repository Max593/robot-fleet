FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY simulator/pyproject.toml ./pyproject.toml
COPY simulator/simulator ./simulator

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

CMD ["python", "-m", "simulator.main"]
