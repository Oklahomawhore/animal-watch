-- 数据库初始化脚本
-- 林麝健康监测系统数据库 Schema

-- 创建数据库
CREATE DATABASE IF NOT EXISTS linshe CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE linshe;

-- =============================================
-- 租户管理
-- =============================================
CREATE TABLE tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '租户名称',
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '租户编码',
    contact_name VARCHAR(50) COMMENT '联系人',
    contact_phone VARCHAR(20) COMMENT '联系电话',
    address TEXT COMMENT '地址',
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    config JSON COMMENT '租户配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='租户表';

-- =============================================
-- 用户管理
-- =============================================
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    open_id VARCHAR(100) COMMENT '微信OpenID',
    phone VARCHAR(20) COMMENT '手机号',
    username VARCHAR(50) COMMENT '用户名',
    password_hash VARCHAR(255) COMMENT '密码哈希',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    avatar VARCHAR(255) COMMENT '头像URL',
    role ENUM('super_admin', 'admin', 'operator', 'viewer') DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant (tenant_id),
    INDEX idx_openid (open_id),
    INDEX idx_phone (phone),
    INDEX idx_role (role)
) ENGINE=InnoDB COMMENT='用户表';

-- =============================================
-- 养殖场/基地
-- =============================================
CREATE TABLE farms (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '养殖场名称',
    code VARCHAR(50) COMMENT '养殖场编码',
    location JSON COMMENT '地理位置 {lat, lng, address}',
    total_sheds INT DEFAULT 0 COMMENT '圈舍总数',
    total_cameras INT DEFAULT 0 COMMENT '摄像头总数',
    status ENUM('active', 'inactive', 'maintenance') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant (tenant_id),
    INDEX idx_code (code)
) ENGINE=InnoDB COMMENT='养殖场表';

