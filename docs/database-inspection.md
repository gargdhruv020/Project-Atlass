# Database Inspection Report: Project Atlas

- **Generated At**: 2026-10-18 15:09:32
- **Database Name**: `project_atlas`
- **MySQL Version**: `8.0.45`
- **Host**: `127.0.0.1:3306`
- **User**: `root`
- **Total Tables**: 3

## Summary of Tables & Row Counts

| Table Name | Row Count | Primary Key | Foreign Keys | Indexes |
| :--- | :--- | :--- | :--- | :--- |
| `clients` | 2 | `id` | 0 | 0 |
| `market_metrics` | 18 | `id` | 1 | 1 |
| `reports` | 3 | `id` | 0 | 0 |

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
