#!/bin/bash

# --- 颜色定义 ---
BLUE='\033[0;34m'
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' 

# --- 辅助函数：打印带样式的步骤 ---
print_step() {
    printf "${BLUE}${BOLD}[STEP]${NC} %-40s" "$1"
}

print_ok() {
    printf "${GREEN}${BOLD}[ OK ]${NC}\n"
}

# --- 脚本开始 ---
clear
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}${BOLD}        明都巡店系统 - 后端自动部署工具          ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 0. 预先获取 sudo 权限，避免中途弹出密码破坏排版
sudo -v

# 1. 停止服务
print_step "正在停止 md-trace 服务..."
sudo systemctl stop md-trace >/dev/null 2>&1
print_ok

# 2. 暴力清除进程 (!!! 关键修改点：屏蔽 Killed 回显 !!!)
print_step "正在强杀僵尸进程 (Gunicorn/Uvicorn)..."
set +m  # 临时关闭作业控制，防止显示 "Killed"
(sudo pkill -9 -f gunicorn >/dev/null 2>&1)
(sudo pkill -9 -f uvicorn >/dev/null 2>&1)
set -m  # 恢复作业控制
sleep 1
print_ok

# 3. 清理缓存
print_step "正在清理 Python 编译缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + >/dev/null 2>&1
print_ok

# 4. 重新加载并启动
print_step "正在重新加载配置并启动服务..."
sudo systemctl daemon-reload
sudo systemctl start md-trace
print_ok

# 5. 状态检查
echo -e "${BLUE}--------------------------------------------------${NC}"
print_step "正在验证服务运行状态..."
sleep 2
STATUS=$(sudo systemctl is-active md-trace)

if [ "$STATUS" = "active" ]; then
    echo -e "${GREEN}${BOLD}ACTIVE${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    echo -e "${GREEN}${BOLD}✅ 部署完成！后端已成功切换至最新版本。${NC}"
    echo -e "${YELLOW}提示：3秒后将自动进入实时日志监控模式...${NC}"
    echo -e "${YELLOW}      (退出日志请按 Ctrl+C，不会再卡死了)${NC}"
    sleep 3
    
    # !!! 关键修改点：重置终端并直接输出日志，不使用分页器 !!!
    stty sane
    sudo journalctl -u md-trace -f --no-pager
else
    echo -e "${RED}${BOLD}FAILED${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    echo -e "${RED}❌ 错误：服务启动失败，请检查 main.py 是否有语法错误。${NC}"
    echo -e "${YELLOW}运行此命令查看详情: sudo journalctl -u md-trace -n 50${NC}"
fi
