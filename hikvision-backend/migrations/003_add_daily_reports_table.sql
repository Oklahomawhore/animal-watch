-- Migration 003: 创建日报表 (daily_reports)
-- 用于存储每日生成的动物健康报告

CREATE TABLE IF NOT EXISTS daily_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL COMMENT '租户ID',
    enclosure_id INT NOT NULL COMMENT '圈舍ID',
    animal_id VARCHAR(32) NOT NULL COMMENT '耳标号如 LS-B2-025',
    report_date DATE NOT NULL COMMENT '报告日期',
    
    -- 基础信息（快照）
    ear_tag VARCHAR(32) COMMENT '耳标号',
    gender VARCHAR(8) COMMENT '雌/雄',
    age VARCHAR(16) COMMENT '年龄如 1岁',
    health_status TINYINT DEFAULT 0 COMMENT '0:绿 1:黄 2:红',
    
    -- 活动数据
    activity_score INT COMMENT '活动评分如 82分',
    activity_level VARCHAR(16) COMMENT '正常/偏低/偏高',
    activity_trend JSON COMMENT '7天趋势 [78,82,75,80,82,79,82]',
    
    -- 进食数据
    feed_main_remain_percent FLOAT COMMENT '主槽剩余%如 35',
    feed_aux_remain_percent FLOAT COMMENT '辅槽剩余%如 72',
    eating_status VARCHAR(32) COMMENT '慢食/正常/快食/未进食',
    
    -- 饮水数据
    water_consumption_liters FLOAT COMMENT '饮水量如 6.8L',
    drinking_status VARCHAR(32) COMMENT '偏多/正常/偏少',
    
    -- 告警摘要
    alerts_summary JSON COMMENT '[{type,message,level,time}]',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (enclosure_id) REFERENCES enclosures(id) ON DELETE CASCADE,
    
    -- 唯一索引和查询索引
    UNIQUE KEY uk_animal_date (animal_id, report_date),
    INDEX idx_enclosure_date (enclosure_id, report_date),
    INDEX idx_report_date (report_date),
    INDEX idx_client_id (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='动物健康日报';
