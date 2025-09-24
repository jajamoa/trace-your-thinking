#!/usr/bin/env bash
# cloud_bootstrap_fixed.sh — 修复版本的云服务器初始化脚本
set -euo pipefail

# 配置你的实际仓库信息
REPO_URL="https://github.com/your-username/tyt-synth-agent.git"  # 请替换为你的实际仓库URL
BRANCH="synth_agent"
DASH_KEY="sk-49dcfb9b95104d698ddad64c469a2f74"  # 请替换为你的实际API密钥

echo "🚀 Initializing TYT Synth Agent on cloud server..."

# ===== 基础环境 =====
echo "📦 Installing system packages..."
if command -v apt >/dev/null 2>&1; then
  sudo apt update -y
  sudo apt install -y python3 python3-venv python3-pip git rsync tmux curl jq chrony \
    python-is-python3
elif command -v yum >/dev/null 2>&1; then
  sudo yum makecache -y
  sudo yum install -y python3 python3-pip git rsync tmux curl jq chrony
fi

# 时钟同步
sudo systemctl enable --now chronyd >/dev/null 2>&1 || \
sudo systemctl enable --now chrony >/dev/null 2>&1 || true

# ===== 代码目录 =====
echo "📂 Setting up project directory..."
BASE_DIR="/home/ubuntu/apps"
mkdir -p "$BASE_DIR" && cd "$BASE_DIR"

PROJECT_NAME="tyt-synth-agent"

if [ ! -d "$PROJECT_NAME" ]; then
  echo "🔄 Cloning repository..."
  git clone "$REPO_URL" "$PROJECT_NAME"
fi

cd "$PROJECT_NAME"
echo "📥 Updating code..."
git fetch origin --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

# ===== Python 虚拟环境 =====
echo "🐍 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools

# 项目依赖
echo "📋 Installing dependencies..."
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "⚠️  No requirements.txt found"
fi

# ===== NLTK数据准备 =====
echo "📚 Setting up NLTK data..."
if [ -f scripts/setup_nltk_data.sh ]; then
  chmod +x scripts/setup_nltk_data.sh
  ./scripts/setup_nltk_data.sh
else
  echo "⚠️  NLTK setup script not found, will setup during runtime"
fi

# ===== 环境变量 =====
echo "🔐 Setting up environment variables..."
cat > ".env.local" <<EOF
DASHSCOPE_API_KEY=${DASH_KEY}
MAX_QA_COUNT=20
DEBUG_LLM_IO=false
EOF
chmod 600 ".env.local"

# ===== 结果目录 =====
echo "📁 Creating output directories..."
mkdir -p "experiment/runs"
mkdir -p "experiment/agent_data/synthetic_agents"

# ===== 验证安装 =====
echo "🔍 Verifying installation..."
python3 --version
pip list | grep -E "(nltk|dashscope|requests)" || echo "Some packages may not be installed"

if [ -f "experiment/setup_nltk.py" ]; then
  python3 experiment/setup_nltk.py
fi

echo ""
echo "✅ Setup completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 Project location: $BASE_DIR/$PROJECT_NAME"
echo "🔧 Activate environment: source $BASE_DIR/$PROJECT_NAME/.venv/bin/activate"
echo "🗝️  API key file: $BASE_DIR/$PROJECT_NAME/.env.local"
echo ""
echo "🚀 Ready to run experiments:"
echo "   cd $BASE_DIR/$PROJECT_NAME/experiment"
echo "   bash run_experiments_ultra_parallel.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
