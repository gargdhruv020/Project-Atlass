-- =====================================================================
-- Migration 002: Additive Analyst Escalation Tickets Table
-- Target Database: project_atlas (MySQL 8.0)
-- 
-- Safety Guarantee:
-- 1. 100% Additive: Does not alter or drop any existing tables (clients, reports, market_metrics).
-- 2. Preserves all existing records and relationships.
-- 3. Enables persistent analyst ticket logging with non-sensitive metadata tracking.
-- =====================================================================

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
  `updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_escalation_client` (`client_id`),
  INDEX `idx_escalation_status` (`status`),
  INDEX `idx_escalation_created` (`created_at`),
  CONSTRAINT `fk_escalation_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
