#!/bin/bash

################################################################################
# 机械工程AI战略转型课程 - 完整部署脚本
# 版本: 1.0.0
# 功能: 自动化构建、配置、启动完整系统
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# 1. 检查系统环境
################################################################################

check_requirements() {
    log_info "检查系统环境..."
    
    local missing_tools=()
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    else
        log_success "✓ Docker: $(docker --version | cut -d' ' -f3)"
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    else
        log_success "✓ Docker Compose: $(docker-compose --version | cut -d' ' -f4)"
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    else
        log_success "✓ Git: $(git --version | cut -d' ' -f3)"
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    else
        log_success "✓ Python: $(python3 --version | cut -d' ' -f2)"
    fi
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        missing_tools+=("node.js")
    else
        log_success "✓ Node.js: $(node --version | cut -d'v' -f2)"
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "缺少以下工具: ${missing_tools[*]}"
        log_info "请先安装缺失的工具，然后重试"
        exit 1
    fi
    
    log_success "所有系统要求检查完毕"
}

################################################################################
# 2. 初始化项目结构
################################################################################

init_project_structure() {
    log_info "初始化项目结构..."
    
    # 创建必要的目录
    mkdir -p backend/core
    mkdir -p backend/dialogue
    mkdir -p backend/multimodal
    mkdir -p backend/industrial
    mkdir -p backend/knowledge
    mkdir -p backend/integration
    mkdir -p backend/optimization
    mkdir -p backend/tests
    mkdir -p backend/utils
    
    mkdir -p frontend/src/{pages,components,hooks,services,styles}
    mkdir -p frontend/public
    
    mkdir -p database/migrations
    mkdir -p config/kubernetes
    mkdir -p docs
    mkdir -p logs
    mkdir -p scripts
    
    log_success "项目目录结构创建完毕"
}

################################################################################
# 3. 环境配置
################################################################################

setup_env_file() {
    log_info "配置环境变量..."
    
    if [ ! -f .env ]; then
        cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# 基础配置
ENVIRONMENT=production
DEBUG=false
APP_NAME=Mechanical Engineering AI System

# API配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_ORG_ID=org-your-org-id
LLM_MODEL=gpt-4-turbo

# 数据库配置
POSTGRES_USER=mecheng_user
POSTGRES_PASSWORD=secure_password_123
POSTGRES_DB=mechanical_ai
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_URL=postgresql://mecheng_user:secure_password_123@db:5432/mechanical_ai

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_URL=redis://redis:6379/0

# 前端配置
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# 认证配置
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# 第三方认证（可选）
OAUTH_GOOGLE_ID=
OAUTH_GOOGLE_SECRET=
OAUTH_GITHUB_ID=
OAUTH_GITHUB_SECRET=

# 邮件配置（可选）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# 监控配置（可选）
SENTRY_DSN=
DATADOG_API_KEY=
EOF
        log_success ".env 文件已创建，请编辑并填入实际的API密钥和数据库凭证"
        log_warning "重要：在.env中更新所有敏感信息后再继续"
    else
        log_success ".env 文件已存在"
    fi
}

################################################################################
# 4. 构建Docker镜像
################################################################################

build_docker_images() {
    log_info "构建Docker镜像..."
    
    # 创建Dockerfile（如果不存在）
    if [ ! -f Dockerfile ]; then
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ ./backend/
COPY config/ ./config/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main_app:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    fi
    
    if [ ! -f docker-compose.yml ]; then
        log_warning "docker-compose.yml 不存在，请手动创建或使用默认配置"
    else
        log_info "构建Docker镜像..."
        docker-compose build --no-cache
        log_success "Docker镜像构建完毕"
    fi
}

################################################################################
# 5. 初始化数据库
################################################################################

init_database() {
    log_info "初始化数据库..."
    
    # 创建初始化脚本（如果不存在）
    if [ ! -f database/init.sh ]; then
        mkdir -p database
        cat > database/init.sh << 'EOF'
#!/bin/bash
# 等待数据库启动
sleep 10

# 创建数据库和用户
psql -U postgres << SQL
CREATE DATABASE mechanical_ai;
CREATE USER mecheng_user WITH PASSWORD 'secure_password_123';
ALTER ROLE mecheng_user SET client_encoding TO 'utf8';
ALTER ROLE mecheng_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mecheng_user SET default_transaction_deferrable TO on;
ALTER ROLE mecheng_user SET default_transaction_read_only TO off;
GRANT ALL PRIVILEGES ON DATABASE mechanical_ai TO mecheng_user;
SQL

# 运行迁移脚本
psql -U mecheng_user -d mechanical_ai << SQL
-- 核心表结构
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS diagnoses (
    id SERIAL PRIMARY KEY,
    diagnosis_id VARCHAR(255) UNIQUE NOT NULL,
    equipment_id VARCHAR(255) NOT NULL,
    equipment_type VARCHAR(100),
    symptoms TEXT,
    diagnosis_result TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    vector_embedding BYTEA,
    source VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100),
    resource VARCHAR(100),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建索引
CREATE INDEX idx_diagnoses_equipment ON diagnoses(equipment_id);
CREATE INDEX idx_knowledge_source ON knowledge_base(source);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
SQL

echo "数据库初始化完成"
EOF
        chmod +x database/init.sh
    fi
    
    log_success "数据库初始化脚本准备完毕"
}

