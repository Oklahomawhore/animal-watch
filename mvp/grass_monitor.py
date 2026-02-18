#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
林麝食量监控系统 MVP
===================
基于 OpenCV 的食槽草量检测原型

功能:
1. 加载空槽/满槽基准图
2. 分析当前食槽图像
3. 计算草量覆盖率
4. 生成趋势报告

作者: Animal Watch Team
版本: 1.0.0
"""

import cv2
import numpy as np
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TroughConfig:
    """食槽配置"""
    trough_id: str           # 食槽ID
    name: str                # 名称
    roi: Tuple[int, int, int, int]  # (x, y, width, height) ROI区域
    empty_baseline: str      # 空槽基准图路径
    full_baseline: str       # 满槽基准图路径


@dataclass
class GrassCoverageResult:
    """草量覆盖分析结果"""
    trough_id: str
    timestamp: str
    coverage_ratio: float    # 0-100% 草量覆盖率
    green_ratio: float       # 绿色像素占比
    status: str              # empty/low/medium/high/full
    confidence: float        # 置信度
    
    def to_dict(self) -> dict:
        return asdict(self)


class GrassCoverageAnalyzer:
    """食槽草量覆盖率分析器"""
    
    def __init__(self, config: TroughConfig):
        self.config = config
        self.empty_img = None
        self.full_img = None
        self.empty_green_ratio = 0.0
        self.full_green_ratio = 0.0
        
        # HSV 绿色范围配置
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
        
        self._load_baselines()
    
    def _load_baselines(self):
        """加载基准图"""
        empty_path = Path(self.config.empty_baseline)
        full_path = Path(self.config.full_baseline)
        
        if empty_path.exists():
            self.empty_img = self._extract_roi(cv2.imread(str(empty_path)))
            self.empty_green_ratio = self._calc_green_ratio(self.empty_img)
            logger.info(f"[{self.config.trough_id}] 空槽基准图加载成功, 绿色占比: {self.empty_green_ratio:.2%}")
        else:
            logger.warning(f"[{self.config.trough_id}] 空槽基准图不存在: {empty_path}")
        
        if full_path.exists():
            self.full_img = self._extract_roi(cv2.imread(str(full_path)))
            self.full_green_ratio = self._calc_green_ratio(self.full_img)
            logger.info(f"[{self.config.trough_id}] 满槽基准图加载成功, 绿色占比: {self.full_green_ratio:.2%}")
        else:
            logger.warning(f"[{self.config.trough_id}] 满槽基准图不存在: {full_path}")
    
    def _extract_roi(self, image: np.ndarray) -> np.ndarray:
        """提取 ROI 区域"""
        if image is None:
            return None
        x, y, w, h = self.config.roi
        return image[y:y+h, x:x+w]
    
    def _calc_green_ratio(self, image: np.ndarray) -> float:
        """计算绿色像素占比"""
        if image is None:
            return 0.0
        
        # 转换到 HSV 色彩空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 创建绿色掩码
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # 计算绿色像素占比
        green_pixels = np.sum(mask > 0)
        total_pixels = mask.size
        
        return green_pixels / total_pixels if total_pixels > 0 else 0.0
    
    def analyze(self, image_path: str) -> GrassCoverageResult:
        """分析食槽图像"""
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法加载图像: {image_path}")
        
        # 提取 ROI
        roi = self._extract_roi(image)
        
        # 计算当前绿色占比
        current_green_ratio = self._calc_green_ratio(roi)
        
        # 计算覆盖率
        if self.full_green_ratio > self.empty_green_ratio:
            coverage = (current_green_ratio - self.empty_green_ratio) / \
                      (self.full_green_ratio - self.empty_green_ratio) * 100
        else:
            coverage = 50.0  # 默认中间值
        
        coverage = max(0, min(100, coverage))  # 限制在 0-100
        
        # 判断状态
        status = self._classify_status(coverage)
        
        # 计算置信度 (基于图像清晰度)
        confidence = self._calc_confidence(roi)
        
        return GrassCoverageResult(
            trough_id=self.config.trough_id,
            timestamp=datetime.now().isoformat(),
            coverage_ratio=round(coverage, 2),
            green_ratio=round(current_green_ratio * 100, 2),
            status=status,
            confidence=round(confidence, 2)
        )
    
    def _classify_status(self, coverage: float) -> str:
        """分类食槽状态"""
        if coverage < 10:
            return "empty"      # 空槽
        elif coverage < 30:
            return "low"        # 少量
        elif coverage < 60:
            return "medium"     # 中等
        elif coverage < 90:
            return "high"       # 较多
        else:
            return "full"       # 满槽
    
    def _calc_confidence(self, image: np.ndarray) -> float:
        """计算分析置信度"""
        if image is None:
            return 0.0
        
        # 使用拉普拉斯算子检测图像清晰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 归一化到 0-1
        confidence = min(1.0, laplacian_var / 500)
        return confidence
    
    def visualize(self, image_path: str, result: GrassCoverageResult, 
                  output_path: Optional[str] = None) -> np.ndarray:
        """可视化分析结果"""
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        x, y, w, h = self.config.roi
        
        # 绘制 ROI 框
        color = self._get_status_color(result.status)
        cv2.rectangle(image, (x, y), (x+w, y+h), color, 3)
        
        # 添加文字信息
        info_text = [
            f"Trough: {result.trough_id}",
            f"Coverage: {result.coverage_ratio:.1f}%",
            f"Status: {result.status}",
            f"Confidence: {result.confidence:.2f}"
        ]
        
        y_offset = y - 10
        for text in info_text:
            cv2.putText(image, text, (x, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_offset -= 25
        
        if output_path:
            cv2.imwrite(output_path, image)
            logger.info(f"可视化结果已保存: {output_path}")
        
        return image
    
    def _get_status_color(self, status: str) -> Tuple[int, int, int]:
        """获取状态对应的颜色 (BGR格式)"""
        colors = {
            "empty": (0, 0, 255),      # 红色
            "low": (0, 100, 255),      # 橙色
            "medium": (0, 255, 255),   # 黄色
            "high": (0, 255, 100),     # 浅绿
            "full": (0, 255, 0),       # 绿色
        }
        return colors.get(status, (128, 128, 128))


class FeedingMonitor:
    """喂食监控系统"""
    
    def __init__(self, config_file: str = "troughs.json"):
        self.config_file = config_file
        self.troughs: Dict[str, GrassCoverageAnalyzer] = {}
        self.history: Dict[str, List[GrassCoverageResult]] = {}
        
        self._load_config()
    
    def _load_config(self):
        """加载食槽配置"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_file}, 使用默认配置")
            self._create_default_config()
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        
        for cfg in configs:
            trough_config = TroughConfig(**cfg)
            self.troughs[trough_config.trough_id] = GrassCoverageAnalyzer(trough_config)
            self.history[trough_config.trough_id] = []
        
        logger.info(f"已加载 {len(self.troughs)} 个食槽配置")
    
    def _create_default_config(self):
        """创建默认配置"""
        default_configs = [
            {
                "trough_id": "trough_A01",
                "name": "A01号食槽",
                "roi": [100, 200, 300, 200],
                "empty_baseline": "baselines/empty_A01.jpg",
                "full_baseline": "baselines/full_A01.jpg"
            }
        ]
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_configs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"默认配置已创建: {self.config_file}")
    
    def analyze_trough(self, trough_id: str, image_path: str) -> GrassCoverageResult:
        """分析指定食槽"""
        if trough_id not in self.troughs:
            raise ValueError(f"未知的食槽ID: {trough_id}")
        
        analyzer = self.troughs[trough_id]
        result = analyzer.analyze(image_path)
        
        # 保存历史记录
        self.history[trough_id].append(result)
        
        return result
    
    def monitor_all(self, image_paths: Dict[str, str]) -> Dict[str, GrassCoverageResult]:
        """监控所有食槽"""
        results = {}
        for trough_id, image_path in image_paths.items():
            try:
                result = self.analyze_trough(trough_id, image_path)
                results[trough_id] = result
                logger.info(f"[{trough_id}] 分析完成: {result.coverage_ratio:.1f}% - {result.status}")
            except Exception as e:
                logger.error(f"[{trough_id}] 分析失败: {e}")
        
        return results
    
    def generate_report(self, trough_id: str, hours: int = 24) -> dict:
        """生成监控报告"""
        history = self.history.get(trough_id, [])
        
        if not history:
            return {"error": "无历史数据"}
        
        coverages = [h.coverage_ratio for h in history]
        
        report = {
            "trough_id": trough_id,
            "period_hours": hours,
            "total_records": len(history),
            "avg_coverage": round(np.mean(coverages), 2),
            "min_coverage": round(min(coverages), 2),
            "max_coverage": round(max(coverages), 2),
            "current_coverage": round(coverages[-1], 2),
            "status_changes": self._count_status_changes(history),
            "recommendation": self._generate_recommendation(coverages)
        }
        
        return report
    
    def _count_status_changes(self, history: List[GrassCoverageResult]) -> int:
        """统计状态变化次数"""
        if len(history) < 2:
            return 0
        
        changes = 0
        for i in range(1, len(history)):
            if history[i].status != history[i-1].status:
                changes += 1
        
        return changes
    
    def _generate_recommendation(self, coverages: List[float]) -> str:
        """生成饲喂建议"""
        current = coverages[-1]
        trend = coverages[-1] - np.mean(coverages[:-5] if len(coverages) > 5 else coverages[:-1])
        
        if current < 10:
            return "食槽已空，建议立即补充饲料"
        elif current < 30 and trend < -10:
            return "饲料消耗较快，建议增加投喂量"
        elif current > 80:
            return "饲料充足，无需补充"
        elif trend > 5:
            return "饲料消耗较慢，关注动物食欲"
        else:
            return "饲料量正常，继续观察"
    
    def plot_trend(self, trough_id: str, output_path: str = "trend.png"):
        """绘制趋势图"""
        history = self.history.get(trough_id, [])
        
        if len(history) < 2:
            logger.warning("历史数据不足，无法绘制趋势图")
            return
        
        times = [datetime.fromisoformat(h.timestamp) for h in history]
        coverages = [h.coverage_ratio for h in history]
        
        plt.figure(figsize=(12, 6))
        plt.plot(times, coverages, 'b-', linewidth=2, marker='o', markersize=4)
        plt.axhline(y=50, color='g', linestyle='--', label='50% 警戒线')
        plt.axhline(y=10, color='r', linestyle='--', label='10% 空槽线')
        
        plt.xlabel('时间')
        plt.ylabel('草量覆盖率 (%)')
        plt.title(f'{trough_id} 食槽草量变化趋势')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=150)
        logger.info(f"趋势图已保存: {output_path}")
        plt.close()


