# Build context is the repo root (see render.yaml: dockerContext: .),
# so regulations/ (a sibling of backend/) can be copied into the image.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY regulations/ /regulations/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
