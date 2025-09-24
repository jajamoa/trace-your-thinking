#!/bin/bash
# fix_current_server.sh - 修复当前服务器上的问题

echo "🔧 Fixing current server setup..."

# 检查当前位置
pwd
echo "Current directory: $(pwd)"

# 如果在错误的目录，先找到正确的项目目录
if [ ! -f "requirements.txt" ] && [ ! -f "experiment/setup_nltk.py" ]; then
    echo "❌ Not in the correct project directory"
    
    # 寻找可能的项目目录
    echo "🔍 Looking for project directories..."
    find /home -name "experiment" -type d 2>/dev/null | head -5
    find /home -name "requirements.txt" 2>/dev/null | head -5
    
    echo ""
    echo "Please cd to the correct project directory and run this script again"
    echo "Example:"
    echo "  cd /home/ubuntu/apps/tyt-synth-agent"
    echo "  bash fix_current_server.sh"
    exit 1
fi

echo "✅ Found project files in current directory"

# 检查git状态
if [ -d ".git" ]; then
    echo "✅ Git repository found"
    git status
else
    echo "❌ No git repository found in current directory"
    echo "You may need to clone the repository:"
    echo "  git clone https://github.com/your-repo/tyt-synth-agent.git"
    echo "  cd tyt-synth-agent"
fi

# 检查Python环境
echo ""
echo "🐍 Checking Python environment..."
python3 --version

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✅ Virtual environment found"
    echo "Activate with: source .venv/bin/activate"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# 激活虚拟环境并安装依赖
echo "📋 Installing dependencies..."
source .venv/bin/activate
pip install -U pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found"
fi

# 设置NLTK
echo "📚 Setting up NLTK..."
if [ -f "experiment/setup_nltk.py" ]; then
    python3 experiment/setup_nltk.py
    echo "✅ NLTK setup completed"
else
    echo "❌ NLTK setup script not found"
fi

# 检查环境变量
echo "🔐 Checking environment variables..."
if [ -f ".env.local" ]; then
    echo "✅ .env.local found"
    grep "DASHSCOPE_API_KEY" .env.local && echo "✅ API key configured" || echo "❌ API key missing"
else
    echo "❌ .env.local not found"
    echo "Create it with:"
    echo "  echo 'DASHSCOPE_API_KEY=your_key_here' > .env.local"
fi

echo ""
echo "🎯 Next steps:"
echo "1. Make sure you're in the project directory"
echo "2. Activate virtual environment: source .venv/bin/activate"
echo "3. Set API key: echo 'DASHSCOPE_API_KEY=your_key' > .env.local"
echo "4. Run experiments: cd experiment && bash run_experiments_ultra_parallel.sh"
