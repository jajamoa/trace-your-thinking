# 服务器安装脚本

这个目录包含用于在新服务器上快速部署TYT Synth Agent实验环境的脚本。

## 📋 脚本列表

### 🚀 `server_setup.sh` - 完整服务器配置
一键配置整个实验环境，包括Python、依赖包、NLTK数据等。

**使用方法：**
```bash
# 在项目根目录运行
./scripts/server_setup.sh
```

**功能：**
- 检查和安装Python 3.8+
- 安装pip和项目依赖
- 下载和配置NLTK数据
- 创建.env.local配置模板
- 验证安装是否成功
- 显示系统信息和推荐配置

### 📚 `setup_nltk_data.sh` - NLTK数据专用安装
专门用于安装NLTK数据，适合已有Python环境的服务器。

**使用方法：**
```bash
# 在项目根目录运行
./scripts/setup_nltk_data.sh
```

**功能：**
- 安装NLTK包（如果需要）
- 下载WordNet和Punkt数据到~/nltk_data
- 验证数据完整性
- 测试Python导入

## 🌐 服务器部署完整流程

### 1. 新的云服务器
```bash
# 1. 连接服务器
ssh root@your_server_ip

# 2. 安装git（如果没有）
yum install -y git  # CentOS/RHEL
# 或
apt install -y git  # Ubuntu/Debian

# 3. 克隆项目
git clone https://github.com/your-repo/tyt-synth-agent.git
cd tyt-synth-agent

# 4. 运行完整安装脚本
./scripts/server_setup.sh

# 5. 配置API密钥
echo "DASHSCOPE_API_KEY=your_actual_key_here" > .env.local

# 6. 测试
cd experiment
python test_experiment.py
```

### 2. 现有服务器（只需NLTK）
```bash
cd tyt-synth-agent
./scripts/setup_nltk_data.sh
```

## 🔧 手动安装步骤

如果自动脚本失败，可以手动执行：

```bash
# 1. 安装Python依赖
pip3 install -r requirements.txt

# 2. 设置NLTK
cd experiment
python3 setup_nltk.py

# 3. 配置环境变量
echo "DASHSCOPE_API_KEY=your_key" > .env.local

# 4. 测试
python3 test_experiment.py
```

## 📊 推荐服务器配置

### 阿里云ECS
- **配置**: ecs.c7.2xlarge (8核32GB)
- **价格**: ~¥2-3/小时
- **Workers**: 16个进程
- **LLM线程**: 24个

### 腾讯云CVM
- **配置**: S5.2XLARGE16 (8核16GB)
- **价格**: ~¥1.5-2/小时
- **Workers**: 12个进程
- **LLM线程**: 16个

### AWS EC2
- **配置**: c5.2xlarge (8核16GB)
- **价格**: ~$0.34/小时
- **Workers**: 12个进程
- **LLM线程**: 16个

## 🐛 常见问题

### Python版本问题
```bash
# 检查Python版本
python3 --version

# 如果版本太低，手动安装新版本
# CentOS/RHEL
yum install -y python38 python38-pip
ln -sf /usr/bin/python3.8 /usr/bin/python3

# Ubuntu/Debian
apt install -y python3.8 python3.8-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
```

### NLTK下载失败
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
# 如果需要root权限安装系统包
sudo ./scripts/server_setup.sh

# 或者分步骤：系统包用root，Python包用用户
sudo yum install -y python3 python3-pip  # root安装系统包
./scripts/setup_nltk_data.sh             # 用户安装NLTK
```

## 🚀 快速验证

安装完成后，运行这些命令验证：

```bash
# 检查Python环境
python3 --version
python3 -c "import nltk, dashscope, requests; print('✓ All imports OK')"

# 检查NLTK数据
python3 experiment/setup_nltk.py

# 检查API配置
grep DASHSCOPE_API_KEY .env.local

# 运行测试
cd experiment && python3 test_experiment.py
```

安装成功后即可运行实验：
```bash
cd experiment
bash run_experiments_ultra_parallel.sh
```
