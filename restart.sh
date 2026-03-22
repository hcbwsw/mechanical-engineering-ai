#!/usr/bin/env bash

################################################################################
# 机械工程 AI 系统 — 先 stop 再 start（均在项目根执行）
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/stop.sh"
sleep 2
bash "$SCRIPT_DIR/start.sh"
