#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小时聚合器 (Hourly Aggregator)

功能：
1. 每小时运行一次，聚合前一小时的事件数据
2. 计算活动、进食、饮水、休息等统计指标
3. 生成小时级统计记录
4. 支持手动触发历史数据聚合

技术栈：
- asyncio: 异步处理
- SQLAlchemy: 数据库操作
- APScheduler: 定时任务调度
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 导入模型
from models_algorithm import Event, EventHourlyStats, EventType
from models_v2 import db

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HourlyAggregator:
    """小时级事件聚合器"""
    
    def __init__(self, app=None):
        """
        初始化聚合器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.running = False
        
        # 统计信息
        self.stats = {
            'total_runs': 0,
            'total_hours_processed': 0,
            'total_records_created': 0,
            'errors': 0,
            'last_run': None
        }
    
    async def aggregate_last_hour(self):
        """聚合上一小时的数据"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        stat_date = last_hour.date()
        hour = last_hour.hour
        
        logger.info(f"🕐 开始聚合 {stat_date} {hour}:00 的数据")
        
        await self.aggregate_hour(stat_date, hour)
    
    async def aggregate_hour(self, stat_date: date, hour: int, client_id: int = None, enclosure_id: int = None):
        """
        聚合指定小时的数据
        
        Args:
            stat_date: 统计日期
            hour: 小时 (0-23)
            client_id: 可选，指定租户
            enclosure_id: 可选，指定圈舍
        """
        if not self.app:
            logger.error("❌ 未提供Flask应用实例")
            return
        
        # 计算时间范围
        start_time = datetime.combine(stat_date, datetime.min.time()) + timedelta(hours=hour)
        end_time = start_time + timedelta(hours=1)
        
        with self.app.app_context():
            try:
                # 查询该小时的所有事件
                query = Event.query.filter(
                    Event.event_time >= start_time,
                    Event.event_time < end_time
                )
                
                if client_id:
                    query = query.filter_by(client_id=client_id)
                if enclosure_id:
                    query = query.filter_by(enclosure_id=enclosure_id)
                
                events = query.all()
                
                if not events:
                    logger.info(f"ℹ️ {stat_date} {hour}:00 无事件数据")
                    return
                
                logger.info(f"📊 找到 {len(events)} 个事件")
                
                # 按圈舍和动物分组统计
                grouped_stats = self._group_and_calculate(events, stat_date, hour)
                
                # 保存统计结果
                self._save_stats(grouped_stats)
                
                self.stats['total_hours_processed'] += 1
                self.stats['total_records_created'] += len(grouped_stats)
                
                logger.info(f"✅ 聚合完成，生成 {len(grouped_stats)} 条统计记录")
                
            except Exception as e:
                logger.error(f"❌ 聚合失败: {e}")
                self.stats['errors'] += 1
                raise
    
    def _group_and_calculate(self, events: List[Event], stat_date: date, hour: int) -> List[Dict]:
        """
        分组并计算统计指标
        
        Args:
            events: 事件列表
            stat_date: 统计日期
            hour: 小时
            
        Returns:
            统计结果列表
        """
        # 按 (client_id, enclosure_id, animal_id) 分组
        groups = defaultdict(list)
        
        for event in events:
            key = (event.client_id, event.enclosure_id, event.animal_id)
            groups[key].append(event)
        
        results = []
        
        for (client_id, enclosure_id, animal_id), group_events in groups.items():
            stats = self._calculate_metrics(group_events)
            stats.update({
                'client_id': client_id,
                'enclosure_id': enclosure_id,
                'animal_id': animal_id,
                'stat_date': stat_date,
                'hour': hour
            })
            results.append(stats)
        
        return results
    
    def _calculate_metrics(self, events: List[Event]) -> Dict:
        """
        计算统计指标
        
        Args:
            events: 同一组的事件列表
            
        Returns:
            统计指标字典
        """
        # 初始化统计
        stats = {
            'movement_count': 0,
            'movement_duration': 0,
            'avg_movement_score': None,
            'eating_count': 0,
            'eating_duration': 0,
            'feed_consumption_percent': None,
            'drinking_count': 0,
            'drinking_duration': 0,
            'water_consumption_liters': None,
            'resting_duration': 0,
            'alert_count': 0,
            'alert_types': [],
            'activity_score': None
        }
        
        movement_scores = []
        alert_types = set()
        
        # 遍历事件计算指标
        for event in events:
            event_type = event.event_type
            
            if event_type == EventType.MOVEMENT:
                stats['movement_count'] += 1
                # 假设每个移动事件持续3秒（实际应根据算法输出）
                stats['movement_duration'] += 3
                
                # 收集运动强度分数
                if event.metadata and 'movement_score' in event.metadata:
                    movement_scores.append(event.metadata['movement_score'])
            
            elif event_type == EventType.EATING:
                stats['eating_count'] += 1
                # 假设每次进食持续5秒
                stats['eating_duration'] += 5
                
                # 估算饲料消耗
                if event.metadata and 'feed_consumption' in event.metadata:
                    stats['feed_consumption_percent'] = event.metadata['feed_consumption']
            
            elif event_type == EventType.DRINKING:
                stats['drinking_count'] += 1
                # 假设每次饮水持续2秒
                stats['drinking_duration'] += 2
                
                # 估算饮水量
                if event.metadata and 'water_consumption' in event.metadata:
                    stats['water_consumption_liters'] = event.metadata['water_consumption']
            
            elif event_type == EventType.RESTING:
                # 假设每次休息持续10秒
                stats['resting_duration'] += 10
            
            elif event_type == EventType.ALERT:
                stats['alert_count'] += 1
                alert_types.add(event.metadata.get('alert_type', 'unknown') if event.metadata else 'unknown')
        
        # 计算平均值
        if movement_scores:
            stats['avg_movement_score'] = sum(movement_scores) / len(movement_scores)
        
        if alert_types:
            stats['alert_types'] = list(alert_types)
        
        # 计算活动评分（0-100）
        stats['activity_score'] = self._calculate_activity_score(stats)
        
        return stats
    
    def _calculate_activity_score(self, stats: Dict) -> int:
        """
        计算活动评分
        
        评分规则：
        - 基础分：50分
        - 移动时长加分：每30秒加5分，最高25分
        - 进食正常加分：有进食记录加10分
        - 饮水正常加分：有饮水记录加10分
        - 告警扣分：每个告警扣10分
        
        Args:
            stats: 统计指标
            
        Returns:
            活动评分 (0-100)
        """
        score = 50  # 基础分
        
        # 移动加分
        movement_duration = stats.get('movement_duration', 0)
        score += min(movement_duration // 30 * 5, 25)
        
        # 进食加分
        if stats.get('eating_count', 0) > 0:
            score += 10
        
        # 饮水加分
        if stats.get('drinking_count', 0) > 0:
            score += 10
        
        # 告警扣分
        alert_count = stats.get('alert_count', 0)
        score -= alert_count * 10
        
        # 限制在0-100范围内
        return max(0, min(100, score))
    
    def _save_stats(self, stats_list: List[Dict]):
        """
        保存统计结果到数据库
        
        Args:
            stats_list: 统计结果列表
        """
        for stats in stats_list:
            # 检查是否已存在
            existing = EventHourlyStats.query.filter_by(
                enclosure_id=stats['enclosure_id'],
                animal_id=stats['animal_id'],
                stat_date=stats['stat_date'],
                hour=stats['hour']
            ).first()
            
            if existing:
                # 更新现有记录
                for key, value in stats.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # 创建新记录
                new_stats = EventHourlyStats(**stats)
                db.session.add(new_stats)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 保存统计记录失败: {e}")
            raise
    
    async def aggregate_date_range(self, start_date: date, end_date: date, client_id: int = None):
        """
        聚合日期范围内的所有小时数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            client_id: 可选，指定租户
        """
        logger.info(f"📅 开始聚合 {start_date} 至 {end_date} 的数据")
        
        current_date = start_date
        total_hours = 0
        
        while current_date <= end_date:
            for hour in range(24):
                try:
                    await self.aggregate_hour(current_date, hour, client_id)
                    total_hours += 1
                    
                    # 每处理10小时暂停一下，避免数据库压力过大
                    if total_hours % 10 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"❌ 聚合 {current_date} {hour}:00 失败: {e}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"✅ 日期范围聚合完成，共处理 {total_hours} 小时")
    
    def get_stats(self) -> Dict:
        """获取聚合器统计信息"""
        return {
            'total_runs': self.stats['total_runs'],
            'total_hours_processed': self.stats['total_hours_processed'],
            'total_records_created': self.stats['total_records_created'],
            'errors': self.stats['errors'],
            'last_run': self.stats['last_run'].isoformat() if self.stats['last_run'] else None
        }


# ==================== 服务管理 ====================

_aggregator: Optional[HourlyAggregator] = None


def get_aggregator(app=None) -> HourlyAggregator:
    """获取聚合器实例（单例）"""
    global _aggregator
    if _aggregator is None:
        _aggregator = HourlyAggregator(app)
    return _aggregator


async def run_hourly_aggregation(app, client_id: int = None):
    """
    运行小时聚合（供定时任务调用）
    
    Args:
        app: Flask应用实例
        client_id: 可选，指定租户
    """
    aggregator = get_aggregator(app)
    await aggregator.aggregate_last_hour()


# ==================== 测试入口 ====================

if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    # 创建测试用的Flask应用
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@localhost/animal_watch'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    aggregator = HourlyAggregator(app)
    
    # 测试聚合昨天一整天
    yesterday = date.today() - timedelta(days=1)
    
    async def test():
        await aggregator.aggregate_date_range(yesterday, yesterday)
        print(aggregator.get_stats())
    
    asyncio.run(test())
