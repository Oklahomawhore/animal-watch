-- Migration 005: 创建饲养记录表 (care_records)
-- 用于存储饲养员的日常记录

CREATE TABLE IF NOT EXISTS care_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL COMMENT '租户ID',
    enclosure_id INT COMMENT '圈舍ID',
    animal_id VARCHAR(32) COMMENT '耳标号',
    
    -- 记录类型和分类
    record_type ENUM('observation', 'task', 'measurement', 'photo') NOT NULL COMMENT 'observation/task/measurement/photo',
    category ENUM('粪便', '体温', '蹄部', '用药', '喂食', '其他') COMMENT '分类',
    
    -- 记录内容
    content TEXT COMMENT '记录内容',
    status ENUM('pending', 'completed', 'cancelled') DEFAULT 'completed' COMMENT 'pending/completed/cancelled',
    priority TINYINT DEFAULT 0 COMMENT '0:普通 1:优先 2:紧急',
    
    -- 多媒体
    voice_url VARCHAR(512) COMMENT '语音URL',
    images JSON COMMENT '图片URL列表',
    
    -- 执行人
    operator_id BIGINT COMMENT '执行人ID',
    operator_name VARCHAR(64) COMMENT '执行人姓名',
    
    -- 时间
    scheduled_date DATE COMMENT '计划日期（待办用）',
    completed_at DATETIME COMMENT '完成时间',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (enclosure_id) REFERENCES enclosures(id) ON DELETE SET NULL,
    
    -- 索引
    INDEX idx_animal_created (animal_id, created_at),
    INDEX idx_scheduled_status (scheduled_date, status),
    INDEX idx_record_type (record_type, created_at),
    INDEX idx_client_id (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='饲养记录';
