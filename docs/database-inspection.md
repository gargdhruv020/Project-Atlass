# Database Inspection Report: Project Atlas

- **Generated At**: 2026-10-18 15:09:32
- **Database Name**: `project_atlas`
- **MySQL Version**: `8.0.45`
- **Host**: `127.0.0.1:3306`
- **User**: `root`
- **Total Tables**: 7

## Summary of Tables & Row Counts

| Table Name | Row Count | Primary Key | Foreign Keys | Indexes |
| :--- | :--- | :--- | :--- | :--- |
| `clients` | 2 | `id` | 0 | 0 |
| `market_metrics` | 18 | `id` | 1 | 1 |
| `reports` | 3 | `id` | 0 | 0 |
| `escalation_tickets` | Dynamic | `id` | 1 | 4 |
| `conversations` | Dynamic | `id` | 1 | 1 |
| `chat_messages` | Dynamic | `id` | 2 | 2 |
| `message_feedback` | Dynamic | `id` | 2 | 2 |

---

## Detailed Table Specifications

### Table: `clients`
- **Row Count**: 2

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(10)` | NO | None | YES | NO |
| `company` | `VARCHAR(100)` | NO | None | NO | NO |
| `contact_email` | `VARCHAR(100)` | NO | None | NO | NO |
| `purchased_reports` | `TEXT` | NO | None | NO | NO |

#### Safe Sample Data (Masked)

```json
[
  {
    "id": "C-01",
    "company": "Northwind Utilities",
    "contact_email": "op***@example.com",
    "purchased_reports": "R-101, R-103"
  },
  {
    "id": "C-02",
    "company": "Blue Delta Infra",
    "contact_email": "pr***@example.com",
    "purchased_reports": "R-103"
  }
]
```

---

### Table: `market_metrics`
- **Row Count**: 18

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | NO | None | YES | YES |
| `report_id` | `VARCHAR(10)` | YES | None | NO | NO |
| `metric` | `VARCHAR(100)` | YES | None | NO | NO |
| `region` | `VARCHAR(100)` | YES | None | NO | NO |
| `period` | `VARCHAR(50)` | YES | None | NO | NO |
| `value` | `VARCHAR(50)` | YES | None | NO | NO |
| `scope_note` | `TEXT` | YES | None | NO | NO |

#### Foreign Keys / Relationships

| Constrained Columns | Referred Table | Referred Columns |
| :--- | :--- | :--- |
| `report_id` | `reports` | `id` |

#### Indexes

| Index Name | Column(s) | Unique |
| :--- | :--- | :--- |
| `report_id` | `report_id` | NO |

#### Safe Sample Data (Masked)

```json
[
  {
    "id": "1",
    "report_id": "R-101",
    "metric": "Market size",
    "region": "Global",
    "period": "2024",
    "value": "USD 4.21 B",
    "scope_note": "Includes hardware, software and services"
  },
  {
    "id": "2",
    "report_id": "R-101",
    "metric": "CAGR",
    "region": "Global",
    "period": "2025-2030",
    "value": "11.2%",
    "scope_note": "Forecast period stated as 2025-2030"
  }
]
```

---

### Table: `reports`
- **Row Count**: 3

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(10)` | NO | None | YES | NO |
| `title` | `VARCHAR(255)` | NO | None | NO | NO |
| `publisher` | `VARCHAR(100)` | NO | None | NO | NO |
| `published` | `DATE` | NO | None | NO | NO |
| `sector` | `VARCHAR(50)` | NO | None | NO | NO |
| `access` | `ENUM` | NO | None | NO | NO |

#### Safe Sample Data (Masked)

```json
[
  {
    "id": "R-101",
    "title": "Global Smart Water Meter Market 2025",
    "publisher": "CMR",
    "published": "2025-03-10",
    "sector": "Utilities",
    "access": "paid"
  },
  {
    "id": "R-102",
    "title": "Smart Water Metering: Industry Outlook 2024",
    "publisher": "Aquila Insights (third party)",
    "published": "2024-06-18",
    "sector": "Utilities",
    "access": "public"
  }
]
```

---

### Table: `escalation_tickets`
- **Description**: Stores analyst review tickets created when confidence falls below threshold, sources conflict, or calculations require human judgment.

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | NO | None | YES | YES |
| `ticket_id` | `VARCHAR(50)` | NO | None | NO | NO |
| `client_id` | `VARCHAR(10)` | NO | None | NO | NO |
| `query_text` | `TEXT` | NO | None | NO | NO |
| `reason` | `TEXT` | NO | None | NO | NO |
| `status` | `VARCHAR(30)` | NO | `'open'` | NO | NO |
| `priority` | `VARCHAR(20)` | NO | `'medium'` | NO | NO |
| `metadata_json` | `JSON` | YES | None | NO | NO |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | NO | NO |
| `updated_at` | `DATETIME` | YES | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | NO | NO |

