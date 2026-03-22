-- Migration 004: 创建诊疗记录表 V2 (medical_records_v2)
-- 新版诊疗记录表，基于算法开发计划V2设计

CREATE TABLE IF NOT EXISTS medical_records_v2 (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL COMMENT '租户ID',
    animal_id VARCHAR(32) NOT NULL COMMENT '耳标号',
    
    -- 诊断信息
    diagnosis VARCHAR(128) COMMENT '诊断如 肠炎',
    diagnosis_date DATE COMMENT '诊断日期',
    status ENUM('ongoing', 'resolved', 'chronic') DEFAULT 'ongoing' COMMENT 'ongoing/resolved/chronic',
    
    -- 用药方案
    medications JSON COMMENT '用药方案: [{name,dosage,route,remain_days}]',
    treatment_day INT DEFAULT 1 COMMENT '治疗第几天',
    
    -- 兽医和备注
    veterinarian VARCHAR(64) COMMENT '兽医',
    notes TEXT,
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_animal_id (animal_id),
    INDEX idx_status_date (status, diagnosis_date),
    INDEX idx_client_id (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='诊疗记录 - 新版';
