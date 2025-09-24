#!/bin/bash
# run_experiments_rate_limited.sh - 针对API限制优化的实验运行脚本

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
FORCE_FLAG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        *)
            # Unknown option, keep for python script
            break
            ;;
    esac
done

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}Rate-Limited Experiment Runner${NC}"
echo -e "${CYAN}================================${NC}"

# Setup NLTK data first
echo -e "\n${YELLOW}Setting up NLTK data...${NC}"
if python setup_nltk.py; then
    echo -e "${GREEN}NLTK setup completed${NC}"
else
    echo -e "${RED}NLTK setup failed${NC}"
    exit 1
fi

# Count agents for progress indication
AGENT_COUNT=$(find agent_data/synthetic_agents -maxdepth 1 -type d -name '[a-f0-9]*' 2>/dev/null | wc -l | tr -d ' ')
TOPICS="zoning healthcare surveillance"
TOTAL_COMBINATIONS=$((AGENT_COUNT * 3))

# Calculate optimal settings for rate limiting
CPU_COUNT=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

# Conservative settings to avoid rate limiting
WORKERS=8  # Reduced from 16
LLM_THREADS=4  # Significantly reduced from 24

echo -e "\n${BLUE}Rate-Limited Configuration:${NC}"
echo -e "  Agents found: ${GREEN}${AGENT_COUNT}${NC}"
echo -e "  Topics: ${GREEN}${TOPICS}${NC}"
echo -e "  Total combinations: ${GREEN}${TOTAL_COMBINATIONS}${NC}"
echo -e "  Max QA per conversation: ${GREEN}20${NC}"
echo -e "  Parallel workers: ${GREEN}${WORKERS}${NC} (conservative)"
echo -e "  LLM threads: ${GREEN}${LLM_THREADS}${NC} (rate-limited)"
echo -e "  Estimated max concurrent requests: ${YELLOW}$((WORKERS * LLM_THREADS))${NC}"

echo -e "\n${PURPLE}Running experiments with rate limiting...${NC}"
echo -e "${PURPLE}=========================================${NC}"

# Run experiments with conservative settings
python -u run_experiments_ultra_parallel.py \
    --topics zoning healthcare surveillance \
    --max-qa 20 \
    --workers $WORKERS \
    --llm-threads $LLM_THREADS \
    $FORCE_FLAG \
    2>&1 | while IFS= read -r line; do
        case "$line" in
            *"Found"*"synthetic agents"*)
                echo -e "${CYAN}$line${NC}"
                ;;
            *"Processing"*"combinations"*)
                echo -e "${BLUE}$line${NC}"
                ;;
            *"SUCCESS"*|*"OK"*|*" - success"*)
                echo -e "${GREEN}$line${NC}"
                ;;
            *"ERROR"*|*"FAILED"*|*" - error"*)
                echo -e "${RED}$line${NC}"
                ;;
            *"SKIP"*|*" - skipped"*)
                echo -e "${YELLOW}$line${NC}"
                ;;
            *"RERUN"*|*"need rerun"*)
                echo -e "${YELLOW}$line${NC}"
                ;;
            *"Progress:"*|*"Completed:"*)
                echo -e "${PURPLE}$line${NC}"
                ;;
            *"Rate limited"*|*"429"*|*"Too Many Requests"*)
                echo -e "${YELLOW}⚠️  $line${NC}"
                ;;
            *"Saved experiment summary"*)
                echo -e "${GREEN}$line${NC}"
                ;;
            "="*)
                echo -e "${CYAN}$line${NC}"
                ;;
            "-"*)
                echo -e "${BLUE}$line${NC}"
                ;;
            *)
                echo "$line"
                ;;
        esac
    done

EXIT_CODE=${PIPESTATUS[0]}

echo -e "\n${CYAN}Rate-Limited Experiment Complete!${NC}"
echo -e "${CYAN}==================================${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All experiments completed successfully${NC}"
    
    # Show summary if available
    if [ -f "agent_data/synthetic_agents/experiment_summary.json" ]; then
        echo -e "\n${BLUE}Quick Summary:${NC}"
        python -c "
import json
try:
    with open('agent_data/synthetic_agents/experiment_summary.json', 'r') as f:
        summary = json.load(f)
    stats = summary.get('statistics', {})
    print(f'  Total experiments: {stats.get(\"total_experiments\", 0)}')
    print(f'  Successful: {stats.get(\"successful\", 0)}')
    print(f'  Failed: {stats.get(\"failed\", 0)}')
    print(f'  Skipped: {stats.get(\"skipped\", 0)}')
    
    by_topic = stats.get('by_topic', {})
    if by_topic:
        print('  By topic:')
        for topic, info in by_topic.items():
            print(f'    {topic}: {info.get(\"count\", 0)} conversations, avg {info.get(\"avg_qa_count\", 0):.1f} QA pairs')
except Exception as e:
    print(f'  Could not read summary: {e}')
" 2>/dev/null
    fi
    
    echo -e "\n${GREEN}Ready for analysis!${NC}"
else
    echo -e "${RED}Experiments failed with exit code $EXIT_CODE${NC}"
    echo -e "${YELLOW}Consider further reducing --workers and --llm-threads if rate limiting persists${NC}"
fi

echo -e "\n${CYAN}Rate Limiting Tips:${NC}"
echo -e "• If you still see 429 errors, try: --workers 4 --llm-threads 2"
echo -e "• For even slower but stable: --workers 2 --llm-threads 1"
echo -e "• Check your API plan limits at: https://dashscope.console.aliyun.com/"

exit $EXIT_CODE
