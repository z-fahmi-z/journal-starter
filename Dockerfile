FROM python:3.14-alpine

WORKDIR /app

COPY api ./api

COPY pyproject.toml ./

RUN pip install -e .

CMD ["uvicorn","api.main:app","--reload","--host","0.0.0.0","--port","8080"]

EXPOSE 8080