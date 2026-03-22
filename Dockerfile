# 机械工程 AI 系统 / main_app — 仅打包 API（前端见 docker-compose 中 nginx 服务）
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY main_app.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 8010

# 生产可改为: --workers 2（勿与 --reload 同用）
CMD ["uvicorn", "main_app:app", "--host", "0.0.0.0", "--port", "8010"]
