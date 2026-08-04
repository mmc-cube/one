#!/bin/bash
# ==========================================
# 服务器端更新脚本
# 用法：ssh root@server 'bash /opt/mumu/deploy/update.sh'
# ==========================================
set -e

cd /opt/mumu

echo '>>> 拉取最新代码...'
git pull origin master

echo '>>> 重建并重启服务...'
docker compose -f deploy/docker-compose.yml up -d --build

echo '>>> 更新完成'
