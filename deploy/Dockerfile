FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/

# 数据目录（运行时由 volume 挂载覆盖）
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 43210

# 使用 waitress 作为生产级 WSGI 服务器
CMD ["python", "-c", "from waitress import serve; from backend.server import AppHandler; import os; \
     host = os.environ.get('MCU_HOST', '0.0.0.0'); \
     port = int(os.environ.get('MCU_PORT', '43210')); \
     print(f'Serving on {host}:{port}'); \
     serve(AppHandler, host=host, port=port, threads=8)"]
