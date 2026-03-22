#!/usr/bin/env bash

################################################################################
# 机械工程 AI 系统 — 一键启动（后端 API + 前端静态页）
# 位于项目根目录（与 main_app.py、requirements.txt 同级）。
# 使用：在项目根执行  bash start.sh
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error()   { echo -e "${RED}✗ $1${NC}"; }
print_info()    { echo -e "${YELLOW}➜ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
FRONTEND_DIR="$PROJECT_ROOT/前端"

# 检测本机 TCP 端口是否已被监听（避免与 Docker / 旧进程冲突）
port_in_use() {
    local p=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
    else
        return 1
    fi
}

require_free_port() {
    local p=$1
    local name=$2
    if port_in_use "$p"; then
        print_error "端口 ${p} 已被占用（${name}）。"
        print_info "常见原因：本机正在跑 docker compose（API 常用 8010、Nginx 前端常用 8080），或上次未执行 bash stop.sh。"
        print_info "排查命令: lsof -nP -iTCP:${p} -sTCP:LISTEN"
        print_info "可先:（项目根）docker compose down ；再 bash stop.sh"
        print_info "或换端口启动: BACKEND_PORT=8020 FRONTEND_PORT=18080 bash start.sh"
        exit 1
    fi
}

print_header "机械工程 AI 系统启动"

LOCAL_IP="127.0.0.1"
if [[ "$(uname -s)" == "Darwin" ]]; then
    _ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
    [[ -n "$_ip" ]] && LOCAL_IP="$_ip"
elif command -v hostname >/dev/null 2>&1; then
    _ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    [[ -n "$_ip" ]] && LOCAL_IP="$_ip"
fi

print_info "正在检查系统环境..."
if ! command -v python3 &>/dev/null; then
    print_error "未找到 Python 3，请先安装 Python 3.9+"
    exit 1
fi
print_success "Python $(python3 --version | cut -d' ' -f2)"

if ! command -v pip3 &>/dev/null; then
    print_error "未找到 pip3"
    exit 1
fi
print_success "pip3 已就绪"

print_header "配置 Python 虚拟环境"
if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
    print_info "创建虚拟环境..."
    python3 -m venv "$PROJECT_ROOT/venv"
    print_success "虚拟环境已创建"
else
    print_success "虚拟环境已存在"
fi
# shellcheck source=/dev/null
source "$PROJECT_ROOT/venv/bin/activate"
print_success "虚拟环境已激活"

print_info "升级 pip..."
pip install --upgrade pip setuptools wheel -q
print_success "pip 已升级"

print_header "安装后端依赖"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    print_info "从 requirements.txt 安装..."
    pip install -r "$REQUIREMENTS_FILE" -q
    print_success "后端依赖已安装"
else
    print_info "未找到 requirements.txt，安装最小依赖..."
    pip install fastapi "uvicorn[standard]" pydantic pydantic-settings sqlalchemy psycopg2-binary redis -q
    print_success "最小依赖已安装"
fi

print_header "验证后端代码"
MAIN_APP="$PROJECT_ROOT/main_app.py"
if [[ ! -f "$MAIN_APP" ]]; then
    print_error "未找到 $MAIN_APP（请在项目根目录执行本脚本）"
    exit 1
fi
print_success "main_app.py 已确认"

print_header "验证前端文件"
if [[ ! -d "$FRONTEND_DIR" ]]; then
    print_error "未找到目录: $FRONTEND_DIR"
    exit 1
fi
FRONTEND_FILES=(
    "Unified Application Hub.html"
    "Mechanical Engineering AI Dashboard.html"
    "Knowledge Base Search Frontend.html"
    "Multi-Agent Execution Frontend.html"
    "User Authentication Frontend.html"
    "Analytics Dashboard Frontend.html"
)
for file in "${FRONTEND_FILES[@]}"; do
    if [[ -f "$FRONTEND_DIR/$file" ]]; then
        print_success "$file"
    else
        print_info "⚠ $file 未找到（可选）"
    fi
done

BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

require_free_port "$BACKEND_PORT" "后端 API（uvicorn）"
require_free_port "$FRONTEND_PORT" "前端静态服务（http.server）"

print_header "启动后端 API"
print_info "端口: $BACKEND_PORT"
print_info "API 文档: http://$LOCAL_IP:$BACKEND_PORT/docs"

BACKEND_PID_FILE="/tmp/mechanical_ai_backend.pid"
cd "$PROJECT_ROOT"
nohup python3 -m uvicorn main_app:app --host 0.0.0.0 --port "$BACKEND_PORT" >"$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" >"$BACKEND_PID_FILE"
print_info "后端 PID: $BACKEND_PID"
print_success "后端已启动（日志: $PROJECT_ROOT/backend.log）"

print_info "等待后端就绪..."
sleep 3
if ! ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    print_error "后端启动失败，日志:"
    cat "$PROJECT_ROOT/backend.log"
    exit 1
fi
if grep -qiE 'address already in use|error while attempting to bind' "$PROJECT_ROOT/backend.log" 2>/dev/null; then
    print_error "后端未能绑定端口 ${BACKEND_PORT}，日志摘录:"
    tail -40 "$PROJECT_ROOT/backend.log"
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "$BACKEND_PID_FILE"
    exit 1
fi
print_success "后端进程正常"

FRONTEND_PID=""
FRONTEND_PID_FILE="/tmp/mechanical_ai_frontend.pid"
print_header "启动前端静态服务"
print_info "端口: $FRONTEND_PORT"
cd "$FRONTEND_DIR"
nohup python3 -m http.server "$FRONTEND_PORT" >"$FRONTEND_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >"$FRONTEND_PID_FILE"
print_info "前端 PID: $FRONTEND_PID"
sleep 2
if ps -p "$FRONTEND_PID" >/dev/null 2>&1; then
    print_success "前端已启动（日志: $FRONTEND_DIR/frontend.log）"
else
    print_error "前端启动失败，frontend.log:"
    [[ -f "$FRONTEND_DIR/frontend.log" ]] && cat "$FRONTEND_DIR/frontend.log" || print_info "(无日志文件)"
    FRONTEND_PID=""
    rm -f "$FRONTEND_PID_FILE" 2>/dev/null || true
fi

print_header "启动完成"
echo -e "${YELLOW}本机访问提示 IP: $LOCAL_IP${NC}\n"
echo -e "${BLUE}后端${NC} http://$LOCAL_IP:$BACKEND_PORT/docs"
if [[ -n "$FRONTEND_PID" ]]; then
    echo -e "${BLUE}前端${NC} http://$LOCAL_IP:$FRONTEND_PORT/Unified%20Application%20Hub.html"
fi
echo -e "\n${YELLOW}停止${NC}: bash \"$PROJECT_ROOT/stop.sh\""
echo -e "${YELLOW}重启${NC}: bash \"$PROJECT_ROOT/restart.sh\"\n"

print_info "前台监控中… 按 Ctrl+C 将停止前后端"

cleanup() {
    echo -e "\n${YELLOW}正在关闭…${NC}"
    kill "$BACKEND_PID" 2>/dev/null || true
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
    rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"
    echo -e "${GREEN}已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

while true; do
    if ! ps -p "$BACKEND_PID" >/dev/null 2>&1; then
        print_error "后端已退出"
        exit 1
    fi
    if [[ -n "$FRONTEND_PID" ]] && ! ps -p "$FRONTEND_PID" >/dev/null 2>&1; then
        print_error "前端已退出"
        exit 1
    fi
    sleep 5
done
