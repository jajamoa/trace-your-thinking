#!/bin/bash
# package_nltk_data.sh - 打包NLTK数据用于分发

set -e

echo "📦 NLTK数据打包工具"
echo "=================="

NLTK_DIR="$HOME/nltk_data"
PACKAGE_NAME="nltk_data_package_$(date +%Y%m%d_%H%M%S).tar.gz"
TEMP_DIR="/tmp/nltk_package_$$"

# 检查NLTK数据是否存在
if [ ! -d "$NLTK_DIR" ]; then
    echo "❌ NLTK数据目录不存在: $NLTK_DIR"
    echo "请先运行: python3 experiment/setup_nltk.py"
    exit 1
fi

# 验证数据完整性
echo "🔍 验证NLTK数据完整性..."
python3 -c "
import sys
sys.path.append('.')
from backend.nltk_setup import check_nltk_data
if check_nltk_data():
    print('✅ NLTK数据完整')
else:
    print('❌ NLTK数据不完整')
    sys.exit(1)
"

# 显示数据信息
echo "📊 NLTK数据信息:"
echo "  位置: $NLTK_DIR"
echo "  大小: $(du -sh "$NLTK_DIR" | cut -f1)"
echo "  内容:"
find "$NLTK_DIR" -type d -maxdepth 2 | head -10

# 创建临时目录
mkdir -p "$TEMP_DIR"

# 复制NLTK数据
echo "📋 复制数据到临时目录..."
cp -r "$NLTK_DIR" "$TEMP_DIR/"

# 创建安装脚本
echo "📝 创建安装脚本..."
cat > "$TEMP_DIR/install_nltk_data.sh" << 'EOF'
#!/bin/bash
# install_nltk_data.sh - 安装预下载的NLTK数据

set -e

echo "🚀 安装NLTK数据包..."

TARGET_DIR="$HOME/nltk_data"

# 备份现有数据（如果存在）
if [ -d "$TARGET_DIR" ]; then
    echo "💾 备份现有数据..."
    mv "$TARGET_DIR" "${TARGET_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# 复制新数据
echo "📁 安装新数据..."
cp -r nltk_data "$TARGET_DIR"

# 验证安装
echo "🔍 验证安装..."
if [ -d "$TARGET_DIR/corpora/wordnet" ] && [ -d "$TARGET_DIR/tokenizers/punkt" ]; then
    echo "✅ NLTK数据安装成功!"
    echo "📊 安装大小: $(du -sh "$TARGET_DIR" | cut -f1)"
    echo "📍 安装位置: $TARGET_DIR"
else
    echo "❌ NLTK数据安装失败!"
    exit 1
fi

echo ""
echo "🎉 安装完成! 现在可以运行实验了。"
EOF

chmod +x "$TEMP_DIR/install_nltk_data.sh"

# 创建README
cat > "$TEMP_DIR/README.md" << 'EOF'
# NLTK数据包

这个包包含了TYT Synth Agent项目所需的NLTK数据。

## 安装方法

1. 解压数据包:
   ```bash
   tar -xzf nltk_data_package_*.tar.gz
   cd nltk_data_package_*
   ```

2. 运行安装脚本:
   ```bash
   chmod +x install_nltk_data.sh
   ./install_nltk_data.sh
   ```

## 包含的数据

- WordNet语料库 (`corpora/wordnet`)
- Punkt分词器 (`tokenizers/punkt`)

## 目标位置

数据将安装到: `~/nltk_data/`

## 验证安装

```python
import nltk
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('tokenizers/punkt')
    print("✅ NLTK数据可用")
except:
    print("❌ NLTK数据不可用")
```

## 注意事项

- 如果目标位置已有数据，会自动备份
- 适用于所有支持tar的Linux/Unix系统
- 总大小约: 3-4GB
EOF

# 打包数据
echo "🗜️  打包数据..."
cd "$TEMP_DIR"
tar -czf "../$PACKAGE_NAME" .
cd - > /dev/null

# 移动到当前目录
mv "/tmp/$PACKAGE_NAME" "./"

# 清理临时目录
rm -rf "$TEMP_DIR"

# 显示结果
echo ""
echo "✅ 打包完成!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 包文件: $PACKAGE_NAME"
echo "📊 包大小: $(du -sh "$PACKAGE_NAME" | cut -f1)"
echo ""
echo "🚀 分发方法:"
echo "1. 直接复制文件:"
echo "   scp $PACKAGE_NAME user@server:/tmp/"
echo ""
echo "2. 使用rsync:"
echo "   rsync -av $PACKAGE_NAME user@server:/tmp/"
echo ""
echo "3. 上传到云存储后下载:"
echo "   # 上传到云存储，然后在目标服务器:"
echo "   wget https://your-storage/path/$PACKAGE_NAME"
echo ""
echo "📥 安装方法:"
echo "   tar -xzf $PACKAGE_NAME"
echo "   cd \$(basename $PACKAGE_NAME .tar.gz)"
echo "   ./install_nltk_data.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
