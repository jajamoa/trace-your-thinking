# 服务器部署指南

## 🚀 一键部署

### 方式1：完整部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-repo/tyt-synth-agent.git
cd tyt-synth-agent

# 运行完整部署脚本
bash deploy_server.sh
```

### 方式2：快速部署

```bash
# 克隆仓库后
bash quick_deploy.sh
```

## 📋 部署检查清单

### 系统要求
- [ ] Python 3.8+
- [ ] 8GB+ RAM (推荐16GB+)
- [ ] 20GB+ 磁盘空间
- [ ] 稳定网络连接

### 环境配置
- [ ] 系统依赖已安装
- [ ] Python依赖已安装
- [ ] NLTK数据已下载
- [ ] API密钥已配置

## 🛠️ 手动部署步骤

如果自动脚本失败，可以手动执行：

### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git curl
```

**CentOS/RHEL:**
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip git curl
```

### 2. 安装Python依赖

```bash
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
```

### 3. 准备NLTK数据

```bash
cd experiment
python3 setup_nltk.py
cd ..
```

### 4. 配置API密钥

```bash
echo "DASHSCOPE_API_KEY=your_api_key_here" > .env.local
```

## 🎯 运行实验

### 标准配置
```bash
cd experiment
bash run_experiments_ultra_parallel.sh
```

### 高性能配置（推荐云服务器）
```bash
cd experiment
bash run_experiments_ultra_parallel.sh --workers 32 --llm-threads 48
```

### 自定义配置
```bash
cd experiment
python run_experiments_ultra_parallel.py \
    --topics zoning healthcare surveillance \
    --max-qa 20 \
    --workers 16 \
    --llm-threads 24 \
    --agents agent1 agent2 agent3  # 指定特定agents
```

## ☁️ 云服务器推荐配置

### 阿里云ECS
- **实例类型**: ecs.c7.4xlarge (16核32GB)
- **存储**: 100GB SSD
- **带宽**: 10Mbps+
- **预计成本**: ¥4-6/小时

### 腾讯云CVM  
- **实例类型**: S5.4XLARGE32 (16核32GB)
- **存储**: 100GB SSD
- **带宽**: 10Mbps+
- **预计成本**: ¥3-5/小时

### AWS EC2
- **实例类型**: c5.4xlarge (16核32GB)
- **存储**: 100GB EBS
- **带宽**: 不限
- **预计成本**: $0.68/小时

## 🔧 常见问题

### NLTK数据下载失败
```bash
# 手动下载
python3 -c "
import nltk
nltk.download('wordnet')
nltk.download('punkt')
"
```

### 权限问题
```bash
# 修复pip权限
python3 -m pip install --user -r requirements.txt

# 修复NLTK目录权限
mkdir -p ~/nltk_data
chmod 755 ~/nltk_data
```

### 内存不足
```bash
# 减少并行度
python run_experiments_ultra_parallel.py --workers 4 --llm-threads 8
```

### API限流
```bash
# 降低并发
python run_experiments_ultra_parallel.py --llm-threads 4
```

## 📊 监控实验进度

### 查看实时日志
```bash
tail -f experiment.log
```

### 检查实验状态
```bash
# 查看已完成的实验
find agent_data/synthetic_agents -name "experiment_summary.json"

# 统计完成数量
find agent_data/synthetic_agents -name "*.csv" -path "*/transcript/raw/*" | wc -l
```

## 🔄 结果收集

### 打包实验结果
```bash
tar -czf experiment_results.tar.gz \
  agent_data/synthetic_agents/experiment_summary.json \
  agent_data/synthetic_agents/*/transcript/raw/ \
  agent_data/synthetic_agents/*/cbn_capture/ \
  agent_data/synthetic_agents/*/survey/
```

### 下载到本地
```bash
# 从服务器下载
scp user@server:/path/to/experiment_results.tar.gz ./
```

## 💡 性能优化建议

1. **使用SSD存储**：显著提升I/O性能
2. **增加内存**：减少交换，提升并行效率  
3. **优化网络**：API调用密集，需要稳定网络
4. **监控资源**：使用`htop`监控CPU和内存使用
5. **日志轮转**：避免日志文件过大

## 🚨 安全注意事项

1. **保护API密钥**：不要提交到git
2. **防火墙配置**：只开放必要端口
3. **定期更新**：保持系统和依赖最新
4. **备份数据**：重要实验结果及时备份