# ============ 演示模式 ============

def demo_mode():
    """演示模式 - 使用模拟数据"""
    print("="*60)
    print("林麝食量监控系统 MVP - 演示模式")
    print("="*60)
    
    # 创建演示目录
    Path("demo/baselines").mkdir(parents=True, exist_ok=True)
    Path("demo/images").mkdir(parents=True, exist_ok=True)
    Path("demo/output").mkdir(parents=True, exist_ok=True)
    
    # 生成模拟图像
    print("\n[1] 生成模拟基准图...")
    empty_img = generate_mock_trough_image("empty", (400, 300))
    full_img = generate_mock_trough_image("full", (400, 300))
    
    cv2.imwrite("demo/baselines/empty_A01.jpg", empty_img)
    cv2.imwrite("demo/baselines/full_A01.jpg", full_img)
    print("   ✓ 基准图已生成")
    
    # 初始化监控器
    print("\n[2] 初始化监控系统...")
    monitor = FeedingMonitor("demo/troughs.json")
    print("   ✓ 监控器已初始化")
    
    # 模拟多次检测
    print("\n[3] 模拟进食过程...")
    coverage_levels = [95, 80, 65, 50, 35, 20, 10, 5, 2, 1]  # 从满到空
    
    for i, coverage in enumerate(coverage_levels):
        # 生成模拟图像
        mock_img = generate_mock_trough_image("eating", (400, 300), coverage)
        img_path = f"demo/images/current_{i:02d}.jpg"
        cv2.imwrite(img_path, mock_img)
        
        # 分析
        result = monitor.analyze_trough("trough_A01", img_path)
        print(f"   [{i+1:2d}] 覆盖率: {result.coverage_ratio:5.1f}% | 状态: {result.status:8s} | 置信度: {result.confidence:.2f}")
        
        # 可视化
        analyzer = monitor.troughs["trough_A01"]
        analyzer.visualize(img_path, result, f"demo/output/result_{i:02d}.jpg")
        
        time.sleep(0.1)  # 模拟时间间隔
    
    # 生成报告
    print("\n[4] 生成监控报告...")
    report = monitor.generate_report("trough_A01")
    print(f"""
   监控报告 ({report['trough_id']}):
   - 记录数: {report['total_records']}
   - 平均覆盖率: {report['avg_coverage']}%
   - 最低/最高: {report['min_coverage']}% / {report['max_coverage']}%
   - 当前状态: {report['current_coverage']}%
   - 状态变化次数: {report['status_changes']}
   - 建议: {report['recommendation']}
    """)
    
    # 绘制趋势图
    print("\n[5] 生成趋势图...")
    monitor.plot_trend("trough_A01", "demo/output/trend.png")
    print("   ✓ 趋势图已保存: demo/output/trend.png")
    
    # 保存详细结果
    print("\n[6] 保存详细数据...")
    with open("demo/output/history.json", 'w', encoding='utf-8') as f:
        history_data = [h.to_dict() for h in monitor.history["trough_A01"]]
        json.dump(history_data, f, indent=2, ensure_ascii=False)
    print("   ✓ 历史数据已保存: demo/output/history.json")
    
    print("\n" + "="*60)
    print("演示完成! 请查看 demo/output/ 目录")
    print("="*60)


