# 🚀 机械工程AI诊断系统 - 部署指南

## 📋 目录
- [快速启动](#快速启动)
- [系统要求](#系统要求)
- [详细安装步骤](#详细安装步骤)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

---

## ⚡ 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/hcbwsw/mechanical-engineering-ai.git
cd mechanical-engineering-ai

# 2. 一键启动（Linux/Mac）
# start.sh / stop.sh / restart.sh 位于项目根目录（与 main_app.py 同级），扩展名为 .sh
bash start.sh

# 3. 打开浏览器
# 前端: http://localhost:8080/Unified%20Application%20Hub.html
# API 文档: http://localhost:8010/docs（与 main_app 默认端口一致，可用 BACKEND_PORT 覆盖）
```

**Windows 用户** 参考本文档底部的 Windows 启动说明。

---

## 💻 系统要求

| 组件 | 要求 | 推荐 |
|------|------|------|
| **操作系统** | Linux/Mac/Windows | Ubuntu 20.04+ / Mac 11+ / Windows 10+ |
| **Python** | 3.9+ | 3.10+ |
| **内存** | 2GB最小 | 4GB+ |
| **磁盘** | 500MB | 1GB+ |
| **网络** | 需要连接 | 可离线运行（静态文件） |

### 必需软件
- ✅ Python 3.9 或更高版本
- ✅ pip（Python包管理器）

### 可选软件
- Docker（用于容器化部署）
- Git（版本控制）

---

## 📦 详细安装步骤

### 步骤1：准备环境

```bash
# 检查Python版本
python3 --version  # 需要3.9+

# 检查pip
pip3 --version

# 更新pip
pip3 install --upgrade pip
```

### 步骤2：克隆项目

```bash
git clone https://github.com/hcbwsw/mechanical-engineering-ai.git
cd mechanical-engineering-ai
```

### 步骤3：创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 步骤4：安装依赖

```bash
pip install -r requirements.txt
```

如果没有requirements.txt，执行：
```bash
pip install fastapi uvicorn numpy pandas scikit-learn pydantic python-multipart
```

### 步骤5：启动系统

**Linux/Mac（推荐用脚本，在项目根执行）：**
```bash
cd mechanical-engineering-ai   # 仓库根目录，须含 main_app.py、start.sh
bash start.sh
```

**Windows / 手动分终端：**
```bash
# 在项目根目录（含 main_app.py）
cd mechanical-engineering-ai
python -m uvicorn main_app:app --reload --host 0.0.0.0 --port 8010

# 另一终端：前端静态目录
cd mechanical-engineering-ai/前端
python -m http.server 8080
```

---

## 🌐 访问地址

启动成功后，使用以下地址访问：

### 前端应用（用户界面）
```
http://localhost:8080
```
进入统一应用Hub，选择需要的功能模块

### 后端 API 文档（开发者）
```
http://localhost:8010/docs
```
Swagger UI，接口前缀一般为 **`/api/v1/...`**。

### API 调用示例
```bash
# 健康检查
curl -sS http://localhost:8010/health

# 故障诊断提交（路径以 main_app 为准）
curl -X POST "http://localhost:8010/api/v1/diagnosis/submit" \
  -H "Content-Type: application/json" \
  -d '{"equipment_id":"P-101","equipment_type":"离心泵","symptoms":"轴承部位异常振动"}'

# 知识库检索（POST）
curl -X POST "http://localhost:8010/api/v1/knowledge/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"轴承故障","top_k":5}'
```

---

## 🔧 常用命令

### 启动/停止/重启

均在**项目根目录**执行（与 `main_app.py`、`start.sh` 同级）：

```bash
cd mechanical-engineering-ai

bash start.sh
bash stop.sh
bash restart.sh
```

### 查看日志

```bash
# 在项目根
tail -f backend.log
tail -f 前端/frontend.log
```

### 调试模式

```bash
# 在项目根启动后端（开发模式，自动重载）
python -m uvicorn main_app:app --reload --host 0.0.0.0 --port 8010

cd 前端
python -m http.server 8080
```

---

## ❓ 常见问题

### Q1: 端口被占用

**问题：** `Address already in use` / `OSError: [Errno 48] Address already in use`

**常见原因：** 本机同时跑了 **`docker compose`**（API 映射 **8010**、Nginx 前端常映射 **8080**）和 **`bash start.sh`**，两套服务抢同一端口。

**解决方案：**
```bash
# 二选一即可，不要两套同时占 8010/8080

# A) 只用 Docker：在项目根执行
docker compose up -d
# 此时不要再 bash start.sh

# B) 只用本机脚本：先停 Docker 映射
docker compose down
bash stop.sh
bash start.sh

# 方案：换端口（与 Docker 并存时）
BACKEND_PORT=8020 FRONTEND_PORT=18080 bash start.sh

# 查看谁占用端口
lsof -nP -iTCP:8010 -sTCP:LISTEN
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

### Q2: Python版本过低

**问题：** Python 3.8 或更低版本

**解决方案：**
```bash
# 安装Python 3.10
# Ubuntu:
sudo apt-get install python3.10

# Mac:
brew install python@3.10

# 检查版本
python3 --version
```

### Q3: 依赖安装失败

**问题：** pip install 报错

**解决方案：**
```bash
# 升级pip
pip install --upgrade pip setuptools wheel

# 清除缓存
pip cache purge

# 重新安装
pip install -r requirements.txt -v
```

### Q4: 无法访问前端/后端

**问题：** 浏览器无法连接到 localhost

**解决方案：**
```bash
# 检查服务是否在运行
ps aux | grep uvicorn
ps aux | grep http.server

# 查看日志（项目根）
tail -f backend.log

# 检查防火墙（按需放行 8010、8080）
```

### Q5: 如何修改端口？

在项目根执行：

```bash
BACKEND_PORT=9000 bash start.sh
FRONTEND_PORT=9080 bash start.sh
BACKEND_PORT=9000 FRONTEND_PORT=9080 bash start.sh
```

---

## 🐳 Docker 部署（可选）

### 使用 Docker Compose

在**项目根目录**（含 `docker-compose.yml`、`main_app.py`）执行：

```bash
docker compose up -d --build

docker compose logs -f api

docker compose down
```

### 使用Docker命令

```bash
# 构建镜像
docker build -t mechanical-ai:latest .

# 运行容器
docker run -d \
  -p 8010:8010 \
  --name mechanical-ai-api \
  mechanical-ai:latest

# 查看日志
docker logs -f mechanical-ai-api

# 停止容器
docker stop mechanical-ai-api
docker rm mechanical-ai-api
```

---

## ⚙️ 高级配置

### 性能优化

#### 1. 增加Worker数量（生产环境）

```bash
# 后端（默认1个worker，生产建议4-8个）
python -m uvicorn main_app:app \
  --workers 4 \
  --host 0.0.0.0 \
  --port 8010
```

#### 2. 启用缓存

```bash
# 如果有Redis，配置缓存
# 在main_app.py中配置redis连接
REDIS_URL=redis://localhost:6379/0
```

#### 3. 数据库连接池

```bash
# 提高并发性能
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### 生产部署

#### 使用Nginx反向代理

```nginx
upstream backend {
    server localhost:8010;
}

upstream frontend {
    server localhost:8080;
}

server {
    listen 80;
    server_name example.com;

    # 后端API
    location /api/ {
        proxy_pass http://backend;
    }

    # 前端
    location / {
        proxy_pass http://frontend;
    }
}
```

#### 使用Supervisor管理进程

```ini
[program:mechanical-ai-backend]
command=/home/user/mechanical-engineering-ai/venv/bin/python -m uvicorn main_app:app
directory=/home/user/mechanical-engineering-ai
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/mechanical-ai-backend.log

[program:mechanical-ai-frontend]
command=python -m http.server 8080
directory=/home/user/mechanical-engineering-ai/前端
user=www-data
autostart=true
autorestart=true
```

---

## 📊 系统监控

### 查看系统资源占用

```bash
# 实时监控
top -p $(pgrep -f uvicorn),$(pgrep -f http.server)

# 内存使用
ps aux | grep "uvicorn\|http.server"

# 网络连接
netstat -tuln | grep :8010
```

### 健康检查

```bash
# 检查后端健康状态
curl http://localhost:8010/health

# 检查前端是否可访问
curl http://localhost:8080/Unified\ Application\ Hub.html
```

---

## 🚨 故障排查

### 后端崩溃

1. 查看日志
   ```bash
   tail -100 backend.log
   ```

2. 检查Python版本兼容性
   ```bash
   python3 --version
   ```

3. 检查依赖完整性
   ```bash
   pip check
   ```

4. 重新安装依赖
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

### 前端显示白页

1. 检查文件存在性
   ```bash
   ls -la 前端/*.html
   ```

2. 检查端口
   ```bash
   curl http://localhost:8080/
   ```

3. 查看浏览器控制台错误
   - 按F12打开开发者工具
   - 查看Console标签

### API调用报错

1. 确认后端运行
   ```bash
   curl http://localhost:8010/docs
   ```

2. 查看API日志
   ```bash
   tail -f backend.log
   ```

3. 使用Swagger UI测试
   ```
   http://localhost:8010/docs
   ```

---

## 📞 支持

- 📧 项目地址: https://github.com/hcbwsw/mechanical-engineering-ai
- 📝 提交Issue: 遇到问题请提交Issue报告
- 💬 讨论: 在Discussions中交流想法

---

## 📝 许可证

MIT License - 详见 LICENSE 文件

---

**版本：** 1.0  
**最后更新：** 2026-03-22  
**维护者：** 机械工程AI团队
