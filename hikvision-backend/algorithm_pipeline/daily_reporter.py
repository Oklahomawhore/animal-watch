#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日报生成器 (Daily Reporter)

功能：
1. 每天凌晨生成前一天的日报
2. 聚合24小时统计数据
3. 计算活动评分、进食状态、饮水状态
4. 生成7天趋势数据
5. 整合诊疗记录和告警信息

技术栈：
- asyncio: 异步处理
- SQLAlchemy: 数据库操作
- APScheduler: 定时任务调度
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from collections import defaultdict

# 导入模型
from models_algorithm import (
    EventHourlyStats, DailyReport, MedicalRecordV2, CareRecord,
    HealthStatus, ActivityLevel, EatingStatus, DrinkingStatus
)
from models_v2 import db, Enclosure

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyReporter:
    """日报生成器"""
    
    def __init__(self, app=None):
        """
        初始化日报生成器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.running = False
        
        # 统计信息
        self.stats = {
            'total_runs': 0,
            'total_reports_generated': 0,
            'errors': 0,
            'last_run': None
        }
    
    async def generate_yesterday_reports(self, client_id: int = None, enclosure_id: int = None):
        """
        生成昨天的日报
        
        Args:
            client_id: 可选，指定租户
            enclosure_id: 可选，指定圈舍
        """
        yesterday = date.today() - timedelta(days=1)
        await self.generate_daily_reports(yesterday, client_id, enclosure_id)
    
    async def generate_daily_reports(self, report_date: date, client_id: int = None, enclosure_id: int = None):
        """
        生成指定日期的日报
        
        Args:
            report_date: 报告日期
            client_id: 可选，指定租户
            enclosure_id: 可选，指定圈舍
        """
        if not self.app:
            logger.error("❌ 未提供Flask应用实例")
            return
        
        logger.info(f"📊 开始生成 {report_date} 的日报")
        
        with self.app.app_context():
            try:
                # 获取需要生成日报的动物列表
                animals = self._get_animals(client_id, enclosure_id)
                
                if not animals:
                    logger.info(f"ℹ️ 没有找到需要生成日报的动物")
                    return
                
                logger.info(f"🐾 找到 {len(animals)} 只动物需要生成日报")
                
                # 为每只动物生成日报
                for animal in animals:
                    try:
                        await self._generate_animal_report(animal, report_date)
                        self.stats['total_reports_generated'] += 1
                    except Exception as e:
                        logger.error(f"❌ 生成动物 {animal['animal_id']} 日报失败: {e}")
                        self.stats['errors'] += 1
                
                self.stats['total_runs'] += 1
                self.stats['last_run'] = datetime.utcnow()
                
                logger.info(f"✅ 日报生成完成，共生成 {self.stats['total_reports_generated']} 份报告")
                
            except Exception as e:
                logger.error(f"❌ 日报生成失败: {e}")
                self.stats['errors'] += 1
                raise
    
    def _get_animals(self, client_id: int = None, enclosure_id: int = None) -> List[Dict]:
        """
        获取需要生成日报的动物列表
        
        Returns:
            动物信息列表
        """
        # 从圈舍表中获取所有有动物的圈舍
        query = Enclosure.query.filter(Enclosure.animal_count > 0)
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        if enclosure_id:
            query = query.filter_by(id=enclosure_id)
        
        enclosures = query.all()
        
        animals = []
        for enclosure in enclosures:
            if enclosure.animal_tags:
                for tag_info in enclosure.animal_tags:
                    animals.append({
                        'client_id': enclosure.client_id,
                        'enclosure_id': enclosure.id,
                        'animal_id': tag_info.get('tag'),
                        'animal_name': tag_info.get('name'),
                        'gender': tag_info.get('gender'),
                        'age': self._calculate_age(tag_info.get('birth_date')),
                        'ear_tag': tag_info.get('tag')
                    })
        
        return animals
    
    def _calculate_age(self, birth_date_str: str) -> str:
        """计算年龄"""
        if not birth_date_str:
            return '未知'
        
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            today = date.today()
            age_years = today.year - birth_date.year
            
            if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                age_years -= 1
            
            if age_years < 1:
                age_months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
                return f"{age_months}个月"
            else:
                return f"{age_years}岁"
        except:
            return '未知'
    
    async def _generate_animal_report(self, animal: Dict, report_date: date):
        """
        为单只动物生成日报
        
        Args:
            animal: 动物信息
            report_date: 报告日期
        """
        animal_id = animal['animal_id']
        enclosure_id = animal['enclosure_id']
        client_id = animal['client_id']
        
        logger.debug(f"📝 生成 {animal_id} 的日报")
        
        # 1. 获取24小时统计数据
        hourly_stats = EventHourlyStats.query.filter_by(
            enclosure_id=enclosure_id,
            animal_id=animal_id,
            stat_date=report_date
        ).all()
        
        # 2. 计算日汇总
        daily_summary = self._aggregate_daily(hourly_stats)
        
        # 3. 获取7天趋势
        activity_trend = self._get_7day_trend(animal_id, report_date)
        
        # 4. 获取诊疗记录
        medical = self._get_medical_summary(animal_id)
        
        # 5. 获取告警摘要
        alerts_summary = self._get_alerts_summary(hourly_stats)
        
        # 6. 计算健康状态
        health_status = self._calculate_health_status(daily_summary, medical)
        
        # 7. 构建日报
        report = self._build_report(
            animal=animal,
            report_date=report_date,
            daily_summary=daily_summary,
            activity_trend=activity_trend,
            medical=medical,
            alerts_summary=alerts_summary,
            health_status=health_status
        )
        
        # 8. 保存日报
        self._save_report(report)
    
    def _aggregate_daily(self, hourly_stats: List[EventHourlyStats]) -> Dict:
        """
        聚合日统计数据
        
        Args:
            hourly_stats: 小时统计列表
            
        Returns:
            日汇总数据
        """
        if not hourly_stats:
            return {
                'activity_score': 0,
                'activity_level': ActivityLevel.LOW.value,
                'total_movement_duration': 0,
                'total_eating_duration': 0,
                'total_drinking_duration': 0,
                'eating_status': EatingStatus.NOT_EATING.value,
                'water_consumption': 0,
                'drinking_status': DrinkingStatus.LOW.value,
                'alert_count': 0
            }
        
        # 汇总指标
        total_movement_duration = sum(s.movement_duration for s in hourly_stats)
        total_eating_duration = sum(s.eating_duration for s in hourly_stats)
        total_drinking_duration = sum(s.drinking_duration for s in hourly_stats)
        total_resting_duration = sum(s.resting_duration for s in hourly_stats)
        total_alert_count = sum(s.alert_count for s in hourly_stats)
        
        # 计算平均活动评分
        activity_scores = [s.activity_score for s in hourly_stats if s.activity_score is not None]
        avg_activity_score = sum(activity_scores) / len(activity_scores) if activity_scores else 0
        
        # 计算活动水平
        activity_level = self._determine_activity_level(avg_activity_score)
        
        # 计算进食状态
        eating_status = self._determine_eating_status(total_eating_duration)
        
        # 计算饮水状态
        water_consumption = sum(s.water_consumption_liters or 0 for s in hourly_stats)
        drinking_status = self._determine_drinking_status(water_consumption)
        
        return {
            'activity_score': round(avg_activity_score),
            'activity_level': activity_level.value,
            'total_movement_duration': total_movement_duration,
            'total_eating_duration': total_eating_duration,
            'total_drinking_duration': total_drinking_duration,
            'total_resting_duration': total_resting_duration,
            'eating_status': eating_status.value,
            'water_consumption': round(water_consumption, 2),
            'drinking_status': drinking_status.value,
            'alert_count': total_alert_count
        }
    
    def _determine_activity_level(self, score: float) -> ActivityLevel:
        """根据评分确定活动水平"""
        if score < 30:
            return ActivityLevel.LOW
        elif score > 80:
            return ActivityLevel.HIGH
        else:
            return ActivityLevel.NORMAL
    
    def _determine_eating_status(self, duration_seconds: int) -> EatingStatus:
        """根据进食时长确定进食状态"""
        # 假设正常进食时长为 30-90 分钟
        duration_minutes = duration_seconds / 60
        
        if duration_minutes < 10:
            return EatingStatus.NOT_EATING
        elif duration_minutes < 20:
            return EatingStatus.SLOW
        elif duration_minutes > 120:
            return EatingStatus.FAST
        else:
            return EatingStatus.NORMAL
    
    def _determine_drinking_status(self, liters: float) -> DrinkingStatus:
        """根据饮水量确定饮水状态"""
        # 假设林麝正常日饮水量为 2-5 升
        if liters < 1.5:
            return DrinkingStatus.LOW
        elif liters > 6:
            return DrinkingStatus.HIGH
        else:
            return DrinkingStatus.NORMAL
    
    def _get_7day_trend(self, animal_id: str, end_date: date) -> List[int]:
        """
        获取7天活动评分趋势
        
        Args:
            animal_id: 动物ID
            end_date: 结束日期
            
        Returns:
            7天活动评分列表
        """
        trend = []
        
        for i in range(6, -1, -1):
            check_date = end_date - timedelta(days=i)
            
            # 查询该日的小时统计
            hourly_stats = EventHourlyStats.query.filter_by(
                animal_id=animal_id,
                stat_date=check_date
            ).all()
            
            if hourly_stats:
                scores = [s.activity_score for s in hourly_stats if s.activity_score is not None]
                avg_score = round(sum(scores) / len(scores)) if scores else 0
                trend.append(avg_score)
            else:
                # 如果没有数据，使用日报表中的数据
                report = DailyReport.query.filter_by(
                    animal_id=animal_id,
                    report_date=check_date
                ).first()
                
                if report:
                    trend.append(report.activity_score)
                else:
                    trend.append(0)
        
        return trend
    
    def _get_medical_summary(self, animal_id: str) -> Optional[Dict]:
        """
        获取诊疗摘要
        
        Args:
            animal_id: 动物ID
            
        Returns:
            诊疗摘要或None
        """
        medical = MedicalRecordV2.query.filter_by(
            animal_id=animal_id
        ).order_by(MedicalRecordV2.created_at.desc()).first()
        
        if not medical:
            return None
        
        return {
            'diagnosis': medical.diagnosis,
            'status': medical.status.value if medical.status else None,
            'treatment_day': medical.treatment_day,
            'medications': medical.medications,
            'veterinarian': medical.veterinarian
        }
    
    def _get_alerts_summary(self, hourly_stats: List[EventHourlyStats]) -> List[Dict]:
        """
        获取告警摘要
        
        Args:
            hourly_stats: 小时统计列表
            
        Returns:
            告警摘要列表
        """
        alerts = []
        
        for stat in hourly_stats:
            if stat.alert_count > 0 and stat.alert_types:
                for alert_type in stat.alert_types:
                    alerts.append({
                        'type': alert_type,
                        'message': self._get_alert_message(alert_type),
                        'level': 'warning',
                        'time': f"{stat.hour:02d}:00"
                    })
        
        return alerts[:5]  # 最多返回5条告警
    
    def _get_alert_message(self, alert_type: str) -> str:
        """获取告警消息"""
        messages = {
            'low_activity': '活动量异常偏低',
            'no_animal': '未检测到动物',
            'abnormal_behavior': '行为异常',
            'health_risk': '健康风险'
        }
        return messages.get(alert_type, '未知告警')
    
    def _calculate_health_status(self, daily_summary: Dict, medical: Optional[Dict]) -> int:
        """
        计算健康状态
        
        Returns:
            0: 绿(正常), 1: 黄(关注), 2: 红(告警)
        """
        # 如果有未解决的诊疗记录，标记为黄
        if medical and medical.get('status') == 'ongoing':
            return HealthStatus.YELLOW.value
        
        # 如果有告警，标记为黄
        if daily_summary.get('alert_count', 0) > 0:
            return HealthStatus.YELLOW.value
        
        # 活动评分过低，标记为黄
        if daily_summary.get('activity_score', 100) < 20:
            return HealthStatus.YELLOW.value
        
        return HealthStatus.GREEN.value
    
    def _build_report(self, animal: Dict, report_date: date, daily_summary: Dict,
                     activity_trend: List[int], medical: Optional[Dict],
                     alerts_summary: List[Dict], health_status: int) -> Dict:
        """构建日报数据"""
        return {
            'client_id': animal['client_id'],
            'enclosure_id': animal['enclosure_id'],
            'animal_id': animal['animal_id'],
            'report_date': report_date,
            'ear_tag': animal['ear_tag'],
            'gender': '雌性' if animal.get('gender') == 'female' else '雄性' if animal.get('gender') == 'male' else animal.get('gender'),
            'age': animal.get('age'),
            'health_status': health_status,
            'activity_score': daily_summary['activity_score'],
            'activity_level': daily_summary['activity_level'],
            'activity_trend': activity_trend,
            'feed_main_remain_percent': 35,  # TODO: 从食槽摄像头获取
            'feed_aux_remain_percent': 72,   # TODO: 从食槽摄像头获取
            'eating_status': daily_summary['eating_status'],
            'water_consumption_liters': daily_summary['water_consumption'],
            'drinking_status': daily_summary['drinking_status'],
            'alerts_summary': alerts_summary
        }
    
    def _save_report(self, report_data: Dict):
        """保存日报到数据库"""
        # 检查是否已存在
        existing = DailyReport.query.filter_by(
            animal_id=report_data['animal_id'],
            report_date=report_data['report_date']
        ).first()
        
        if existing:
            # 更新现有记录
            for key, value in report_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            logger.debug(f"📝 更新日报: {report_data['animal_id']} {report_data['report_date']}")
        else:
            # 创建新记录
            new_report = DailyReport(**report_data)
            db.session.add(new_report)
            logger.debug(f"📝 创建日报: {report_data['animal_id']} {report_data['report_date']}")
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 保存日报失败: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """获取生成器统计信息"""
        return {
            'total_runs': self.stats['total_runs'],
            'total_reports_generated': self.stats['total_reports_generated'],
            'errors': self.stats['errors'],
            'last_run': self.stats['last_run'].isoformat() if self.stats['last_run'] else None
        }


# ==================== 服务管理 ====================

_reporter: Optional[DailyReporter] = None


def get_reporter(app=None) -> DailyReporter:
    """获取日报生成器实例（单例）"""
    global _reporter
    if _reporter is None:
        _reporter = DailyReporter(app)
    return _reporter


async def run_daily_report_generation(app, client_id: int = None):
    """
    运行日报生成（供定时任务调用）
    
    Args:
        app: Flask应用实例
        client_id: 可选，指定租户
    """
    reporter = get_reporter(app)
    await reporter.generate_yesterday_reports(client_id)


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
    
    reporter = DailyReporter(app)
    
    async def test():
        await reporter.generate_yesterday_reports()
        print(reporter.get_stats())
    
    asyncio.run(test())
