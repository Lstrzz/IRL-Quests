# Веб-версия IRL Quests: сборка Flet web и раздача через nginx.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        unzip \
        xz-utils \
        zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install "flet[all]==1.0.5"

# Flutter ставим отдельным слоем: он большой, и при сбое сборки не будет
# скачиваться заново. safe.directory нужен, иначе Flutter-репозиторий внутри
# контейнера считается чужим и git завершается с exit code 128.
RUN git config --global --add safe.directory "*" \
    && python -c "import flet.version as v; from flet_cli.utils.flutter import install_flutter; install_flutter(v.flutter_version, print)"

RUN flet build web --yes

FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/build/web /usr/share/nginx/html

EXPOSE 80
