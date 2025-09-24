#!/bin/bash
# run_experiments_staggered.sh - 分批启动实验避免thundering herd

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
BATCH_SIZE=6  # Number of workers to start at once
BATCH_DELAY=10  # Seconds between batches

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --batch-delay)
            BATCH_DELAY="$2"
            shift 2
            ;;
        *)
            # Unknown option, keep for python script
            break
            ;;
    esac
done

echo -e "${CYAN}====================================${NC}"
echo -e "${CYAN}Staggered Experiment Runner${NC}"
echo -e "${CYAN}====================================${NC}"

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

# Calculate staggered settings
TOTAL_WORKERS=12  # Conservative total
LLM_THREADS=6     # Conservative per worker
BATCHES=$(( (TOTAL_WORKERS + BATCH_SIZE - 1) / BATCH_SIZE ))  # Ceiling division

echo -e "\n${BLUE}Staggered Configuration:${NC}"
echo -e "  Agents found: ${GREEN}${AGENT_COUNT}${NC}"
echo -e "  Topics: ${GREEN}${TOPICS}${NC}"
echo -e "  Total combinations: ${GREEN}${TOTAL_COMBINATIONS}${NC}"
echo -e "  Max QA per conversation: ${GREEN}20${NC}"
echo -e "  Total workers: ${GREEN}${TOTAL_WORKERS}${NC}"
echo -e "  Batch size: ${GREEN}${BATCH_SIZE}${NC} workers"
echo -e "  Batch delay: ${GREEN}${BATCH_DELAY}${NC} seconds"
echo -e "  Number of batches: ${GREEN}${BATCHES}${NC}"
echo -e "  LLM threads per worker: ${GREEN}${LLM_THREADS}${NC}"

echo -e "\n${PURPLE}Running experiments with staggered start...${NC}"
echo -e "${PURPLE}==========================================${NC}"

# Create a Python script for staggered execution
cat > /tmp/staggered_experiment.py << EOF
import subprocess
import time
import sys
import os

def run_batch(batch_num, workers, llm_threads, force_flag):
    print(f"🚀 Starting batch {batch_num} with {workers} workers...")
    
    cmd = [
        sys.executable, "run_experiments_ultra_parallel.py",
        "--topics", "zoning", "healthcare", "surveillance",
        "--max-qa", "20",
        "--workers", str(workers),
        "--llm-threads", str(llm_threads)
    ]
    
    if force_flag:
        cmd.append("--force")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Read output in real-time
    for line in iter(process.stdout.readline, ''):
        if line:
            # Color code output
            line = line.strip()
            if "SUCCESS" in line:
                print(f"\\033[0;32m{line}\\033[0m")
            elif "ERROR" in line or "FAILED" in line:
                print(f"\\033[0;31m{line}\\033[0m")
            elif "Rate limited" in line or "429" in line:
                print(f"\\033[1;33m⚠️  {line}\\033[0m")
            elif "Progress:" in line:
                print(f"\\033[0;35m{line}\\033[0m")
            else:
                print(line)
    
    return_code = process.wait()
    return return_code

# Main execution
batch_size = ${BATCH_SIZE}
total_workers = ${TOTAL_WORKERS}
batch_delay = ${BATCH_DELAY}
llm_threads = ${LLM_THREADS}
force_flag = "${FORCE_FLAG}" == "--force"

batches = []
remaining_workers = total_workers

for i in range(0, total_workers, batch_size):
    workers_in_batch = min(batch_size, remaining_workers)
    batches.append(workers_in_batch)
    remaining_workers -= workers_in_batch

print(f"📊 Batch plan: {batches}")

# Run batches with delays
for i, workers in enumerate(batches, 1):
    if i > 1:
        print(f"⏰ Waiting {batch_delay} seconds before next batch...")
        time.sleep(batch_delay)
    
    return_code = run_batch(i, workers, llm_threads, force_flag)
    
    if return_code != 0:
        print(f"❌ Batch {i} failed with exit code {return_code}")
        sys.exit(return_code)

print("🎉 All batches completed successfully!")
EOF

# Run the staggered experiment
python /tmp/staggered_experiment.py

EXIT_CODE=$?

# Cleanup
rm -f /tmp/staggered_experiment.py

echo -e "\n${CYAN}Staggered Experiment Complete!${NC}"
echo -e "${CYAN}===============================${NC}"

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
except Exception as e:
    print(f'  Could not read summary: {e}')
" 2>/dev/null
    fi
    
    echo -e "\n${GREEN}Ready for analysis!${NC}"
else
    echo -e "${RED}Experiments failed with exit code $EXIT_CODE${NC}"
fi

echo -e "\n${CYAN}Staggered Start Benefits:${NC}"
echo -e "• Prevents all workers from hitting API limits simultaneously"
echo -e "• Reduces thundering herd effect"
echo -e "• More stable and predictable execution"
echo -e "• Better resource utilization"

exit $EXIT_CODE
