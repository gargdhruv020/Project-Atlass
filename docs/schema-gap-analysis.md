# Project Atlas &mdash; Database Schema Gap Analysis & Migration Plan

**Date**: 2026-10-18  
**Database**: `project_atlas`  
**MySQL Server**: MySQL 8.0.45  
**Host**: `127.0.0.1:3306`

---

## 1. Executive Summary

This document performs an exhaustive, non-destructive audit of the existing `project_atlas` MySQL database against the full relational requirements of the **Project Atlas AI Copilot**.

The current database contains 3 core tables (`clients`, `reports`, and `market_metrics`) representing foundational market intelligence and client entitlements. However, several critical requirements necessary for an interactive AI copilot &mdash; including conversational session management, feedback tracking, analyst escalation workflows, and security audit logging &mdash; are currently missing.

All findings below are based on direct read-only inspection without altering any existing schemas or data.

---

## 2. Current Schema & Table Definitions

### 2.1 Table: `reports`
Stores market research reports and public/paid entitlement levels.

```sql
CREATE TABLE `reports` (
  `id` varchar(10) NOT NULL,
  `title` varchar(255) NOT NULL,
  `publisher` varchar(100) NOT NULL,
  `published` date NOT NULL,
  `sector` varchar(50) NOT NULL,
  `access` enum('paid','public') NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Actual Records (3 rows)**:
| `id` | `title` | `publisher` | `published` | `sector` | `access` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `R-101` | Global Smart Water Meter Market 2025 | CMR | 2025-03-10 | Utilities | paid |
| `R-102` | Smart Water Metering: Industry Outlook 2024 | Aquila Insights (third party) | 2024-06-18 | Utilities | public |
| `R-103` | Residential Water Purifier Market | CMR | 2025-01-22 | Consumer Durables | paid |

---

### 2.2 Table: `clients`
Stores client profile information and purchased report entitlements.

```sql
CREATE TABLE `clients` (
  `id` varchar(10) NOT NULL,
  `company` varchar(100) NOT NULL,
  `contact_email` varchar(100) NOT NULL,
  `purchased_reports` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Actual Records (2 rows)**:
| `id` | `company` | `contact_email` | `purchased_reports` |
| :--- | :--- | :--- | :--- |
| `C-01` | Northwind Utilities | ops@example.com | `R-101, R-103` |
| `C-02` | Blue Delta Infra | procurement@example.com | `R-103` |

---

### 2.3 Table: `market_metrics`
Stores granular, structured research metrics extracted from market reports.

```sql
CREATE TABLE `market_metrics` (
  `id` int NOT NULL AUTO_INCREMENT,
  `report_id` varchar(10) DEFAULT NULL,
  `metric` varchar(100) DEFAULT NULL,
  `region` varchar(100) DEFAULT NULL,
  `period` varchar(50) DEFAULT NULL,
  `value` varchar(50) DEFAULT NULL,
  `scope_note` text,
  PRIMARY KEY (`id`),
  KEY `report_id` (`report_id`),
  CONSTRAINT `market_metrics_ibfk_1` FOREIGN KEY (`report_id`) REFERENCES `reports` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Actual Records (24 rows)**:
The table currently contains 24 rows consisting of 6 unique metric tuples repeated 4 times (IDs 1-6, 7-12, 13-18, 19-24):
1. `R-101` | Market size | Global | 2024 | `USD 4.21 B` | Includes hardware, software and services
2. `R-101` | CAGR | Global | 2025-2030 | `11.2%` | Forecast period stated as 2025-2030
3. `R-101` | Regional share | APAC | 2024 | `38%` | Share of global market size
4. `R-102` | Market size | Global | 2024 | `USD 3.87 B` | AMR/AMI hardware only
5. `R-102` | CAGR | Global | 2024-2029 | `9.8%` | Different forecast window from R-101
6. `R-102` | Regional share | APAC | 2024 | `41%ch` | Share of hardware market *(Note: typo '41%ch' in source value)*

---

## 3. Data Integrity & Consistency Verification

### 3.1 Verification of Seed Entities
* **Seed Clients (`C-01`, `C-02`)**: Both exist in the database.
* **Seed Reports (`R-101`, `R-102`, `R-103`)**: All three exist in the database.
* **Preservation Notice**: No seed insert scripts should be run; running them would create duplicate primary key conflicts or duplicate metrics.

### 3.2 Consistency of Report IDs and Client Purchases
* In `clients`, purchases are stored as a comma-separated string (`'R-101, R-103'` and `'R-103'`).
* **Validation**:
  * `C-01` purchases `R-101` (exists, `paid`) and `R-103` (exists, `paid`). &check;
  * `C-02` purchases `R-103` (exists, `paid`). &check;
  * `R-102` is `public`, so any client has implicit access. &check;
  * Zero dangling foreign keys exist between `market_metrics.report_id` and `reports.id`. &check;

### 3.3 Identified Schema & Data Quirks
1. **Denormalized Entitlements**: `clients.purchased_reports` uses a comma-delimited `TEXT` string. While functional for the legacy CodeIgniter portal, it cannot enforce foreign key constraints, index lookups, or purchase timestamps.
2. **Duplicate Records in `market_metrics`**: 6 distinct metric rows have been inserted 4 times (total 24 rows).
3. **Data Type / Content Quirks**:
   * `market_metrics.value` is `VARCHAR(50)` storing formatted strings (`USD 4.21 B`, `11.2%`, `41%ch`).
   * Row 6 (and its copies 12, 18, 24) contains the string `'41%ch'`, indicating a typographical suffix.
   * Report `R-103` currently has **0 records** in `market_metrics`.

---

## 4. Requirements Gap Analysis Matrix

| Requirement | Current Status | Existing Schema Location | Gaps & Deficiencies |
| :--- | :--- | :--- | :--- |
| **Market reports & metadata** | **Implemented** | `reports` table | Missing timestamps (`created_at`, `updated_at`), summary/abstract column, and document file path. |
| **Clients** | **Implemented** | `clients` table | Missing account timestamps (`created_at`), status (`is_active`), and auth token/secret fields. |
| **Client-to-report purchases / entitlements** | **Partially Implemented** | `clients.purchased_reports` (TEXT) | Denormalized (violates 1NF). Lacks purchase timestamps (`purchased_at`), expiration dates, and relational foreign keys. |
| **Analyst escalation tickets** | **MISSING** | None | No table exists to track escalation requests, analyst notes, ticket status, or assignment. |
| **Chat conversations and messages** | **MISSING** | None | No tables exist to store conversation sessions, message history, timestamps, or retrieval citations. |
| **Thumbs-up & thumbs-down feedback** | **MISSING** | None | No table exists to collect user ratings, feedback comments, or evaluation markers on AI responses. |
| **Request logs / audit records** | **MISSING** | None | No table exists to track API queries, response latency, client access checks, or authorization failures. |

---

## 5. Proposed Additive SQL Migration Plan

> [!IMPORTANT]
> **Safety Guarantee**: This migration plan is **100% additive**. It:
> 1. Does not drop or alter any existing tables.
> 2. Does not delete, modify, or truncate existing records.
> 3. Preserves `clients.purchased_reports` intact so existing CodeIgniter 3 queries continue functioning without disruption.
> 4. Adds normalized junction tables, conversational history, ticketing, and logging with strict foreign key constraints.

---

### Step 1: Additive Performance Indexes & Audit Columns (Optional / Non-breaking)
Add performance indexes to improve query speeds on existing tables.

```sql
-- Migration 01: Additive performance indexes
ALTER TABLE `reports` 
  ADD INDEX `idx_reports_sector` (`sector`),
  ADD INDEX `idx_reports_access` (`access`);

ALTER TABLE `market_metrics` 
  ADD INDEX `idx_metrics_lookup` (`report_id`, `metric`(50));
```

---

### Step 2: Normalized Client Entitlements Table (`client_entitlements`)
Creates a relational junction table between `clients` and `reports` for robust permission checks and purchase timestamps, while keeping `clients.purchased_reports` intact for backward compatibility.

```sql
-- Migration 02: Client Entitlements
CREATE TABLE IF NOT EXISTS `client_entitlements` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `client_id` VARCHAR(10) NOT NULL,
  `report_id` VARCHAR(10) NOT NULL,
  `purchased_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `expires_at` TIMESTAMP NULL DEFAULT NULL,
  `status` ENUM('active', 'expired', 'revoked') DEFAULT 'active',
  UNIQUE KEY `uk_client_report` (`client_id`, `report_id`),
  INDEX `idx_entitlement_client` (`client_id`),
  INDEX `idx_entitlement_report` (`report_id`),
  CONSTRAINT `fk_entitlement_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_entitlement_report` FOREIGN KEY (`report_id`) REFERENCES `reports` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Backfill entitlements from existing clients.purchased_reports safely (idempotent):
INSERT IGNORE INTO `client_entitlements` (`client_id`, `report_id`)
VALUES 
  ('C-01', 'R-101'),
  ('C-01', 'R-103'),
  ('C-02', 'R-103');
```

---

### Step 3: Chat Conversations & Messages (`conversations`, `chat_messages`)
Enables multi-turn conversational memory, citation tracking, and session organization.

```sql
-- Migration 03: Conversations and Chat Messages
CREATE TABLE IF NOT EXISTS `conversations` (
  `id` VARCHAR(36) PRIMARY KEY,
  `client_id` VARCHAR(10) NOT NULL,
  `title` VARCHAR(255) DEFAULT 'New Conversation',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_conversation_client` (`client_id`),
  CONSTRAINT `fk_conversation_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `conversation_id` VARCHAR(36) NOT NULL,
  `sender` ENUM('user', 'assistant', 'system') NOT NULL,
  `content` MEDIUMTEXT NOT NULL,
  `citations` JSON DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_message_conversation` (`conversation_id`),
  CONSTRAINT `fk_message_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

### Step 4: Message Feedback Table (`message_feedback`)
Enables users to provide thumbs-up/thumbs-down ratings and comments on AI responses.

```sql
-- Migration 04: User Feedback
CREATE TABLE IF NOT EXISTS `message_feedback` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `message_id` INT NOT NULL,
  `client_id` VARCHAR(10) NOT NULL,
  `rating` ENUM('thumbs_up', 'thumbs_down') NOT NULL,
  `comment` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_message_client_feedback` (`message_id`, `client_id`),
  INDEX `idx_feedback_client` (`client_id`),
  CONSTRAINT `fk_feedback_message` FOREIGN KEY (`message_id`) REFERENCES `chat_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_feedback_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

### Step 5: Analyst Escalation Tickets Table (`analyst_tickets`)
Enables routing unanswered or complex research queries to human market analysts.

```sql
-- Migration 05: Analyst Escalation Tickets
CREATE TABLE IF NOT EXISTS `analyst_tickets` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `ticket_number` VARCHAR(20) NOT NULL UNIQUE,
  `client_id` VARCHAR(10) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `report_id` VARCHAR(10) DEFAULT NULL,
  `query_text` TEXT NOT NULL,
  `status` ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
  `priority` ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
  `assigned_analyst` VARCHAR(100) DEFAULT NULL,
  `analyst_response` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` TIMESTAMP NULL DEFAULT NULL,
  INDEX `idx_ticket_client` (`client_id`),
  INDEX `idx_ticket_status` (`status`),
  CONSTRAINT `fk_ticket_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ticket_report` FOREIGN KEY (`report_id`) REFERENCES `reports` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_ticket_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

### Step 6: Security & API Request Audit Logs (`audit_logs`)
Records API usage, access authorization decisions, latency, and client interactions.

```sql
-- Migration 06: Request & Audit Logs
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `client_id` VARCHAR(10) DEFAULT NULL,
  `endpoint` VARCHAR(255) NOT NULL,
  `method` VARCHAR(10) NOT NULL,
  `status_code` INT NOT NULL,
  `access_granted` TINYINT(1) DEFAULT 1,
  `latency_ms` INT DEFAULT NULL,
  `ip_address` VARCHAR(45) DEFAULT NULL,
  `details` JSON DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_audit_client` (`client_id`),
  INDEX `idx_audit_created` (`created_at`),
  CONSTRAINT `fk_audit_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

## 6. Optional Clean-up (Requires Explicit Approval)

> [!CAUTION]
> **Optional Deduplication of `market_metrics`**:
> Currently, `market_metrics` contains 24 rows (4 sets of identical 6 metric rows).
> If you wish to deduplicate this table in the future so that only unique metrics remain (reducing it to 6 rows), the following query can be used:
> ```sql
> -- DO NOT EXECUTE WITHOUT APPROVAL
> DELETE m1 FROM market_metrics m1
> INNER JOIN market_metrics m2 
> WHERE m1.id > m2.id 
>   AND m1.report_id = m2.report_id 
>   AND m1.metric = m2.metric 
>   AND m1.region = m2.region 
>   AND m1.period = m2.period;
> ```
> **Per safety requirements, this cleanup will NOT be executed unless explicitly requested.**
