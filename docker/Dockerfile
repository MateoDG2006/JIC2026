FROM python:3.10-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONPATH=/app
ENV CHEMBL_BACKEND=sqlite
ENV CHEMBL_DB_PATH=/data/chembl/chembl_37.db

CMD ["python", "scripts/analisis_proyecto/fase1/extract_chembl_local.py"]
