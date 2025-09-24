#!/bin/bash
# TYT Synth Agent - Server Setup Script
# 一键在新服务器上配置实验环境

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}TYT Synth Agent - Server Setup${NC}"
echo -e "${CYAN}================================${NC}"

# Check if running as root (for package installation)
if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}Running as root - can install system packages${NC}"
    CAN_INSTALL_PACKAGES=true
else
    echo -e "${YELLOW}Running as user - will skip system package installation${NC}"
    CAN_INSTALL_PACKAGES=false
fi

# 1. Check and install Python 3.8+
echo -e "\n${BLUE}Step 1: Checking Python installation${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python 3 found: $PYTHON_VERSION${NC}"
    
    # Check if version is >= 3.8
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8) ]]; then
        echo -e "${RED}✗ Python 3.8+ required, found $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    if [[ $CAN_INSTALL_PACKAGES == true ]]; then
        echo -e "${YELLOW}Installing Python 3...${NC}"
        # Detect OS and install accordingly
        if command -v yum &> /dev/null; then
            yum update -y
            yum install -y python3 python3-pip python3-dev
        elif command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y python3 python3-pip python3-dev
        elif command -v dnf &> /dev/null; then
            dnf install -y python3 python3-pip python3-devel
        else
            echo -e "${RED}✗ Cannot auto-install Python. Please install Python 3.8+ manually${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Please install Python 3.8+ and re-run this script${NC}"
        exit 1
    fi
fi

# 2. Check and install pip
echo -e "\n${BLUE}Step 2: Checking pip installation${NC}"
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ pip3 found${NC}"
elif command -v pip &> /dev/null; then
    echo -e "${GREEN}✓ pip found${NC}"
    alias pip3=pip
else
    echo -e "${YELLOW}Installing pip...${NC}"
    python3 -m ensurepip --upgrade
fi

# 3. Install Python dependencies
echo -e "\n${BLUE}Step 3: Installing Python dependencies${NC}"
if [[ -f "requirements.txt" ]]; then
    echo -e "${YELLOW}Installing from requirements.txt...${NC}"
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

# 4. Setup NLTK data directory
echo -e "\n${BLUE}Step 4: Setting up NLTK data${NC}"
NLTK_DATA_DIR="$HOME/nltk_data"

if [[ -d "$NLTK_DATA_DIR" ]]; then
    echo -e "${YELLOW}NLTK data directory already exists: $NLTK_DATA_DIR${NC}"
    
    # Check if required data exists
    if [[ -d "$NLTK_DATA_DIR/corpora/wordnet" && -d "$NLTK_DATA_DIR/tokenizers/punkt" ]]; then
        echo -e "${GREEN}✓ Required NLTK data already present${NC}"
    else
        echo -e "${YELLOW}Downloading missing NLTK data...${NC}"
        python3 experiment/setup_nltk.py
    fi
else
    echo -e "${YELLOW}Creating NLTK data directory and downloading data...${NC}"
    mkdir -p "$NLTK_DATA_DIR"
    python3 experiment/setup_nltk.py
fi

# 5. Check API key configuration
echo -e "\n${BLUE}Step 5: Checking API configuration${NC}"
if [[ -f ".env.local" ]]; then
    if grep -q "DASHSCOPE_API_KEY" .env.local; then
        echo -e "${GREEN}✓ API key configured in .env.local${NC}"
    else
        echo -e "${YELLOW}⚠ .env.local exists but no DASHSCOPE_API_KEY found${NC}"
    fi
elif [[ -f ".env" ]]; then
    if grep -q "DASHSCOPE_API_KEY" .env; then
        echo -e "${GREEN}✓ API key configured in .env${NC}"
    else
        echo -e "${YELLOW}⚠ .env exists but no DASHSCOPE_API_KEY found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No .env file found${NC}"
    echo -e "${CYAN}Creating .env.local template...${NC}"
    cat > .env.local << EOF
# Dashscope API key for LLM operations
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Optional: Maximum QA count for conversations (default: 50)
MAX_QA_COUNT=20

# Optional: Default topic for stance nodes (default: "climate change")
DEFAULT_TOPIC=climate change

# Optional: Enable debug LLM I/O logging (default: false)
DEBUG_LLM_IO=false
EOF
    echo -e "${GREEN}✓ Created .env.local template${NC}"
    echo -e "${YELLOW}Please edit .env.local and add your DASHSCOPE_API_KEY${NC}"
fi

# 6. Test basic functionality
echo -e "\n${BLUE}Step 6: Testing setup${NC}"
echo -e "${YELLOW}Testing NLTK setup...${NC}"
if python3 experiment/setup_nltk.py; then
    echo -e "${GREEN}✓ NLTK test passed${NC}"
else
    echo -e "${RED}✗ NLTK test failed${NC}"
    exit 1
fi

echo -e "${YELLOW}Testing Python imports...${NC}"
python3 -c "
import sys
sys.path.append('.')
try:
    from backend.nltk_setup import check_nltk_data
    from experiment.conversation_manager import ConversationManager
    print('✓ Core imports successful')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
" || exit 1

# 7. Display system info
echo -e "\n${BLUE}Step 7: System Information${NC}"
echo -e "Python version: $(python3 --version)"
echo -e "Pip version: $(python3 -m pip --version)"
echo -e "NLTK data path: $NLTK_DATA_DIR"
echo -e "CPU cores: $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 'unknown')"
echo -e "Available RAM: $(free -h 2>/dev/null | grep '^Mem:' | awk '{print $2}' || echo 'unknown')"

# 8. Provide next steps
echo -e "\n${GREEN}===============================${NC}"
echo -e "${GREEN}✓ Server setup completed!${NC}"
echo -e "${GREEN}===============================${NC}"

echo -e "\n${CYAN}Next steps:${NC}"
if [[ ! -f ".env.local" ]] || ! grep -q "DASHSCOPE_API_KEY.*[^_].*=" .env.local; then
    echo -e "1. ${YELLOW}Configure API key:${NC}"
    echo -e "   echo 'DASHSCOPE_API_KEY=your_actual_key_here' > .env.local"
fi

echo -e "2. ${YELLOW}Test the experiment system:${NC}"
echo -e "   cd experiment"
echo -e "   python test_experiment.py"

echo -e "3. ${YELLOW}Run experiments:${NC}"
echo -e "   cd experiment"
echo -e "   bash run_experiments_ultra_parallel.sh"

echo -e "\n${CYAN}Parallel processing settings:${NC}"
echo -e "- Recommended workers: $(nproc 2>/dev/null || echo '4')"
echo -e "- Recommended LLM threads: $(($(nproc 2>/dev/null || echo '4') * 2))"

echo -e "\n${GREEN}Setup complete! 🚀${NC}"
