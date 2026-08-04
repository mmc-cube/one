#!/bin/bash
# 打包元器件资料库，用于传输到服务器
# 用法：bash deploy/package-lib.sh

LIB_DIR="${1:-D:/niuma_modules_extracted}"
OUTPUT="deploy/niuma_modules.tar.gz"

if [ ! -d "$LIB_DIR" ]; then
    echo "错误：找不到元器件库目录 $LIB_DIR"
    echo "用法：bash deploy/package-lib.sh <元器件库路径>"
    exit 1
fi

echo "正在打包 $LIB_DIR ..."
tar -czf "$OUTPUT" -C "$(dirname "$LIB_DIR")" "$(basename "$LIB_DIR")"
SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "完成：$OUTPUT ($SIZE)"
echo ""
echo "上传到服务器："
echo "  scp $OUTPUT user@server:/tmp/"
echo "  ssh user@server 'tar -xzf /tmp/niuma_modules.tar.gz -C /data/'"
