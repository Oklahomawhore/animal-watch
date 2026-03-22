-- Migration 002: 创建小时统计表 (event_hourly_stats)
-- 用于存储小时级聚合数据

CREATE TABLE IF NOT EXISTS event_hourly_stats (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL COMMENT '租户ID',
    enclosure_id INT NOT NULL COMMENT '圈舍ID',
    animal_id VARCHAR(32) COMMENT '耳标号，为空表示群体统计',
    
    -- 统计时间
    stat_date DATE NOT NULL COMMENT '统计日期',
    hour TINYINT NOT NULL COMMENT '小时 0-23',
    
    -- 活动统计
    movement_count INT DEFAULT 0 COMMENT '移动次数',
    movement_duration INT DEFAULT 0 COMMENT '移动总时长(秒)',
    avg_movement_score FLOAT COMMENT '平均运动强度',
    
    -- 进食统计
    eating_count INT DEFAULT 0 COMMENT '进食次数',
    eating_duration INT DEFAULT 0 COMMENT '进食时长(秒)',
    feed_consumption_percent FLOAT COMMENT '饲料消耗百分比估算',
    
    -- 饮水统计
    drinking_count INT DEFAULT 0 COMMENT '饮水次数',
    drinking_duration INT DEFAULT 0 COMMENT '饮水时长(秒)',
    water_consumption_liters FLOAT COMMENT '饮水量估算',
    
    -- 休息统计
    resting_duration INT DEFAULT 0 COMMENT '休息时长(秒)',
    
    -- 异常统计
    alert_count INT DEFAULT 0 COMMENT '告警次数',
    alert_types JSON COMMENT '告警类型列表',
    
    -- 综合评分
    activity_score INT COMMENT '活动评分 0-100',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (enclosure_id) REFERENCES enclosures(id) ON DELETE CASCADE,
    
    -- 唯一索引和查询索引
    UNIQUE KEY uk_enclosure_animal_hour (enclosure_id, animal_id, stat_date, hour),
    INDEX idx_stat_date_hour (stat_date, hour),
    INDEX idx_animal_date (animal_id, stat_date),
    INDEX idx_client_id (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='小时级事件统计';
