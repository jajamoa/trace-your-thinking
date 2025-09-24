#!/bin/bash
# copy_nltk_to_server.sh - 直接复制NLTK数据到远程服务器

set -e

# 使用方法检查
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <server_address> [server_user]"
    echo ""
    echo "示例:"
    echo "  $0 192.168.1.100"
    echo "  $0 server.example.com ubuntu"
    echo "  $0 root@server.example.com"
    exit 1
fi

SERVER="$1"
USER="${2:-ubuntu}"

# 如果SERVER已包含用户名，解析出来
if [[ "$SERVER" == *"@"* ]]; then
    USER=$(echo "$SERVER" | cut -d'@' -f1)
    SERVER=$(echo "$SERVER" | cut -d'@' -f2)
fi

NLTK_DIR="$HOME/nltk_data"

echo "🚀 NLTK数据复制工具"
echo "==================="
echo "📍 本地数据: $NLTK_DIR"
echo "🎯 目标服务器: $USER@$SERVER"
echo ""

# 检查本地NLTK数据
if [ ! -d "$NLTK_DIR" ]; then
    echo "❌ 本地NLTK数据不存在: $NLTK_DIR"
    echo "请先运行: python3 experiment/setup_nltk.py"
    exit 1
fi

# 验证本地数据
echo "🔍 验证本地NLTK数据..."
python3 -c "
import sys
sys.path.append('.')
from backend.nltk_setup import check_nltk_data
if check_nltk_data():
    print('✅ 本地NLTK数据完整')
else:
    print('❌ 本地NLTK数据不完整，请重新下载')
    sys.exit(1)
"

# 显示数据大小
echo "📊 数据大小: $(du -sh "$NLTK_DIR" | cut -f1)"

# 测试服务器连接
echo "🔗 测试服务器连接..."
if ! ssh "$USER@$SERVER" "echo '连接成功'" 2>/dev/null; then
    echo "❌ 无法连接到服务器 $USER@$SERVER"
    echo "请检查:"
    echo "1. 服务器地址是否正确"
    echo "2. SSH密钥是否配置"
    echo "3. 网络连接是否正常"
    exit 1
fi

echo "✅ 服务器连接正常"

# 在远程服务器上备份现有数据（如果存在）
echo "💾 在远程服务器备份现有NLTK数据..."
ssh "$USER@$SERVER" "
if [ -d ~/nltk_data ]; then
    echo '发现现有NLTK数据，进行备份...'
    mv ~/nltk_data ~/nltk_data.backup.\$(date +%Y%m%d_%H%M%S)
    echo '备份完成'
else
    echo '未发现现有NLTK数据'
fi
"

# 复制数据
echo "📋 开始复制NLTK数据..."
echo "这可能需要几分钟，请耐心等待..."

# 使用rsync复制，显示进度
rsync -avz --progress "$NLTK_DIR/" "$USER@$SERVER:~/nltk_data/"

# 验证远程数据
echo "🔍 验证远程NLTK数据..."
ssh "$USER@$SERVER" "
echo '检查远程数据...'
if [ -d ~/nltk_data/corpora/wordnet ] && [ -d ~/nltk_data/tokenizers/punkt ]; then
    echo '✅ NLTK数据复制成功!'
    echo '📊 远程数据大小:' \$(du -sh ~/nltk_data | cut -f1)
    echo '📁 数据位置: ~/nltk_data'
else
    echo '❌ NLTK数据复制失败!'
    exit 1
fi
"

echo ""
echo "🎉 NLTK数据复制完成!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 数据已成功复制到 $USER@$SERVER:~/nltk_data/"
echo ""
echo "🚀 现在可以在远程服务器上运行实验:"
echo "   ssh $USER@$SERVER"
echo "   cd your_project_directory"
echo "   bash run_experiments_ultra_parallel.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