-- =============================================
-- 圈舍
-- =============================================
CREATE TABLE sheds (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    farm_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '圈舍名称',
    code VARCHAR(50) COMMENT '圈舍编码',
    capacity INT DEFAULT 50 COMMENT '容量',
    current_count INT DEFAULT 0 COMMENT '当前存栏数',
    area DECIMAL(10, 2) COMMENT '面积(平方米)',
    location JSON COMMENT '位置信息',
    status ENUM('normal', 'warning', 'danger', 'maintenance') DEFAULT 'normal',
    config JSON COMMENT '配置信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
    INDEX idx_tenant (tenant_id),
    INDEX idx_farm (farm_id),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='圈舍表';

-- =============================================
-- 摄像头
-- =============================================
CREATE TABLE cameras (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    farm_id VARCHAR(36) NOT NULL,
    shed_id VARCHAR(36),
    name VARCHAR(100) NOT NULL COMMENT '摄像头名称',
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '设备编码',
    device_serial VARCHAR(100) COMMENT '设备序列号',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    port INT DEFAULT 80,
    username VARCHAR(50) COMMENT '用户名',
    password_encrypted VARCHAR(255) COMMENT '加密密码',
    protocol ENUM('http', 'https') DEFAULT 'http',
    channel_id INT DEFAULT 1,
    stream_url VARCHAR(255) COMMENT '视频流地址',
    status ENUM('online', 'offline', 'error', 'maintenance') DEFAULT 'offline',
    last_heartbeat TIMESTAMP NULL,
    capabilities JSON COMMENT '能力集 {motion_detection, intrusion, ...}',
    config JSON COMMENT '配置参数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
    FOREIGN KEY (shed_id) REFERENCES sheds(id) ON DELETE SET NULL,
    INDEX idx_tenant (tenant_id),
    INDEX idx_farm (farm_id),
    INDEX idx_shed (shed_id),
    INDEX idx_code (code),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='摄像头表';

-- =============================================
-- 林麝档案
-- =============================================
CREATE TABLE animals (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    farm_id VARCHAR(36) NOT NULL,
    shed_id VARCHAR(36),
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '耳标号',
    name VARCHAR(50) COMMENT '昵称',
    gender ENUM('male', 'female') COMMENT '性别',
    birth_date DATE COMMENT '出生日期',
    age_months INT COMMENT '月龄',
    weight DECIMAL(6, 2) COMMENT '体重(kg)',
    status ENUM('healthy', 'warning', 'sick', 'isolated', 'quarantined', 'sold', 'died') DEFAULT 'healthy',
    breed VARCHAR(50) COMMENT '品种',
    origin VARCHAR(100) COMMENT '来源',
    description TEXT COMMENT '备注',
    profile_image VARCHAR(255) COMMENT '照片',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
    FOREIGN KEY (shed_id) REFERENCES sheds(id) ON DELETE SET NULL,
    INDEX idx_tenant (tenant_id),
    INDEX idx_farm (farm_id),
    INDEX idx_shed (shed_id),
    INDEX idx_code (code),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='林麝档案表';

-- =============================================
-- 活动量记录 (汇总数据)
-- =============================================
CREATE TABLE activity_records (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    camera_id VARCHAR(36) NOT NULL,
    shed_id VARCHAR(36),
    animal_id VARCHAR(36),
    record_time DATETIME NOT NULL COMMENT '记录时间',
    period ENUM('5min', '15min', 'hour', 'day') DEFAULT '5min' COMMENT '统计周期',
    
    -- 活动量指标
    activity_score DECIMAL(5, 2) COMMENT '活动量评分 0-100',
    activity_level ENUM('idle', 'low', 'moderate', 'high', 'very_high') COMMENT '活动等级',
    event_count INT DEFAULT 0 COMMENT '事件数量',
    event_frequency DECIMAL(6, 2) COMMENT '事件频率(次/分钟)',
    region_coverage INT COMMENT '覆盖区域数',
    
    -- 原始统计
    raw_data JSON COMMENT '原始统计数据',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    FOREIGN KEY (shed_id) REFERENCES sheds(id) ON DELETE SET NULL,
    FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE SET NULL,
    INDEX idx_tenant_time (tenant_id, record_time),
    INDEX idx_camera_time (camera_id, record_time),
    INDEX idx_shed_time (shed_id, record_time),
    INDEX idx_period (period)
) ENGINE=InnoDB COMMENT='活动量记录表';

-- =============================================
-- 异常告警
-- =============================================
CREATE TABLE alerts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    farm_id VARCHAR(36),
    shed_id VARCHAR(36),
    camera_id VARCHAR(36),
    animal_id VARCHAR(36),
    
    alert_type ENUM('activity_drop', 'activity_spike', 'prolonged_idle', 
                    'device_offline', 'device_error', 'abnormal_behavior') NOT NULL,
    severity ENUM('info', 'warning', 'critical') DEFAULT 'warning',
    
    title VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 异常详情
    current_value DECIMAL(10, 2) COMMENT '当前值',
    baseline_value DECIMAL(10, 2) COMMENT '基线值',
    deviation DECIMAL(10, 2) COMMENT '偏差值',
    z_score DECIMAL(6, 2) COMMENT 'Z分数',
    
    -- 状态
    status ENUM('unhandled', 'handling', 'resolved', 'ignored') DEFAULT 'unhandled',
    handled_by VARCHAR(36),
    handled_at TIMESTAMP NULL,
    handle_note TEXT,
    
    -- 通知状态
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_time TIMESTAMP NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
    FOREIGN KEY (shed_id) REFERENCES sheds(id) ON DELETE SET NULL,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL,
    FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE SET NULL,
    FOREIGN KEY (handled_by) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_time (tenant_id, created_at),
    INDEX idx_type (alert_type),
    INDEX idx_severity (severity),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='告警表';

-- =============================================
-- 系统配置
-- =============================================
CREATE TABLE system_configs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE KEY uk_tenant_key (tenant_id, config_key)
) ENGINE=InnoDB COMMENT='系统配置表';

-- =============================================
-- 操作日志
-- =============================================
CREATE TABLE operation_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_id VARCHAR(36) COMMENT '资源ID',
    details JSON COMMENT '操作详情',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    user_agent TEXT COMMENT 'User Agent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_tenant_time (tenant_id, created_at),
    INDEX idx_user (user_id),
    INDEX idx_action (action)
) ENGINE=InnoDB COMMENT='操作日志表';

-- 插入默认租户
INSERT INTO tenants (id, name, code, status) VALUES 
('tenant_demo', '演示租户', 'DEMO', 'active');

-- 插入默认用户 (密码: admin123)
INSERT INTO users (id, tenant_id, username, password_hash, name, role) VALUES
('user_admin', 'tenant_demo', 'admin', '$2b$10$YourHashedPasswordHere', '管理员', 'admin');