#### Foreign Keys / Relationships

| Constrained Columns | Referred Table | Referred Columns | On Delete |
| :--- | :--- | :--- | :--- |
| `client_id` | `clients` | `id` | `CASCADE` |

#### Indexes

| Index Name | Column(s) | Unique |
| :--- | :--- | :--- |
| `ticket_id` | `ticket_id` | YES |
| `idx_escalation_client` | `client_id` | NO |
| `idx_escalation_status` | `status` | NO |
| `idx_escalation_created` | `created_at` | NO |

---

### Table: `conversations`
- **Description**: Multi-turn conversation sessions associated with authenticated clients.

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | None | YES | NO |
| `client_id` | `VARCHAR(10)` | NO | None | NO | NO |
| `title` | `VARCHAR(255)` | YES | `'New Conversation'` | NO | NO |
| `created_at` | `TIMESTAMP` | YES | `CURRENT_TIMESTAMP` | NO | NO |
| `updated_at` | `TIMESTAMP` | YES | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | NO | NO |

#### Foreign Keys / Relationships

| Constrained Columns | Referred Table | Referred Columns | On Delete |
| :--- | :--- | :--- | :--- |
| `client_id` | `clients` | `id` | `CASCADE` |

#### Indexes

| Index Name | Column(s) | Unique |
| :--- | :--- | :--- |
| `idx_conversation_client` | `client_id` | NO |

---

### Table: `chat_messages`
- **Description**: Stores individual user queries and assistant answers along with complete AI research metadata (citations, conflicts, derived values, confidence, escalation tickets).

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | NO | None | YES | YES |
| `conversation_id` | `VARCHAR(36)` | NO | None | NO | NO |
| `client_id` | `VARCHAR(10)` | NO | None | NO | NO |
| `sender` | `ENUM('user', 'assistant')` | NO | None | NO | NO |
| `content` | `MEDIUMTEXT` | NO | None | NO | NO |
| `citations` | `JSON` | YES | None | NO | NO |
| `conflicts` | `JSON` | YES | None | NO | NO |
| `derived_values` | `JSON` | YES | None | NO | NO |
| `confidence` | `FLOAT` | YES | None | NO | NO |
| `escalated` | `TINYINT(1)` | YES | `0` | NO | NO |
| `escalation_ticket` | `VARCHAR(50)` | YES | None | NO | NO |
| `created_at` | `TIMESTAMP` | YES | `CURRENT_TIMESTAMP` | NO | NO |

#### Foreign Keys / Relationships

| Constrained Columns | Referred Table | Referred Columns | On Delete |
| :--- | :--- | :--- | :--- |
| `conversation_id` | `conversations` | `id` | `CASCADE` |
| `client_id` | `clients` | `id` | `CASCADE` |

#### Indexes

| Index Name | Column(s) | Unique |
| :--- | :--- | :--- |
| `idx_message_conversation` | `conversation_id` | NO |
| `idx_message_client` | `client_id` | NO |

---

### Table: `message_feedback`
- **Description**: Stores thumbs-up / thumbs-down user ratings and optional feedback comments on assistant answers. Unique key `(message_id, client_id)` ensures idempotent repeated feedback handling (UPSERT).

#### Columns

| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | NO | None | YES | YES |
| `message_id` | `INTEGER` | NO | None | NO | NO |
| `conversation_id` | `VARCHAR(36)` | NO | None | NO | NO |
| `client_id` | `VARCHAR(10)` | NO | None | NO | NO |
| `rating` | `ENUM('thumbs_up', 'thumbs_down')` | NO | None | NO | NO |
| `comment` | `TEXT` | YES | None | NO | NO |
| `created_at` | `TIMESTAMP` | YES | `CURRENT_TIMESTAMP` | NO | NO |

#### Foreign Keys / Relationships

| Constrained Columns | Referred Table | Referred Columns | On Delete |
| :--- | :--- | :--- | :--- |
| `message_id` | `chat_messages` | `id` | `CASCADE` |
| `client_id` | `clients` | `id` | `CASCADE` |

#### Indexes

| Index Name | Column(s) | Unique |
| :--- | :--- | :--- |
| `uk_message_client_feedback` | `(message_id, client_id)` | YES |
| `idx_feedback_client` | `client_id` | NO |
