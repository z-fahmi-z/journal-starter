# Define a base image for metadata and environment setup
FROM python:3.12.3-alpine AS base

ARG POSTGRES_USER
ARG POSTGRES_PASSWORD
ARG POSTGRES_DB
ARG DATABASE_URL

ENV POSTGRES_USER=$POSTGRES_USER
ENV POSTGRES_PASSWORD=$POSTGRES_PASSWORD
ENV POSTGRES_DB=$POSTGRES_DB
ENV DATABASE_URL=$DATABASE_URL

WORKDIR /app

# Setup python dependencies
FROM base AS api_setup

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Deploy the python api
FROM api_setup AS api_deploy

COPY . .

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" ]
