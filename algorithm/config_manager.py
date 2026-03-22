"""
林麝算法 Pipeline 配置
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import json
import os


@dataclass
class ROIConfig:
    """ROI区域配置"""
    name: str
    x: int
    y: int
    width: int
    height: int
    roi_type: str  # 'feeding', 'water', 'rest', 'other'
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'type': self.roi_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ROIConfig':
        return cls(
            name=data['name'],
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height'],
            roi_type=data['type']
        )
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """返回 (x1, y1, x2, y2) 格式"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class CameraConfig:
    """摄像头算法配置"""
    camera_id: str
    device_serial: str
    channel_no: int = 1
    name: str = ""
    roi_regions: List[ROIConfig] = field(default_factory=list)
    enabled: bool = True
    
    # 算法参数
    detection_threshold: float = 0.3
    movement_threshold: float = 10.0
    min_animal_area: int = 500
    max_animal_area_ratio: float = 0.5
    
    # 事件冷却时间（秒）
    event_cooldowns: Dict[str, int] = field(default_factory=lambda: {
        'eating': 30,
        'drinking': 30,
        'movement': 5,
        'resting': 60
    })
    
    def to_dict(self) -> Dict:
        return {
            'camera_id': self.camera_id,
            'device_serial': self.device_serial,
            'channel_no': self.channel_no,
            'name': self.name,
            'roi_regions': [r.to_dict() for r in self.roi_regions],
            'enabled': self.enabled,
            'detection_threshold': self.detection_threshold,
            'movement_threshold': self.movement_threshold,
            'min_animal_area': self.min_animal_area,
            'max_animal_area_ratio': self.max_animal_area_ratio,
            'event_cooldowns': self.event_cooldowns
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CameraConfig':
        roi_regions = [ROIConfig.from_dict(r) for r in data.get('roi_regions', [])]
        return cls(
            camera_id=data['camera_id'],
            device_serial=data['device_serial'],
            channel_no=data.get('channel_no', 1),
            name=data.get('name', ''),
            roi_regions=roi_regions,
            enabled=data.get('enabled', True),
            detection_threshold=data.get('detection_threshold', 0.3),
            movement_threshold=data.get('movement_threshold', 10.0),
            min_animal_area=data.get('min_animal_area', 500),
            max_animal_area_ratio=data.get('max_animal_area_ratio', 0.5),
            event_cooldowns=data.get('event_cooldowns', {
                'eating': 30, 'drinking': 30, 'movement': 5, 'resting': 60
            })
        )


class AlgorithmConfig:
    """算法全局配置管理"""
    
    DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'algorithm_config.json')
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.cameras: Dict[str, CameraConfig] = {}
        self.global_settings = {
            'frame_interval': 1.0,  # 处理间隔（秒）
            'max_fps': 1,  # 最大帧率
            'enable_gpu': False,
            'debug_mode': False,
            'save_debug_images': False,
            'debug_image_path': 'output/debug'
        }
        self._load_config()
    
    def _load_config(self):
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载全局设置
                self.global_settings.update(data.get('global_settings', {}))
                
                # 加载摄像头配置
                for cam_data in data.get('cameras', []):
                    cam_config = CameraConfig.from_dict(cam_data)
                    self.cameras[cam_config.camera_id] = cam_config
                
                print(f"✅ 配置已加载: {self.config_path}")
                print(f"   摄像头数量: {len(self.cameras)}")
            except Exception as e:
                print(f"⚠️ 加载配置失败: {e}，使用默认配置")
                self._create_default_config()
        else:
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self.save_config()
        print(f"✅ 已创建默认配置文件: {self.config_path}")
    
    def save_config(self):
        """保存配置到文件"""
        data = {
            'global_settings': self.global_settings,
            'cameras': [cam.to_dict() for cam in self.cameras.values()]
        }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_camera_config(self, camera_id: str) -> Optional[CameraConfig]:
        """获取摄像头配置"""
        return self.cameras.get(camera_id)
    
    def add_camera(self, config: CameraConfig):
        """添加摄像头配置"""
        self.cameras[config.camera_id] = config
        self.save_config()
    
    def update_camera(self, camera_id: str, **kwargs):
        """更新摄像头配置"""
        if camera_id in self.cameras:
            cam = self.cameras[camera_id]
            for key, value in kwargs.items():
                if hasattr(cam, key):
                    setattr(cam, key, value)
            self.save_config()
    
    def remove_camera(self, camera_id: str):
        """移除摄像头配置"""
        if camera_id in self.cameras:
            del self.cameras[camera_id]
            self.save_config()
    
    def add_roi_region(self, camera_id: str, roi: ROIConfig):
        """为摄像头添加ROI区域"""
        if camera_id in self.cameras:
            self.cameras[camera_id].roi_regions.append(roi)
            self.save_config()
    
    def list_cameras(self) -> List[str]:
        """列出所有摄像头ID"""
        return list(self.cameras.keys())


# 全局配置实例
_config_instance = None

def get_config(config_path: Optional[str] = None) -> AlgorithmConfig:
    """获取全局配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = AlgorithmConfig(config_path)
    return _config_instance
