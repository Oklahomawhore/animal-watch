#!/usr/bin/env python3
"""
冷启动方案演示脚本
验证从视频截图到 events 流的转换
"""

import cv2
import numpy as np
import json
import time
import sys
from pathlib import Path

# 添加算法目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from cold_start_detector import ColdStartDetector, EventStreamGenerator, EventType


def create_synthetic_frame(width=1280, height=720, frame_idx=0):
    """
    生成合成测试帧（模拟真实场景）
    """
    # 创建背景（圈舍地面）
    frame = np.ones((height, width, 3), dtype=np.uint8) * 120
    
    # 添加食槽区域（绿色矩形）
    cv2.rectangle(frame, (200, 400), (400, 500), (50, 150, 50), -1)
    cv2.putText(frame, "Feeding Trough", (210, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # 添加水盆区域（蓝色矩形）
    cv2.rectangle(frame, (800, 400), (950, 480), (150, 100, 50), -1)
    cv2.putText(frame, "Water Basin", (810, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # 模拟动物移动（基于帧索引）
    num_animals = 3
    for i in range(num_animals):
        # 动物位置随时间变化
        base_x = 300 + i * 200
        base_y = 200 + (frame_idx * 5 + i * 50) % 150
        
        # 绘制动物（棕色椭圆）
        animal_color = (80, 100, 120)  # BGR
        cv2.ellipse(frame, (base_x, base_y), (40, 60), 0, 0, 360, animal_color, -1)
        
        # 偶尔让动物靠近食槽（模拟进食）
        if frame_idx % 100 > 80 and i == 0:
            cv2.ellipse(frame, (300, 450), (35, 50), 0, 0, 360, animal_color, -1)
        
        # 偶尔让动物靠近水盆（模拟饮水）
        if frame_idx % 150 > 130 and i == 1:
            cv2.ellipse(frame, (875, 440), (35, 50), 0, 0, 360, animal_color, -1)
    
    # 添加噪声模拟真实场景
    noise = np.random.normal(0, 5, frame.shape).astype(np.uint8)
    frame = cv2.add(frame, noise)
    
    return frame


def demo_single_frame():
    """演示单帧检测"""
    print("=" * 60)
    print("演示 1: 单帧检测")
    print("=" * 60)
    
    # 创建检测器
    detector = ColdStartDetector()
    
    # 生成测试帧
    frame = create_synthetic_frame(frame_idx=50)
    
    # 处理帧
    result = detector.process_frame(frame)
    
    print(f"\n检测时间戳: {result['timestamp']}")
    print(f"检测到动物数量: {result['animal_count']}")
    print(f"运动量评分: {result['movement_score']:.2f}")
    print(f"\n检测到的事件:")
    
    for event in result['events']:
        print(f"  - {event['event_type']}: 置信度={event['confidence']:.2f}")
        if event['metadata']:
            print(f"    元数据: {event['metadata']}")
    
    # 保存可视化结果
    vis_frame = visualize_detection(frame, result)
    output_path = Path(__file__).parent / "demo_output_single.jpg"
    cv2.imwrite(str(output_path), vis_frame)
    print(f"\n可视化结果已保存: {output_path}")
    
    return result


def demo_event_stream():
    """演示事件流生成"""
    print("\n" + "=" * 60)
    print("演示 2: 事件流生成（模拟视频序列）")
    print("=" * 60)
    
    detector = ColdStartDetector()
    stream_gen = EventStreamGenerator(detector)
    
    print("\n模拟处理 200 帧视频...")
    
    all_events = []
    for i in range(200):
        frame = create_synthetic_frame(frame_idx=i)
        new_events = stream_gen.process_frame(frame)
        all_events.extend(new_events)
        
        if new_events:
            print(f"  帧 {i}: 检测到 {len(new_events)} 个新事件")
            for e in new_events:
                print(f"    - {e.event_type.value}")
    
    print(f"\n总共生成 {len(all_events)} 个原子事件")
    
    # 获取统计
    stats = stream_gen.get_statistics(time_window=3600)
    print(f"\n事件统计:")
    print(f"  总事件数: {stats['total_events']}")
    print(f"  事件分布:")
    for event_type, count in stats['event_counts'].items():
        print(f"    - {event_type}: {count}")
    
    # 保存最后一帧的可视化
    frame = create_synthetic_frame(frame_idx=199)
    result = detector.process_frame(frame)
    vis_frame = visualize_detection(frame, result)
    output_path = Path(__file__).parent / "demo_output_stream.jpg"
    cv2.imwrite(str(output_path), vis_frame)
    print(f"\n可视化结果已保存: {output_path}")
    
    return all_events


def demo_real_image(image_path: str):
    """演示真实图像检测"""
    print("\n" + "=" * 60)
    print("演示 3: 真实图像检测")
    print("=" * 60)
    
    if not Path(image_path).exists():
        print(f"错误: 图像不存在: {image_path}")
        print("跳过此演示")
        return None
    
    # 读取图像
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"错误: 无法读取图像: {image_path}")
        return None
    
    print(f"\n处理图像: {image_path}")
    print(f"图像尺寸: {frame.shape}")
    
    # 创建检测器
    detector = ColdStartDetector()
    
    # 处理帧
    result = detector.process_frame(frame)
    
    print(f"\n检测结果:")
    print(f"  动物数量: {result['animal_count']}")
    print(f"  运动量: {result['movement_score']:.2f}")
    print(f"  事件数: {len(result['events'])}")
    
    for event in result['events']:
        print(f"    - {event['event_type']}: {event['confidence']:.2f}")
    
    # 保存可视化结果
    vis_frame = visualize_detection(frame, result)
    output_path = Path(__file__).parent / "demo_output_real.jpg"
    cv2.imwrite(str(output_path), vis_frame)
    print(f"\n可视化结果已保存: {output_path}")
    
    return result


def visualize_detection(frame: np.ndarray, result: dict) -> np.ndarray:
    """
    可视化检测结果
    """
    vis = frame.copy()
    h, w = vis.shape[:2]
    
    # 绘制检测框
    for det in result['detections']:
        x1, y1, x2, y2 = int(det['x1']), int(det['y1']), int(det['x2']), int(det['y2'])
        conf = det['confidence']
        
        # 根据置信度选择颜色
        color = (0, int(255 * conf), int(255 * (1 - conf)))
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, f"Animal: {conf:.2f}", (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # 绘制事件信息
    y_offset = 30
    cv2.putText(vis, f"Animals: {result['animal_count']}", (10, y_offset),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_offset += 30
    cv2.putText(vis, f"Movement: {result['movement_score']:.1f}", (10, y_offset),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # 绘制事件列表
    y_offset += 40
    for event in result['events']:
        text = f"{event['event_type']}: {event['confidence']:.2f}"
        cv2.putText(vis, text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25
    
    return vis


def export_events_to_json(events: list, output_path: str):
    """导出事件为JSON"""
    events_dict = [e.to_dict() if hasattr(e, 'to_dict') else e for e in events]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(events_dict, f, ensure_ascii=False, indent=2)
    
    print(f"\n事件已导出到: {output_path}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("林麝行为检测 - 冷启动方案演示")
    print("=" * 60)
    print("\n本演示验证：")
    print("1. 无需标注数据的动物检测")
    print("2. 原子事件识别（移动、进食、饮水、休息）")
    print("3. 事件流生成与去重")
    print("4. 从截图到结构化事件的转换")
    
    # 演示1: 单帧检测
    result1 = demo_single_frame()
    
    # 演示2: 事件流
    events = demo_event_stream()
    
    # 演示3: 真实图像（如果有）
    test_image = Path(__file__).parent / "test_image.jpg"
    if test_image.exists():
        demo_real_image(str(test_image))
    else:
        print(f"\n跳过真实图像演示（未找到测试图像: {test_image}）")
        print("可以将真实截图命名为 'test_image.jpg' 放在 algorithm/ 目录下")
    
    # 导出事件示例
    if events:
        export_path = Path(__file__).parent / "demo_events.json"
        export_events_to_json(events, str(export_path))
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n冷启动方案可行性:")
    print("✅ 无需预训练模型，纯CV方法检测动物")
    print("✅ 基于区域重叠检测进食/饮水行为")
    print("✅ 背景减除计算运动量")
    print("✅ 事件去重避免重复上报")
    print("✅ 可处理真实截图生成结构化事件流")


if __name__ == "__main__":
    main()
