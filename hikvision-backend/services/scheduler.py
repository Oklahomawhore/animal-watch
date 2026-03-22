#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器 (Scheduler)

功能：
1. 每小时运行一次小时聚合器
2. 每天凌晨运行日报生成器
3. 支持手动触发任务
4. 任务执行日志记录

技术栈：
- APScheduler: 定时任务调度
- asyncio: 异步任务执行
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 导入算法 Pipeline
from algorithm_pipeline import (
    run_hourly_aggregation,
    run_daily_report_generation
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, app=None):
        """
        初始化调度器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.running = False
        
        # 任务执行日志
        self.job_logs: Dict[str, list] = {
            'hourly_aggregation': [],
            'daily_report': []
        }
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("⚠️ 调度器已在运行")
            return
        
        self.scheduler = AsyncIOScheduler()
        
        # 添加定时任务
        self._add_jobs()
        
        # 启动调度器
        self.scheduler.start()
        self.running = True
        
        logger.info("🚀 定时任务调度器已启动")
        logger.info("📅 任务计划:")
        logger.info("   - 小时聚合: 每小时第5分钟运行")
        logger.info("   - 日报生成: 每天凌晨1:00运行")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
        
        self.running = False
        logger.info("🛑 定时任务调度器已停止")
    
    def _add_jobs(self):
        """添加定时任务"""
        # 小时聚合任务 - 每小时第5分钟运行
        self.scheduler.add_job(
            self._run_hourly_aggregation,
            trigger=CronTrigger(minute=5),  # 每小时第5分钟
            id='hourly_aggregation',
            name='小时数据聚合',
            replace_existing=True
        )
        
        # 日报生成任务 - 每天凌晨1:00运行
        self.scheduler.add_job(
            self._run_daily_report,
            trigger=CronTrigger(hour=1, minute=0),  # 每天凌晨1:00
            id='daily_report',
            name='日报生成',
            replace_existing=True
        )
    
    async def _run_hourly_aggregation(self):
        """运行小时聚合任务"""
        start_time = datetime.utcnow()
        logger.info(f"🕐 [{start_time}] 开始执行小时聚合任务")
        
        try:
            if self.app:
                await run_hourly_aggregation(self.app)
            
            self._log_job('hourly_aggregation', 'success', start_time)
            logger.info(f"✅ 小时聚合任务完成")
            
        except Exception as e:
            self._log_job('hourly_aggregation', 'failed', start_time, str(e))
            logger.error(f"❌ 小时聚合任务失败: {e}")
    
    async def _run_daily_report(self):
        """运行日报生成任务"""
        start_time = datetime.utcnow()
        logger.info(f"📊 [{start_time}] 开始执行日报生成任务")
        
        try:
            if self.app:
                await run_daily_report_generation(self.app)
            
            self._log_job('daily_report', 'success', start_time)
            logger.info(f"✅ 日报生成任务完成")
            
        except Exception as e:
            self._log_job('daily_report', 'failed', start_time, str(e))
            logger.error(f"❌ 日报生成任务失败: {e}")
    
    def _log_job(self, job_id: str, status: str, start_time: datetime, error: str = None):
        """记录任务执行日志"""
        log_entry = {
            'start_time': start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'status': status,
            'error': error
        }
        
        self.job_logs[job_id].append(log_entry)
        
        # 只保留最近100条日志
        if len(self.job_logs[job_id]) > 100:
            self.job_logs[job_id] = self.job_logs[job_id][-100:]
    
    def get_job_logs(self, job_id: str = None, limit: int = 10) -> Dict:
        """获取任务执行日志"""
        if job_id:
            return {
                'job_id': job_id,
                'logs': self.job_logs.get(job_id, [])[-limit:]
            }
        
        return {
            job_id: logs[-limit:]
            for job_id, logs in self.job_logs.items()
        }
    
    def get_scheduled_jobs(self) -> list:
        """获取已计划的任务列表"""
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jobs


# ==================== 服务管理 ====================

_scheduler: Optional[TaskScheduler] = None


def get_scheduler(app=None) -> TaskScheduler:
    """获取调度器实例（单例）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler(app)
    return _scheduler


def start_scheduler(app):
    """启动调度器"""
    scheduler = get_scheduler(app)
    scheduler.start()
    return scheduler


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


# ==================== 手动触发接口 ====================

async def trigger_hourly_aggregation(app):
    """手动触发小时聚合"""
    scheduler = get_scheduler(app)
    await scheduler._run_hourly_aggregation()


async def trigger_daily_report(app):
    """手动触发日报生成"""
    scheduler = get_scheduler(app)
    await scheduler._run_daily_report()
