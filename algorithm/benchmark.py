#!/usr/bin/env python3
"""
算法性能测试报告生成工具
生成详细的性能测试报告
"""
import cv2
import numpy as np
import time
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 添加算法目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from cold_start_detector import ColdStartDetector
from capture_service import CaptureService
from config_manager import get_config


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.results = {}
        self.detector = ColdStartDetector()
        
    def create_test_frame(self, width: int, height: int, num_animals: int = 2) -> np.ndarray:
        """创建测试帧"""
        frame = np.ones((height, width, 3), dtype=np.uint8) * 120
        
        # 添加食槽和水盆
        cv2.rectangle(frame, (width//6, height//2), (width//3, height*2//3), (50, 150, 50), -1)
        cv2.rectangle(frame, (width*2//3, height//2), (width*5//6, height*2//3), (200, 100, 50), -1)
        
        # 添加动物
        for i in range(num_animals):
            x = width // 4 + i * width // 4
            y = height // 3 + (i * 50) % 100
            cv2.ellipse(frame, (x, y), (40, 60), 0, 0, 360, (80, 100, 120), -1)
        
        return frame
    
    def benchmark_resolution(self, iterations: int = 50) -> Dict:
        """测试不同分辨率下的性能"""
        print("\n测试不同分辨率性能...")
        
        resolutions = [
            (640, 480, "VGA (640x480)"),
            (800, 600, "SVGA (800x600)"),
            (1280, 720, "HD (1280x720)"),
            (1920, 1080, "Full HD (1920x1080)"),
        ]
        
        results = []
        
        for width, height, name in resolutions:
            times = []
            
            for i in range(iterations):
                frame = self.create_test_frame(width, height)
                
                start = time.perf_counter()
                self.detector.process_frame(frame)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                
                times.append(elapsed)
            
            results.append({
                'resolution': name,
                'width': width,
                'height': height,
                'mean_ms': np.mean(times),
                'std_ms': np.std(times),
                'min_ms': np.min(times),
                'max_ms': np.max(times),
                'median_ms': np.median(times),
                'p95_ms': np.percentile(times, 95),
                'p99_ms': np.percentile(times, 99),
                'fps': 1000 / np.mean(times)
            })
            
            print(f"  {name}: 平均 {np.mean(times):.1f}ms, FPS: {1000/np.mean(times):.1f}")
        
        return {'resolutions': results}
    
    def benchmark_animal_count(self, iterations: int = 30) -> Dict:
        """测试不同动物数量的性能"""
        print("\n测试不同动物数量性能...")
        
        animal_counts = [0, 1, 2, 3, 5, 8]
        results = []
        
        for count in animal_counts:
            times = []
            
            for i in range(iterations):
                frame = self.create_test_frame(1280, 720, num_animals=count)
                
                start = time.perf_counter()
                result = self.detector.process_frame(frame)
                elapsed = (time.perf_counter() - start) * 1000
                
                times.append(elapsed)
            
            results.append({
                'animal_count': count,
                'mean_ms': np.mean(times),
                'std_ms': np.std(times),
                'fps': 1000 / np.mean(times)
            })
            
            print(f"  {count}只动物: 平均 {np.mean(times):.1f}ms, FPS: {1000/np.mean(times):.1f}")
        
        return {'animal_counts': results}
    
    def benchmark_long_running(self, duration_seconds: int = 60) -> Dict:
        """长时间运行稳定性测试"""
        print(f"\n长时间运行测试 ({duration_seconds}秒)...")
        
        times = []
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            frame = self.create_test_frame(1280, 720)
            
            start = time.perf_counter()
            self.detector.process_frame(frame)
            elapsed = (time.perf_counter() - start) * 1000
            
            times.append(elapsed)
            frame_count += 1
            
            # 模拟1秒间隔
            time.sleep(max(0, 1.0 - elapsed / 1000))
        
        actual_duration = time.time() - start_time
        
        # 分段统计
        segment_size = len(times) // 6
        segments = []
        for i in range(6):
            start_idx = i * segment_size
            end_idx = (i + 1) * segment_size if i < 5 else len(times)
            segment_times = times[start_idx:end_idx]
            segments.append({
                'segment': i + 1,
                'mean_ms': np.mean(segment_times),
                'std_ms': np.std(segment_times)
            })
        
        result = {
            'duration_seconds': actual_duration,
            'total_frames': frame_count,
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times),
            'p95_ms': np.percentile(times, 95),
            'p99_ms': np.percentile(times, 99),
            'segments': segments
        }
        
        print(f"  处理 {frame_count} 帧, 平均 {result['mean_ms']:.1f}ms")
        print(f"  稳定性: 标准差 {result['std_ms']:.1f}ms")
        
        return result
    
    def benchmark_memory_usage(self) -> Dict:
        """测试内存使用"""
        print("\n测试内存使用...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 初始内存
        initial_mem = process.memory_info().rss / 1024 / 1024  # MB
        
        # 处理1000帧
        for i in range(1000):
            frame = self.create_test_frame(1280, 720)
            self.detector.process_frame(frame)
        
        # 最终内存
        final_mem = process.memory_info().rss / 1024 / 1024
        
        result = {
            'initial_mb': initial_mem,
            'final_mb': final_mem,
            'increase_mb': final_mem - initial_mem,
            'avg_per_frame_kb': (final_mem - initial_mem) * 1024 / 1000
        }
        
        print(f"  初始内存: {initial_mem:.1f}MB")
        print(f"  最终内存: {final_mem:.1f}MB")
        print(f"  增长: {result['increase_mb']:.1f}MB")
        
        return result
    
    def generate_charts(self, output_dir: Path):
        """生成性能图表"""
        print("\n生成性能图表...")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 分辨率性能对比
        if 'resolutions' in self.results:
            res_data = self.results['resolutions']['resolutions']
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            names = [r['resolution'].split()[0] for r in res_data]
            means = [r['mean_ms'] for r in res_data]
            stds = [r['std_ms'] for r in res_data]
            fps = [r['fps'] for r in res_data]
            
            # 处理时间
            ax1.bar(names, means, yerr=stds, capsize=5, color='steelblue', alpha=0.7)
            ax1.axhline(y=1000, color='r', linestyle='--', label='1秒阈值')
            ax1.set_ylabel('处理时间 (ms)')
            ax1.set_title('不同分辨率处理时间')
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)
            
            # FPS
            ax2.bar(names, fps, color='green', alpha=0.7)
            ax2.axhline(y=1, color='r', linestyle='--', label='1 FPS阈值')
            ax2.set_ylabel('FPS')
            ax2.set_title('不同分辨率FPS')
            ax2.legend()
            ax2.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / 'resolution_performance.png', dpi=150)
            plt.close()
            
            print(f"  已保存: resolution_performance.png")
        
        # 2. 动物数量影响
        if 'animal_counts' in self.results:
            count_data = self.results['animal_counts']['animal_counts']
            
            fig, ax = plt.subplots(figsize=(8, 5))
            
            counts = [c['animal_count'] for c in count_data]
            means = [c['mean_ms'] for c in count_data]
            
            ax.plot(counts, means, 'o-', linewidth=2, markersize=8, color='steelblue')
            ax.axhline(y=1000, color='r', linestyle='--', label='1秒阈值')
            ax.set_xlabel('动物数量')
            ax.set_ylabel('处理时间 (ms)')
            ax.set_title('动物数量对性能的影响')
            ax.legend()
            ax.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / 'animal_count_performance.png', dpi=150)
            plt.close()
            
            print(f"  已保存: animal_count_performance.png")
        
        # 3. 长时间运行稳定性
        if 'long_running' in self.results:
            long_data = self.results['long_running']
            
            if 'segments' in long_data:
                fig, ax = plt.subplots(figsize=(10, 5))
                
                segments = long_data['segments']
                x = [s['segment'] for s in segments]
                means = [s['mean_ms'] for s in segments]
                stds = [s['std_ms'] for s in segments]
                
                ax.errorbar(x, means, yerr=stds, marker='o', linewidth=2, 
                           capsize=5, color='steelblue')
                ax.axhline(y=1000, color='r', linestyle='--', label='1秒阈值')
                ax.set_xlabel('时间段')
                ax.set_ylabel('处理时间 (ms)')
                ax.set_title('长时间运行稳定性')
                ax.legend()
                ax.grid(alpha=0.3)
                
                plt.tight_layout()
                plt.savefig(output_dir / 'stability_performance.png', dpi=150)
                plt.close()
                
                print(f"  已保存: stability_performance.png")
    
    def generate_report(self, output_path: str = None):
        """生成完整测试报告"""
        print("\n" + "="*60)
        print("算法性能测试报告")
        print("="*60)
        
        # 运行所有测试
        self.results['resolutions'] = self.benchmark_resolution(iterations=50)
        self.results['animal_counts'] = self.benchmark_animal_count(iterations=30)
        self.results['long_running'] = self.benchmark_long_running(duration_seconds=60)
        
        try:
            self.results['memory'] = self.benchmark_memory_usage()
        except ImportError:
            print("  跳过内存测试 (psutil 未安装)")
        
        # 生成图表
        output_dir = Path(__file__).parent / "output" / "performance"
        self.generate_charts(output_dir)
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'test_count': len(self.results),
                'meets_requirements': self._check_requirements()
            },
            'details': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        # 保存JSON报告
        if output_path is None:
            output_path = output_dir / 'performance_report.json'
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存: {output_path}")
        
        # 打印摘要
        self._print_summary(report)
        
        return report
    
    def _check_requirements(self) -> Dict:
        """检查是否满足要求"""
        checks = {
            'real_time_1fps': False,
            'resolution_hd': False,
            'stability': False
        }
        
        # 检查实时性 (1秒/帧 = 1 FPS)
        if 'resolutions' in self.results:
            for res in self.results['resolutions']['resolutions']:
                if 'HD' in res['resolution'] and res['mean_ms'] < 1000:
                    checks['real_time_1fps'] = True
                if 'HD' in res['resolution']:
                    checks['resolution_hd'] = True
        
        # 检查稳定性
        if 'long_running' in self.results:
            long_data = self.results['long_running']
            cv = long_data['std_ms'] / long_data['mean_ms'] if long_data['mean_ms'] > 0 else 0
            checks['stability'] = cv < 0.3  # 变异系数小于30%
        
        checks['all_passed'] = all(checks.values())
        return checks
    
    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if 'resolutions' in self.results:
            hd_data = None
            for res in self.results['resolutions']['resolutions']:
                if 'HD' in res['resolution']:
                    hd_data = res
                    break
            
            if hd_data:
                if hd_data['mean_ms'] > 500:
                    recommendations.append("处理时间超过500ms，建议优化算法或降低分辨率")
                if hd_data['p95_ms'] > 1000:
                    recommendations.append("P95延迟超过1秒，存在实时性风险")
        
        if 'memory' in self.results:
            mem_data = self.results['memory']
            if mem_data['increase_mb'] > 100:
                recommendations.append("内存增长较快，建议检查内存泄漏")
        
        if not recommendations:
            recommendations.append("性能表现良好，满足实时性要求")
        
        return recommendations
    
    def _print_summary(self, report: Dict):
        """打印报告摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)
        
        summary = report['summary']
        checks = summary['meets_requirements']
        
        print(f"\n实时性要求 (1秒/帧):")
        print(f"  {'✅' if checks['real_time_1fps'] else '❌'} 1 FPS 达标")
        
        print(f"\n分辨率支持:")
        print(f"  {'✅' if checks['resolution_hd'] else '❌'} HD (1280x720)")
        
        print(f"\n稳定性:")
        print(f"  {'✅' if checks['stability'] else '❌'} 长时间运行稳定")
        
        print(f"\n总体评估:")
        if checks['all_passed']:
            print("  ✅ 所有测试通过，满足上线要求")
        else:
            print("  ⚠️ 部分测试未通过，需要优化")
        
        print(f"\n优化建议:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='算法性能测试报告生成')
    parser.add_argument('--output', '-o', help='输出报告路径')
    parser.add_argument('--quick', '-q', action='store_true', help='快速模式（减少测试量）')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    if args.quick:
        # 快速模式
        print("快速模式（减少测试量）")
        benchmark.results['resolutions'] = benchmark.benchmark_resolution(iterations=10)
        benchmark.results['animal_counts'] = benchmark.benchmark_animal_count(iterations=10)
    else:
        # 完整测试
        benchmark.generate_report(args.output)


if __name__ == "__main__":
    main()
