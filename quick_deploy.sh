#!/bin/bash
# 快速部署脚本 - 适用于云服务器的最小化部署

set -e

echo "🚀 TYT Synth Agent 快速部署"
echo "================================"

# 检测并安装Python3
if ! command -v python3 &> /dev/null; then
    echo "安装Python3..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip git
    elif command -v yum &> /dev/null; then
        sudo yum update -y && sudo yum install -y python3 python3-pip git
    fi
fi

echo "✓ Python3 已安装"

# 升级pip并安装依赖
echo "安装Python依赖..."
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt

echo "✓ Python依赖安装完成"

# 设置NLTK数据
echo "准备NLTK语料数据..."
cd experiment
python3 setup_nltk.py
cd ..

echo "✓ NLTK数据准备完成"

# 检查API密钥
if [[ ! -f ".env.local" ]]; then
    echo "⚠️  未找到API密钥配置"
    echo "请创建.env.local文件并添加:"
    echo "DASHSCOPE_API_KEY=your_api_key_here"
    echo ""
    echo "或者现在设置:"
    read -p "API密钥 (回车跳过): " api_key
    if [[ -n "$api_key" ]]; then
        echo "DASHSCOPE_API_KEY=$api_key" > .env.local
        echo "✓ API密钥已保存"
    fi
fi

echo ""
echo "🎉 部署完成！"
echo ""
echo "运行实验:"
echo "  cd experiment"
echo "  bash run_experiments_ultra_parallel.sh"
echo ""
echo "高性能配置:"
echo "  bash run_experiments_ultra_parallel.sh --workers 32 --llm-threads 48"
