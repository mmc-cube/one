#!/bin/bash
# ==========================================
# 服务器端更新脚本
# 用法：ssh user@server 'bash /opt/mumu/deploy/update.sh'
# ==========================================
set -e

cd /opt/mumu

echo ">>> 拉取最新代码..."
git pull origin main

echo ">>> 安装新依赖（如有）..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

echo ">>> 重启服务..."
# Docker 方式
if docker ps | grep -q baili-electronics; then
    docker compose -f deploy/docker-compose.yml up -d --build
    echo ">>> Docker 已重启"
# systemd 方式
elif systemctl is-active --quiet baili-electronics; then
    sudo systemctl restart baili-electronics
    echo ">>> systemd 服务已重启"
else
    echo "!!! 未检测到运行中的服务，请手动启动"
fi

echo ">>> 更新完成"
