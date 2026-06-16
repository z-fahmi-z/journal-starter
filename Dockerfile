FROM python:3.14-alpine

RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

WORKDIR /app

COPY api ./api

COPY pyproject.toml ./

RUN pip install -e .

RUN chown -R appuser:appgroup /app

USER appuser

CMD ["uvicorn","api.main:app","--reload","--host","0.0.0.0","--port","8080"]

EXPOSE 8080