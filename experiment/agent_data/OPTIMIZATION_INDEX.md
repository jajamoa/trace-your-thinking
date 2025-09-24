# CBN Generator Project File Index

## Core Generators

### 1. **enhanced_unified_agent_generator.py** ⭐ CURRENT
- **Purpose**: enhanced unified agent generator with rich prompt CBNs
- **Features**: 15-20 nodes, BFS subgraph extraction, 2-hop neighborhood
- **Usage**: `python enhanced_unified_agent_generator.py --num_agents 100`

### 1a. **fixed_unified_agent_generator.py** (previous)
- **Purpose**: fixed unified agent generator, ensures no empty CBNs
- **Features**: connectivity validation, but smaller prompt CBNs (3-6 nodes)
- **Status**: replaced by enhanced version

### 1b. **unified_agent_generator.py** (deprecated)
- **Purpose**: original unified agent generator
- **Issue**: could generate empty prompt CBNs
- **Status**: replaced by fixed/enhanced versions

### 2. **synthetic_cbn_generator.py**
- **Purpose**: original CBN generator
- **Status**: baseline version with lower similarity

### 3. **optimized_synthetic_cbn_generator.py**
- **Purpose**: first optimization attempt
- **Improvement**: semantic generation
- **Issue**: structural over-optimization

### 4. **balanced_synthetic_cbn_generator.py** ⭐ Recommended
- **Purpose**: balanced optimization version
- **Achievement**: 53.25% similarity
- **Features**: good balance between structure and semantics

### 5. **edge_aware_synthetic_cbn_generator.py**
- **Purpose**: edge pattern-aware generator
- **Features**: considers node connection patterns
- **Use case**: scenarios requiring specific edge patterns

## Analysis Tools

### 6. **cbn_statistics_analyzer.py** ⭐
- **Purpose**: analyze statistical features of real CBN data
- **Features**: intelligent caching, avoids redundant computation
- **Output**: statistical JSON files for each topic

### 7. **edge_pattern_analyzer.py**
- **Purpose**: analyze edge connection patterns in CBNs
- **Functions**: node categorization, pattern statistics
- **Usage**: `python edge_pattern_analyzer.py camera`

### 8. **cbn_similarity_analyzer.py**
- **Purpose**: basic similarity analysis
- **Metrics**: structural and semantic similarity

### 9. **enhanced_cbn_similarity_analyzer.py** ⭐
- **Purpose**: enhanced similarity analysis
- **Features**: includes edge pattern similarity
- **Usage**: `python enhanced_cbn_similarity_analyzer.py synthetic_agents camera output_dir`

## Scripts and Documentation

### 10. **generate_agents.sh**
- **Purpose**: shell script for quick agent generation
- **Usage**: `./generate_agents.sh 100 output_dir`

### 11. **run_similarity_analysis.py**
- **Purpose**: wrapper script for running similarity analysis

### 12. **example_usage.py**
- **Purpose**: example code demonstrating generator usage

### 13. **test_unified_generator.py**
- **Purpose**: test unified generator

## Documentation

### 14. **ENHANCED_CBN_SUMMARY.md** ⭐ Latest Update
- **Content**: enhanced CBN generator with rich prompt CBNs (15-20 nodes)

### 15. **FINAL_OPTIMIZATION_SUMMARY.md** ⭐ Must Read
- **Content**: complete optimization journey and results summary

### 16. **HOW_TO_USE.md**
- **Content**: quick usage guide

## Quick Start

```bash
# 1. Generate 100 agents
./generate_agents.sh 100

# 2. Analyze similarity
python enhanced_cbn_similarity_analyzer.py synthetic_agents camera analysis_output

# 3. View results
cat analysis_output/enhanced_similarity_report.txt
```

## Recommended Usage

- **Generate agents**: use `enhanced_unified_agent_generator.py` (via `./generate_agents.sh`)
- **Analysis tools**: use `enhanced_cbn_similarity_analyzer.py` for comprehensive analysis
- **Learn more**: read `ENHANCED_CBN_SUMMARY.md` and `FINAL_OPTIMIZATION_SUMMARY.md`
