# PostgreSQL 17 + PostGIS 3, built on the official multi-arch postgres image so it runs
# natively on both Apple Silicon (arm64) and Intel/AMD (amd64) machines.
FROM postgres:17

RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-17-postgis-3 \
 && rm -rf /var/lib/apt/lists/*
