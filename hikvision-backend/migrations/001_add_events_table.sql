-- Migration 001: 创建原子事件表 (events)
-- 用于存储算法每秒检测到的原子事件

CREATE TABLE IF NOT EXISTS events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL COMMENT '租户ID',
    enclosure_id INT NOT NULL COMMENT '圈舍ID',
    animal_id VARCHAR(32) COMMENT '动物耳标号（个体识别后）',
    camera_id VARCHAR(64) COMMENT '摄像头ID',
    channel_no INT COMMENT '通道号',
    
    event_type ENUM('movement', 'eating', 'drinking', 'resting', 'alert') NOT NULL COMMENT '事件类型',
    confidence FLOAT COMMENT '置信度 0-1',
    
    -- 位置信息（边界框）
    bbox_x1 FLOAT,
    bbox_y1 FLOAT,
    bbox_x2 FLOAT,
    bbox_y2 FLOAT,
    
    -- 元数据
    metadata JSON COMMENT '事件元数据: overlap_ratio, movement_score等',
    
    -- 时间
    event_time DATETIME(3) NOT NULL COMMENT '事件发生时间（毫秒精度）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (enclosure_id) REFERENCES enclosures(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_client_time (client_id, event_time),
    INDEX idx_enclosure_time (enclosure_id, event_time),
    INDEX idx_event_type_time (event_type, event_time),
    INDEX idx_animal_id (animal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='原子事件表 - 算法秒级输出';
