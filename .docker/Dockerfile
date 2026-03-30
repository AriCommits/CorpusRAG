FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r /app/requirements.txt

COPY src /app/src
COPY configs /app/configs

ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["python", "-m", "corpus_callosum.api"]
