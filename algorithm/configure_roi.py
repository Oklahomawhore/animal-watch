#!/usr/bin/env python3
"""
ROI区域配置工具
用于交互式标注食槽、水盆等ROI区域
"""
import cv2
import numpy as np
import json
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# 添加算法目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import get_config, ROIConfig, CameraConfig


class ROIConfigurator:
    """ROI配置器"""
    
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"无法加载图像: {image_path}")
        
        self.clone = self.image.copy()
        self.roi_regions: List[ROIConfig] = []
        self.current_roi = None
        self.drawing = False
        self.ix, self.iy = -1, -1
        
        # ROI类型
        self.roi_types = ['feeding', 'water', 'rest', 'other']
        self.current_type_idx = 0
        
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                img = self.clone.copy()
                cv2.rectangle(img, (self.ix, self.iy), (x, y), (0, 255, 0), 2)
                
                # 显示尺寸
                w, h = abs(x - self.ix), abs(y - self.iy)
                cv2.putText(img, f"{w}x{h}", (x + 5, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                cv2.imshow("ROI Configuration", img)
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            x1, y1 = min(self.ix, x), min(self.iy, y)
            x2, y2 = max(self.ix, x), max(self.iy, y)
            
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
                self.current_roi = {
                    'x': x1,
                    'y': y1,
                    'width': x2 - x1,
                    'height': y2 - y1
                }
                
                # 绘制最终ROI
                cv2.rectangle(self.clone, (x1, y1), (x2, y2), (0, 255, 0), 2)
                roi_type = self.roi_types[self.current_type_idx]
                cv2.putText(self.clone, f"{roi_type}", (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                cv2.imshow("ROI Configuration", self.clone)
                
                print(f"\n绘制区域: ({x1}, {y1}) - ({x2}, {y2})")
                print(f"尺寸: {x2-x1}x{y2-y1}")
    
    def run(self):
        """运行配置器"""
        cv2.namedWindow("ROI Configuration")
        cv2.setMouseCallback("ROI Configuration", self.mouse_callback)
        
        print("="*60)
        print("ROI区域配置工具")
        print("="*60)
        print("\n操作说明:")
        print("  鼠标左键拖拽 - 绘制ROI区域")
        print("  s - 保存当前区域")
        print("  c - 取消当前绘制")
        print("  t - 切换ROI类型 (feeding/water/rest/other)")
        print("  d - 删除最后一个区域")
        print("  r - 重置所有区域")
        print("  q - 保存并退出")
        print("  ESC - 放弃并退出")
        print("="*60)
        
        print(f"\n当前ROI类型: {self.roi_types[self.current_type_idx]}")
        
        while True:
            cv2.imshow("ROI Configuration", self.clone)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # 保存并退出
                break
                
            elif key == 27:  # ESC
                # 放弃并退出
                print("\n放弃配置")
                cv2.destroyAllWindows()
                return None
                
            elif key == ord('s'):
                # 保存当前区域
                if self.current_roi:
                    roi_type = self.roi_types[self.current_type_idx]
                    name = f"{roi_type}_{len(self.roi_regions) + 1}"
                    
                    roi = ROIConfig(
                        name=name,
                        x=self.current_roi['x'],
                        y=self.current_roi['y'],
                        width=self.current_roi['width'],
                        height=self.current_roi['height'],
                        roi_type=roi_type
                    )
                    self.roi_regions.append(roi)
                    
                    print(f"✅ 已保存区域: {name}")
                    print(f"   位置: ({roi.x}, {roi.y})")
                    print(f"   尺寸: {roi.width}x{roi.height}")
                    
                    self.current_roi = None
                else:
                    print("⚠️ 请先绘制一个区域")
                    
            elif key == ord('c'):
                # 取消当前绘制
                self.clone = self.image.copy()
                for roi in self.roi_regions:
                    x2, y2 = roi.x + roi.width, roi.y + roi.height
                    color = (0, 255, 0) if roi.roi_type == 'feeding' else \
                            (255, 0, 0) if roi.roi_type == 'water' else \
                            (0, 0, 255) if roi.roi_type == 'rest' else (128, 128, 128)
                    cv2.rectangle(self.clone, (roi.x, roi.y), (x2, y2), color, 2)
                    cv2.putText(self.clone, roi.name, (roi.x, roi.y - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                self.current_roi = None
                print("🔄 取消当前绘制")
                
            elif key == ord('t'):
                # 切换ROI类型
                self.current_type_idx = (self.current_type_idx + 1) % len(self.roi_types)
                print(f"📝 切换ROI类型: {self.roi_types[self.current_type_idx]}")
                
            elif key == ord('d'):
                # 删除最后一个区域
                if self.roi_regions:
                    removed = self.roi_regions.pop()
                    print(f"🗑️ 删除区域: {removed.name}")
                    
                    # 重绘
                    self.clone = self.image.copy()
                    for roi in self.roi_regions:
                        x2, y2 = roi.x + roi.width, roi.y + roi.height
                        color = (0, 255, 0) if roi.roi_type == 'feeding' else \
                                (255, 0, 0) if roi.roi_type == 'water' else \
                                (0, 0, 255) if roi.roi_type == 'rest' else (128, 128, 128)
                        cv2.rectangle(self.clone, (roi.x, roi.y), (x2, y2), color, 2)
                        cv2.putText(self.clone, roi.name, (roi.x, roi.y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                else:
                    print("⚠️ 没有可删除的区域")
                    
            elif key == ord('r'):
                # 重置所有区域
                self.roi_regions = []
                self.clone = self.image.copy()
                print("🔄 重置所有区域")
        
        cv2.destroyAllWindows()
        return self.roi_regions
    
    def save_config(self, camera_id: str, device_serial: str, channel_no: int = 1):
        """保存配置到文件"""
        config = get_config()
        
        # 检查是否已有配置
        cam_config = config.get_camera_config(camera_id)
        
        if cam_config is None:
            # 创建新配置
            cam_config = CameraConfig(
                camera_id=camera_id,
                device_serial=device_serial,
                channel_no=channel_no,
                name=f"摄像头_{camera_id}",
                roi_regions=self.roi_regions
            )
            config.add_camera(cam_config)
        else:
            # 更新现有配置
            cam_config.roi_regions = self.roi_regions
            config.save_config()
        
        print(f"\n✅ 配置已保存: {camera_id}")
        print(f"   ROI区域数: {len(self.roi_regions)}")
        for roi in self.roi_regions:
            print(f"   - {roi.name}: ({roi.x}, {roi.y}) {roi.width}x{roi.height}")


def configure_from_camera_capture(device_serial: str, channel_no: int = 1):
    """
    从摄像头抓拍图像配置ROI
    
    Args:
        device_serial: 设备序列号
        channel_no: 通道号
    """
    print(f"正在从摄像头 {device_serial} 通道 {channel_no} 抓拍图像...")
    
    # TODO: 实现实际的API调用
    # 目前使用模拟图像
    print("⚠️ 使用模拟图像（请替换为实际API调用）")
    
    # 创建模拟图像
    frame = np.ones((720, 1280, 3), dtype=np.uint8) * 120
    cv2.rectangle(frame, (200, 400), (400, 500), (50, 150, 50), -1)
    cv2.putText(frame, "Feeding Area", (210, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.rectangle(frame, (800, 400), (950, 480), (200, 100, 50), -1)
    cv2.putText(frame, "Water Area", (810, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 保存临时图像
    temp_path = Path(__file__).parent / "temp_capture.jpg"
    cv2.imwrite(str(temp_path), frame)
    
    # 启动配置器
    camera_id = f"{device_serial}_{channel_no}"
    configurator = ROIConfigurator(str(temp_path))
    regions = configurator.run()
    
    if regions:
        configurator.save_config(camera_id, device_serial, channel_no)
    
    # 清理临时文件
    temp_path.unlink(missing_ok=True)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ROI区域配置工具')
    parser.add_argument('--image', '-i', help='图像文件路径')
    parser.add_argument('--camera', '-c', help='设备序列号（从摄像头抓拍）')
    parser.add_argument('--channel', '-ch', type=int, default=1, help='通道号（默认1）')
    parser.add_argument('--camera-id', help='摄像头ID（用于保存配置）')
    
    args = parser.parse_args()
    
    if args.camera:
        # 从摄像头配置
        configure_from_camera_capture(args.camera, args.channel)
    elif args.image:
        # 从图像文件配置
        if not Path(args.image).exists():
            print(f"错误: 图像文件不存在: {args.image}")
            sys.exit(1)
        
        camera_id = args.camera_id or f"camera_{Path(args.image).stem}"
        device_serial = args.camera_id or f"device_{Path(args.image).stem}"
        
        configurator = ROIConfigurator(args.image)
        regions = configurator.run()
        
        if regions:
            configurator.save_config(camera_id, device_serial, args.channel)
        else:
            print("未保存任何配置")
    else:
        # 使用模拟图像
        print("使用模拟图像进行演示...")
        frame = np.ones((720, 1280, 3), dtype=np.uint8) * 120
        cv2.rectangle(frame, (200, 400), (400, 500), (50, 150, 50), -1)
        cv2.putText(frame, "Feeding Area", (210, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.rectangle(frame, (800, 400), (950, 480), (200, 100, 50), -1)
        cv2.putText(frame, "Water Area", (810, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        temp_path = Path(__file__).parent / "temp_demo.jpg"
        cv2.imwrite(str(temp_path), frame)
        
        configurator = ROIConfigurator(str(temp_path))
        regions = configurator.run()
        
        if regions:
            configurator.save_config("demo_camera", "DEMO123", 1)
        
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
