#!/bin/bash
# fix_nltk_corruption.sh - 修复损坏的NLTK数据

set -e

echo "🔧 Fixing corrupted NLTK data..."

NLTK_DIR="$HOME/nltk_data"

echo "📍 NLTK directory: $NLTK_DIR"

# 停止所有可能的实验进程
echo "🛑 Stopping any running experiments..."
pkill -f "run_experiments" || true
pkill -f "python.*experiment" || true
sleep 2

# 备份现有数据（如果需要）
if [ -d "$NLTK_DIR" ]; then
    echo "💾 Backing up existing NLTK data..."
    mv "$NLTK_DIR" "${NLTK_DIR}.backup.$(date +%Y%m%d_%H%M%S)" || true
fi

# 重新创建目录
echo "📁 Creating fresh NLTK directory..."
mkdir -p "$NLTK_DIR"

# 重新下载NLTK数据
echo "📚 Downloading fresh NLTK data..."
python3 -c "
import nltk
import os

# Set NLTK data path
nltk_data_dir = os.path.expanduser('~/nltk_data')
nltk.data.path.insert(0, nltk_data_dir)

print(f'Downloading to: {nltk_data_dir}')

# Download with explicit directory
try:
    result1 = nltk.download('wordnet', download_dir=nltk_data_dir, quiet=False)
    print(f'WordNet download result: {result1}')
except Exception as e:
    print(f'WordNet download error: {e}')

try:
    result2 = nltk.download('punkt', download_dir=nltk_data_dir, quiet=False)
    print(f'Punkt download result: {result2}')
except Exception as e:
    print(f'Punkt download error: {e}')

# Verify downloads
try:
    nltk.data.find('corpora/wordnet')
    print('✓ WordNet verified')
except Exception as e:
    print(f'✗ WordNet verification failed: {e}')

try:
    nltk.data.find('tokenizers/punkt')
    print('✓ Punkt verified')
except Exception as e:
    print(f'✗ Punkt verification failed: {e}')
"

# 验证数据完整性
echo "🔍 Verifying data integrity..."
if [ -d "$NLTK_DIR/corpora/wordnet" ] && [ -d "$NLTK_DIR/tokenizers/punkt" ]; then
    echo "✅ NLTK data successfully restored!"
    
    # 显示目录大小
    echo "📊 Data size: $(du -sh $NLTK_DIR | cut -f1)"
    
    # 列出内容
    echo "📂 Contents:"
    find "$NLTK_DIR" -type d -maxdepth 2 | head -10
    
else
    echo "❌ NLTK data restoration failed!"
    exit 1
fi

echo ""
echo "✅ NLTK corruption fixed!"
echo "🚀 You can now restart your experiments:"
echo "   cd experiment"
echo "   bash run_experiments_ultra_parallel.sh"