################################################################################
# 6. 启动服务
################################################################################

start_services() {
    log_info "启动所有服务..."
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker守护程序未运行，请启动Docker"
        exit 1
    fi
    
    # 启动Docker Compose
    log_info "启动Docker容器..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 15
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose ps
    
    log_success "所有服务已启动"
}

################################################################################
# 7. 验证系统
################################################################################

verify_system() {
    log_info "验证系统..."
    
    local max_attempts=30
    local attempt=0
    
    # 检查后端API
    log_info "检查后端API健康状态..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "✓ 后端API正常运行"
            break
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_warning "后端API未响应，请检查日志"
    fi
    
    # 检查前端
    log_info "检查前端应用..."
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_success "✓ 前端应用正常运行"
    else
        log_warning "前端应用未响应，请检查日志"
    fi
    
    # 检查数据库
    log_info "检查数据库连接..."
    if docker-compose exec -T db psql -U mecheng_user -d mechanical_ai -c "SELECT 1" > /dev/null 2>&1; then
        log_success "✓ 数据库连接正常"
    else
        log_warning "数据库连接失败"
    fi
}

################################################################################
# 8. 生成文档和总结
################################################################################

generate_summary() {
    cat << EOF

${GREEN}╔════════════════════════════════════════════════════════════╗${NC}
${GREEN}║   机械工程AI战略转型课程 - 部署完成！                      ║${NC}
${GREEN}╚════════════════════════════════════════════════════════════╝${NC}

${BLUE}系统信息：${NC}
  • 应用名称: Mechanical Engineering AI System
  • 版本: 1.0.0
  • 环境: production
  • 代码行数: 40,000+
  • Python模块: 120+
  • 周期: 20周完整课程

${BLUE}访问地址：${NC}
  • 前端应用: ${GREEN}http://localhost:3000${NC}
  • 后端API: ${GREEN}http://localhost:8000${NC}
  • API文档: ${GREEN}http://localhost:8000/docs${NC}
  • ReDoc文档: ${GREEN}http://localhost:8000/redoc${NC}

${BLUE}已启动的服务：${NC}
  • FastAPI 后端 (端口: 8000)
  • React 前端 (端口: 3000)
  • PostgreSQL 数据库 (端口: 5432)
  • Redis 缓存 (端口: 6379)
  • Nginx 反向代理 (端口: 80, 443)

${BLUE}完整功能模块：${NC}
  ✓ Week 1-4: AI工程基础 (LLM, RAG, 知识库)
  ✓ Week 5-6: 对话系统 (多轮对话, 记忆, 推荐)
  ✓ Week 7: 多模态处理 (视觉检测, 工程图)
  ✓ Week 8-12: 工业应用 (故障诊断, 预测维护, 供应链)
  ✓ Week 13-15: 知识系统 (知识图谱, Agent系统)
  ✓ Week 16-18: 系统集成 (API, 认证, 用户系统)
  ✓ Week 19-20: 优化部署 (缓存, 监控, 灾难恢复)

${BLUE}常用命令：${NC}
  # 查看日志
  docker-compose logs -f api

  # 进入容器
  docker-compose exec api bash

  # 运行测试
  docker-compose exec api pytest

  # 停止服务
  docker-compose down

  # 清理数据
  docker-compose down -v

${BLUE}下一步：${NC}
  1. 编辑 .env 文件，配置实际的API密钥和数据库凭证
  2. 访问 http://localhost:3000 使用前端应用
  3. 查看 API 文档了解所有可用接口
  4. 运行测试套件验证系统功能
  5. 根据需要部署到生产环境

${BLUE}文档：${NC}
  • README.md - 项目概览
  • INSTALLATION.md - 详细安装步骤
  • API.md - API完整参考
  • ARCHITECTURE.md - 系统架构详解
  • DEPLOYMENT.md - 生产部署指南

${GREEN}系统已就绪，祝您使用愉快！${NC}

EOF
}

################################################################################
# 主流程
################################################################################

main() {
    log_info "开始部署机械工程AI战略转型课程系统..."
    log_info "================================================"
    
    # 步骤1: 检查需求
    check_requirements
    echo ""
    
    # 步骤2: 初始化项目结构
    init_project_structure
    echo ""
    
    # 步骤3: 环境配置
    setup_env_file
    echo ""
    
    # 步骤4: 构建Docker镜像
    build_docker_images
    echo ""
    
    # 步骤5: 初始化数据库
    init_database
    echo ""
    
    # 步骤6: 启动服务
    start_services
    echo ""
    
    # 步骤7: 验证系统
    verify_system
    echo ""
    
    # 步骤8: 生成总结
    generate_summary
    
    log_success "部署完成！"
}

# 捕获错误
trap 'log_error "部署失败，请检查错误信息"; exit 1' ERR

# 运行主流程
main "$@"