def generate_mock_trough_image(state: str, size: Tuple[int, int], 
                                coverage: Optional[float] = None) -> np.ndarray:
    """生成模拟食槽图像"""
    width, height = size
    image = np.ones((height, width, 3), dtype=np.uint8) * 180  # 灰色背景
    
    # 绘制食槽边框
    trough_x, trough_y = 50, 50
    trough_w, trough_h = width - 100, height - 100
    cv2.rectangle(image, (trough_x, trough_y), 
                 (trough_x + trough_w, trough_y + trough_h), (100, 100, 100), 3)
    
    if state == "empty":
        # 空槽 - 少量绿色噪点
        noise = np.random.randint(0, 30, (trough_h-10, trough_w-10, 3), dtype=np.uint8)
        noise[:, :, 1] = noise[:, :, 1] + 20  # 增加绿色通道
        image[trough_y+5:trough_y+trough_h-5, trough_x+5:trough_x+trough_w-5] = noise
        
    elif state == "full":
        # 满槽 - 大量绿色
        grass = np.random.randint(40, 120, (trough_h-10, trough_w-10, 3), dtype=np.uint8)
        grass[:, :, 1] = grass[:, :, 1] + 100  # 大量绿色通道
        image[trough_y+5:trough_y+trough_h-5, trough_x+5:trough_x+trough_w-5] = grass
        
    elif state == "eating" and coverage is not None:
        # 进食中 - 根据覆盖率生成
        grass_area = int((trough_h - 10) * coverage / 100)
        
        # 底部是草
        if grass_area > 0:
            grass = np.random.randint(40, 120, (grass_area, trough_w-10, 3), dtype=np.uint8)
            grass[:, :, 1] = grass[:, :, 1] + 100
            y_start = trough_y + trough_h - 5 - grass_area
            y_end = trough_y + trough_h - 5
            image[y_start:y_end, trough_x+5:trough_x+trough_w-5] = grass
        
        # 顶部是空
        if grass_area < trough_h - 10:
            empty = np.random.randint(0, 30, (trough_h - 10 - grass_area, trough_w-10, 3), dtype=np.uint8)
            empty[:, :, 1] = empty[:, :, 1] + 20
            image[trough_y+5:trough_y+trough_h-5-grass_area, trough_x+5:trough_x+trough_w-5] = empty
    
    # 添加随机噪点模拟真实环境
    noise_mask = np.random.random(image.shape[:2]) > 0.95
    noise_color = np.random.randint(0, 255, (3,), dtype=np.uint8)
    image[noise_mask] = noise_color
    
    return image


# ============ 主程序 ============

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_mode()
    else:
        print("""
林麝食量监控系统 MVP

使用方法:
  python grass_monitor.py demo     - 运行演示模式

配置文件格式 (troughs.json):
[
  {
    "trough_id": "trough_A01",
    "name": "A01号食槽",
    "roi": [x, y, width, height],
    "empty_baseline": "path/to/empty.jpg",
    "full_baseline": "path/to/full.jpg"
  }
]

Python API 使用示例:
  from grass_monitor import FeedingMonitor
  
  monitor = FeedingMonitor("troughs.json")
  result = monitor.analyze_trough("trough_A01", "current.jpg")
  print(f"覆盖率: {result.coverage_ratio}%")
        """)
