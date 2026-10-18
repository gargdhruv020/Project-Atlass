-- ==============================================================================
-- Project Atlas: Docker Compose MySQL Initialization Script
-- Used exclusively for fresh containerized review environments.
-- NEVER executed against existing host databases.
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `project_atlas` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `project_atlas`;

-- ------------------------------------------------------------------------------
-- 1. Table: clients
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `clients` (
    `id` VARCHAR(10) NOT NULL PRIMARY KEY,
    `company` VARCHAR(100) NOT NULL,
    `contact_email` VARCHAR(100) NOT NULL,
    `purchased_reports` TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `clients` (`id`, `company`, `contact_email`, `purchased_reports`) VALUES
('C-01', 'Northwind Utilities', 'operations@northwindutilities.example.com', 'R-101, R-103'),
('C-02', 'Blue Delta Infra', 'procurement@bluedeltainfra.example.com', 'R-103');

-- ------------------------------------------------------------------------------
-- 2. Table: reports
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `reports` (
    `id` VARCHAR(10) NOT NULL PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `publisher` VARCHAR(100) NOT NULL,
    `published` DATE NOT NULL,
    `sector` VARCHAR(50) NOT NULL,
    `access` ENUM('paid', 'public') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `reports` (`id`, `title`, `publisher`, `published`, `sector`, `access`) VALUES
('R-101', 'Global Smart Water Meter Market 2025', 'CMR', '2025-03-10', 'Utilities', 'paid'),
('R-102', 'Smart Water Metering: Industry Outlook 2024', 'Aquila Insights (third party)', '2024-06-18', 'Utilities', 'public'),
('R-103', 'Residential Water Purifier Market', 'AquaTech Analytics', '2025-01-15', 'Water Treatment', 'paid');

-- ------------------------------------------------------------------------------
-- 3. Table: market_metrics
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `market_metrics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `report_id` VARCHAR(10) NOT NULL,
    `metric` VARCHAR(100) NOT NULL,
    `region` VARCHAR(100) NOT NULL,
    `period` VARCHAR(50) NOT NULL,
    `value` VARCHAR(50) NOT NULL,
    `scope_note` TEXT,
    CONSTRAINT `fk_metric_report` FOREIGN KEY (`report_id`) REFERENCES `reports` (`id`) ON DELETE CASCADE,
    INDEX `idx_metric_report` (`report_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `market_metrics` (`id`, `report_id`, `metric`, `region`, `period`, `value`, `scope_note`) VALUES
(1, 'R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
(2, 'R-101', 'CAGR', 'Global', '2025-2030', '11.2%', 'Forecast period stated as 2025-2030'),
(3, 'R-101', 'Regional share', 'APAC', '2024', '38%', 'Share of global market size'),
(4, 'R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR/AMI hardware only'),
(5, 'R-102', 'CAGR', 'Global', '2024-2029', '9.8%', 'Different forecast window from R-101'),
(6, 'R-102', 'Regional share', 'APAC', '2024', '41%ch', 'Share of hardware market'),
(7, 'R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
(8, 'R-101', 'CAGR', 'Global', '2025-2030', '11.2%', 'Forecast period stated as 2025-2030'),
(9, 'R-101', 'Regional share', 'APAC', '2024', '38%', 'Share of global market size'),
(10, 'R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR/AMI hardware only'),
(11, 'R-102', 'CAGR', 'Global', '2024-2029', '9.8%', 'Different forecast window from R-101'),
(12, 'R-102', 'Regional share', 'APAC', '2024', '41%ch', 'Share of hardware market'),
(13, 'R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
(14, 'R-101', 'CAGR', 'Global', '2025-2030', '11.2%', 'Forecast period stated as 2025-2030'),
(15, 'R-101', 'Regional share', 'APAC', '2024', '38%', 'Share of global market size'),
(16, 'R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR/AMI hardware only'),
(17, 'R-102', 'CAGR', 'Global', '2024-2029', '9.8%', 'Different forecast window from R-101'),
(18, 'R-102', 'Regional share', 'APAC', '2024', '41%ch', 'Share of hardware market');

-- ------------------------------------------------------------------------------
-- 4. Table: escalation_tickets
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `escalation_tickets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ticket_id` VARCHAR(50) NOT NULL UNIQUE,
    `client_id` VARCHAR(10) NOT NULL,
    `query_text` TEXT NOT NULL,
    `reason` TEXT NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'open',
    `priority` VARCHAR(20) NOT NULL DEFAULT 'medium',
    `metadata_json` JSON DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_escalation_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
    INDEX `idx_escalation_client` (`client_id`),
    INDEX `idx_escalation_status` (`status`),
    INDEX `idx_escalation_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 5. Table: conversations
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conversations` (
    `id` VARCHAR(36) NOT NULL PRIMARY KEY,
    `client_id` VARCHAR(10) NOT NULL,
    `title` VARCHAR(255) DEFAULT 'New Conversation',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_conversation_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
    INDEX `idx_conversation_client` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 6. Table: chat_messages
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `conversation_id` VARCHAR(36) NOT NULL,
    `client_id` VARCHAR(10) NOT NULL,
    `sender` ENUM('user', 'assistant') NOT NULL,
    `content` MEDIUMTEXT NOT NULL,
    `citations` JSON DEFAULT NULL,
    `conflicts` JSON DEFAULT NULL,
    `derived_values` JSON DEFAULT NULL,
    `confidence` FLOAT DEFAULT NULL,
    `escalated` TINYINT(1) DEFAULT 0,
    `escalation_ticket` VARCHAR(50) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_message_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_message_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
    INDEX `idx_message_conversation` (`conversation_id`),
    INDEX `idx_message_client` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 7. Table: message_feedback
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `message_feedback` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `message_id` INT NOT NULL,
    `conversation_id` VARCHAR(36) NOT NULL,
    `client_id` VARCHAR(10) NOT NULL,
    `rating` ENUM('thumbs_up', 'thumbs_down') NOT NULL,
    `comment` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_feedback_message` FOREIGN KEY (`message_id`) REFERENCES `chat_messages` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_feedback_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
    INDEX `idx_feedback_client` (`client_id`),
    UNIQUE KEY `uk_message_client_feedback` (`message_id`, `client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 8. Restricted Read-Only User for Agent SQL Tool
-- ------------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'atlas_readonly'@'%' IDENTIFIED BY 'AtlasReadOnly2026!';
GRANT SELECT ON `project_atlas`.* TO 'atlas_readonly'@'%';
FLUSH PRIVILEGES;
