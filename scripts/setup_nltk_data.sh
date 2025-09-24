#!/bin/bash
# NLTK Data Setup Script
# 专门用于在新服务器上安装NLTK数据

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}NLTK Data Setup${NC}"
echo -e "${BLUE}===============${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.8+ first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"

# Check if in correct directory
if [[ ! -f "experiment/setup_nltk.py" ]]; then
    echo -e "${RED}✗ Please run this script from the tyt-synth-agent root directory${NC}"
    exit 1
fi

# Install NLTK if needed
echo -e "\n${YELLOW}Checking NLTK installation...${NC}"
if python3 -c "import nltk" 2>/dev/null; then
    echo -e "${GREEN}✓ NLTK already installed${NC}"
else
    echo -e "${YELLOW}Installing NLTK...${NC}"
    # Try different installation methods
    if python3 -m pip install nltk 2>/dev/null; then
        echo -e "${GREEN}✓ NLTK installed via pip${NC}"
    elif python3 -m pip install --user nltk 2>/dev/null; then
        echo -e "${GREEN}✓ NLTK installed via pip --user${NC}"
    elif python3 -m pip install --break-system-packages nltk 2>/dev/null; then
        echo -e "${GREEN}✓ NLTK installed via pip --break-system-packages${NC}"
    else
        echo -e "${RED}✗ Could not install NLTK automatically${NC}"
        echo -e "${YELLOW}Please install NLTK manually:${NC}"
        echo -e "  pip3 install nltk"
        echo -e "  # or"
        echo -e "  pip3 install --user nltk"
        exit 1
    fi
fi

# Setup NLTK data
echo -e "\n${YELLOW}Setting up NLTK data...${NC}"
NLTK_DATA_DIR="$HOME/nltk_data"

echo -e "NLTK data directory: ${BLUE}$NLTK_DATA_DIR${NC}"

# Create directory if it doesn't exist
mkdir -p "$NLTK_DATA_DIR"

# Run the setup script
python3 experiment/setup_nltk.py

# Verify installation
echo -e "\n${YELLOW}Verifying NLTK data...${NC}"
if [[ -d "$NLTK_DATA_DIR/corpora/wordnet" && -d "$NLTK_DATA_DIR/tokenizers/punkt" ]]; then
    echo -e "${GREEN}✓ NLTK data verified successfully${NC}"
    echo -e "  - WordNet: $NLTK_DATA_DIR/corpora/wordnet"
    echo -e "  - Punkt: $NLTK_DATA_DIR/tokenizers/punkt"
else
    echo -e "${RED}✗ NLTK data verification failed${NC}"
    exit 1
fi

# Test import
echo -e "\n${YELLOW}Testing NLTK imports...${NC}"
python3 -c "
import sys
sys.path.append('.')
from backend.nltk_setup import check_nltk_data
if check_nltk_data():
    print('✓ NLTK data accessible from Python')
else:
    print('✗ NLTK data not accessible')
    sys.exit(1)
"

echo -e "\n${GREEN}==============================${NC}"
echo -e "${GREEN}✓ NLTK setup completed!${NC}"
echo -e "${GREEN}==============================${NC}"

echo -e "\n${BLUE}Info:${NC}"
echo -e "- Data location: $NLTK_DATA_DIR"
echo -e "- Data size: $(du -sh "$NLTK_DATA_DIR" 2>/dev/null | cut -f1 || echo 'unknown')"
echo -e "- This data will be shared by all Python processes"

echo -e "\n${GREEN}Ready for experiments! 🚀${NC}"
