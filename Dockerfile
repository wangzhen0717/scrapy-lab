FROM python:3.12-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN set -eux; \
    find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0 \
      | xargs -0 -r sed -i \
        -e 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
        -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g'; \
    apt-get update \
        -o Acquire::Retries=5 \
        -o Acquire::http::Timeout=30 \
        -o Acquire::https::Timeout=30 \
        -o Acquire::ForceIPv4=true; \
    apt-get install -y --no-install-recommends \
        tzdata \
        ca-certificates; \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime; \
    echo "$TZ" > /etc/timezone; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip --retries 5 --timeout 60 \
    && pip install -r requirements.txt \
        --only-binary=:all: \
        --retries 5 \
        --timeout 60

COPY . .

RUN mkdir -p /app/data

ENTRYPOINT ["scrapy", "crawl", "ithome"]
