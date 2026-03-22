#!/bin/bash
# Token 刷新定时任务安装脚本

# 添加定时任务：每天凌晨 3 点执行 Token 刷新
# 替换为你的项目路径
PROJECT_PATH="/path/to/lin-she-health-monitor"

# 检查是否已经存在定时任务
CRON_JOB="0 3 * * * cd $PROJECT_PATH/hikvision-backend && python3 services/token_refresher.py >> /var/log/hikvision_token_refresh.log 2>&1"

# 查看当前定时任务
echo "当前定时任务:"
crontab -l 2>/dev/null || echo "无定时任务"

# 添加新的定时任务
echo ""
echo "将添加以下定时任务:"
echo "$CRON_JOB"

# 追加到 crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "定时任务已添加！"

# 立即运行一次测试
echo ""
echo "是否立即运行一次测试? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    cd "$PROJECT_PATH/hikvision-backend"
    python3 services/token_refresher.py
fi
