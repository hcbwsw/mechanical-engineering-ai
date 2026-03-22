#!/usr/bin/env bash

################################################################################
# 机械工程 AI 系统 — 停止前后端进程
# 在项目根目录执行：bash stop.sh
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

print_header "停止机械工程 AI 系统"

BACKEND_PID_FILE="/tmp/mechanical_ai_backend.pid"
FRONTEND_PID_FILE="/tmp/mechanical_ai_frontend.pid"

if [[ -f "$BACKEND_PID_FILE" ]]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
        print_info "停止后端 (PID: $BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
            print_info "强制结束后端..."
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
        print_success "后端已停止"
    else
        print_info "后端未在运行"
    fi
    rm -f "$BACKEND_PID_FILE"
else
    print_info "无后端 PID 文件，尝试匹配 uvicorn..."
    FOUND_PID=$(pgrep -f "uvicorn main_app:app" | head -1 || true)
    if [[ -n "$FOUND_PID" ]]; then
        print_info "找到进程 PID: $FOUND_PID，正在停止..."
        kill -TERM "$FOUND_PID" 2>/dev/null || true
        sleep 2
        ps -p "$FOUND_PID" >/dev/null 2>&1 && kill -9 "$FOUND_PID" 2>/dev/null || true
        print_success "后端已停止"
    else
        print_info "未找到后端进程"
    fi
fi

if [[ -f "$FRONTEND_PID_FILE" ]]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if ps -p "$FRONTEND_PID" >/dev/null 2>&1; then
        print_info "停止前端 (PID: $FRONTEND_PID)..."
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
        sleep 1
        if ps -p "$FRONTEND_PID" >/dev/null 2>&1; then
            kill -9 "$FRONTEND_PID" 2>/dev/null || true
        fi
        print_success "前端已停止"
    else
        print_info "前端未在运行"
    fi
    rm -f "$FRONTEND_PID_FILE"
else
    print_info "无前端 PID 文件；若曾用默认方式启动，可尝试匹配 http.server"
    FOUND_PID=$(pgrep -f "python3 -m http.server" | head -1 || true)
    if [[ -n "$FOUND_PID" ]]; then
        print_info "找到 PID: $FOUND_PID（请确认是本项目前端）..."
        kill -TERM "$FOUND_PID" 2>/dev/null || true
        sleep 1
        ps -p "$FOUND_PID" >/dev/null 2>&1 && kill -9 "$FOUND_PID" 2>/dev/null || true
        print_success "已尝试停止"
    else
        print_info "未找到前端进程"
    fi
fi

print_header "停止流程结束"
