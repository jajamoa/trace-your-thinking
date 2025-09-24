#!/bin/bash
# 服务器一键部署脚本 - TYT Synth Agent
# 自动安装依赖、下载语料、准备环境

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  TYT Synth Agent 服务器部署脚本${NC}"
echo -e "${CYAN}========================================${NC}"

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (for system package installation)
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        print_warning "部分操作需要sudo权限，请确保当前用户有sudo权限"
    fi
}

# Detect OS and package manager
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            OS="ubuntu"
            PKG_MANAGER="apt-get"
        elif command -v yum &> /dev/null; then
            OS="centos"
            PKG_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            OS="fedora"
            PKG_MANAGER="dnf"
        else
            print_error "不支持的Linux发行版"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PKG_MANAGER="brew"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    print_status "检测到操作系统: $OS"
}

# Install system dependencies
install_system_deps() {
    print_status "安装系统依赖..."
    
    case $OS in
        "ubuntu")
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv git curl wget
            ;;
        "centos")
            sudo yum update -y
            sudo yum install -y python3 python3-pip git curl wget
            ;;
        "fedora")
            sudo dnf update -y
            sudo dnf install -y python3 python3-pip git curl wget
            ;;
        "macos")
            if ! command -v brew &> /dev/null; then
                print_status "安装Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python3 git
            ;;
    esac
    
    print_success "系统依赖安装完成"
}

# Check Python version
check_python() {
    print_status "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_status "Python版本: $PYTHON_VERSION"
        
        # Check if version is >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            print_success "Python版本符合要求 (>= 3.8)"
        else
            print_error "Python版本过低，需要 >= 3.8"
            exit 1
        fi
    else
        print_error "未找到Python3"
        exit 1
    fi
}

# Setup virtual environment (optional but recommended)
setup_venv() {
    read -p "是否创建Python虚拟环境? (推荐) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "创建Python虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        print_success "虚拟环境已激活"
        
        # Create activation reminder
        cat > activate_env.sh << 'EOF'
#!/bin/bash
echo "激活Python虚拟环境..."
source venv/bin/activate
echo "虚拟环境已激活。运行 'deactivate' 退出虚拟环境。"
EOF
        chmod +x activate_env.sh
        print_status "创建了 activate_env.sh 脚本，下次可以用它激活环境"
    fi
}

# Install Python dependencies
install_python_deps() {
    print_status "安装Python依赖..."
    
    # Upgrade pip first
    python3 -m pip install --upgrade pip
    
    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        pip3 install -r requirements.txt
        print_success "Python依赖安装完成"
    else
        print_error "未找到requirements.txt文件"
        exit 1
    fi
}

# Setup NLTK data
setup_nltk() {
    print_status "设置NLTK语料数据..."
    
    cd experiment
    python3 setup_nltk.py
    cd ..
    
    print_success "NLTK数据准备完成"
}

# Check API key
check_api_key() {
    print_status "检查API密钥配置..."
    
    if [[ -f ".env.local" ]]; then
        if grep -q "DASHSCOPE_API_KEY" .env.local; then
            print_success "发现已配置的API密钥"
        else
            print_warning "未找到DASHSCOPE_API_KEY配置"
        fi
    else
        print_warning "未找到.env.local文件"
        read -p "是否现在配置API密钥? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "请输入DASHSCOPE_API_KEY: " api_key
            echo "DASHSCOPE_API_KEY=$api_key" > .env.local
            print_success "API密钥已保存到.env.local"
        fi
    fi
}

# Test installation
test_installation() {
    print_status "测试安装..."
    
    # Test Python imports
    python3 -c "
import sys
import json
import csv
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
import random
import time
import signal
import threading
import requests
import numpy as np
import pandas as pd
import matplotlib
import nltk
import sklearn
print('✓ 所有核心依赖导入成功')
" 2>/dev/null && print_success "依赖测试通过" || print_error "依赖测试失败"
    
    # Test NLTK data
    python3 -c "
import nltk
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('tokenizers/punkt')
    print('✓ NLTK数据可用')
except:
    print('✗ NLTK数据不可用')
    exit(1)
" && print_success "NLTK数据测试通过" || print_error "NLTK数据测试失败"
}

# Show usage instructions
show_usage() {
    echo
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  部署完成！使用说明${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo
    echo -e "${GREEN}1. 运行实验：${NC}"
    echo -e "   cd experiment"
    echo -e "   bash run_experiments_ultra_parallel.sh"
    echo
    echo -e "${GREEN}2. 如果使用了虚拟环境：${NC}"
    echo -e "   source venv/bin/activate  # 激活环境"
    echo -e "   # 或者运行: bash activate_env.sh"
    echo
    echo -e "${GREEN}3. 配置文件：${NC}"
    echo -e "   .env.local - API密钥配置"
    echo -e "   requirements.txt - Python依赖"
    echo
    echo -e "${GREEN}4. 数据目录：${NC}"
    echo -e "   ~/nltk_data - NLTK语料数据"
    echo -e "   experiment/agent_data - 实验数据"
    echo
    echo -e "${YELLOW}注意：如果在云服务器上，记得配置防火墙和安全组${NC}"
    echo
}

# Main deployment process
main() {
    print_status "开始部署流程..."
    
    # Check prerequisites
    check_sudo
    detect_os
    
    # Install dependencies
    install_system_deps
    check_python
    
    # Setup Python environment
    setup_venv
    install_python_deps
    
    # Setup language data
    setup_nltk
    
    # Configuration
    check_api_key
    
    # Test everything
    test_installation
    
    # Show usage
    show_usage
    
    print_success "部署完成！"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-system)
            SKIP_SYSTEM=true
            shift
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --help|-h)
            echo "TYT Synth Agent 服务器部署脚本"
            echo
            echo "用法: $0 [选项]"
            echo
            echo "选项:"
            echo "  --skip-system   跳过系统依赖安装"
            echo "  --skip-venv     跳过虚拟环境创建"
            echo "  --help, -h      显示此帮助"
            echo
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# Run main deployment
main
