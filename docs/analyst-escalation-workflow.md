# Project Atlas &mdash; Analyst Escalation Workflow

## 1. Overview & Architecture

Project Atlas implements an automated **Analyst Escalation Workflow** that detects when research inquiries exceed automated certainty bounds and smoothly transitions callers to human subject-matter experts.

The workflow integrates:
- **Authoritative MySQL Storage**: Persists tickets in `escalation_tickets` with non-sensitive audit metadata.
- **Configurable Confidence Gate**: Governed by `ESCALATION_CONFIDENCE_THRESHOLD` (default: `0.70`).
- **Explainability Contract**: Articulates **What was verified**, **What remains uncertain**, and **Analyst follow-up**.
- **Security & Integrity**: Reuses duplicate open tickets and strictly avoids fabricating ticket IDs if database operations fail.

---

## 2. Escalation Triggers

The workflow escalates when:
1. **Low Confidence Score**: Retrieval or evidence confidence score falls below `ESCALATION_CONFIDENCE_THRESHOLD` (0.70).
2. **Unvalidated Material Numerical Claims**: Critical numerical figures, out-of-catalog report IDs, or out-of-bound pages are detected and excised.
3. **Material Source Conflicts Requiring Judgment**: Authorized reports (e.g., R-101 $4.21B vs R-102 $3.87B) materially diverge and the caller demands a single resolved choice or asks "which is correct".
4. **Unresolved Calculation Assumptions**: Projections exceed published forecast horizons (e.g., querying beyond 2030 for R-101 or 2029 for R-102) without verified empirical data.
5. **Missing Evidence / Out-of-Catalog Topics**: Inquiries requesting topics completely absent from the client's entitled research corpus.
6. **Backend Service Failures**: System errors or connectivity interruptions during evidence retrieval.

> [!NOTE]
> Standard factual lookups grounded in authorized evidence do not escalate unnecessarily and return structured answers with high confidence ($\ge 0.90$).

---

## 3. Database Schema & Migration Specification

### 3.1 Proposed Additive Migration: `escalation_tickets`

The migration is defined in [`scripts/migrations/002_create_escalation_tickets.sql`](../scripts/migrations/002_create_escalation_tickets.sql). It is **100% additive** and preserves all existing database records without altering `clients`, `reports`, or `market_metrics`.

```sql
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
```

### 3.2 Tracked Metadata Fields

The `metadata_json` column stores non-sensitive telemetry:
- `confidence_score`: float
- `target_report_id`: string
- `intent`: string (e.g., `comparison`, `calculation_projection`)
- `conflict_count`: integer
- `metrics_found`: integer
- `escalation_reason`: string

*Sensitive tokens, passwords, raw chunks, and unauthorized text are strictly stripped prior to storage.*

---

## 4. Response Behavior & Formatting

When escalation triggers, the response contains:
- `escalated`: `true`
- `escalation_ticket`: String identifier (e.g. `"ESC-0001"`) or `null` if database operation failed.
- `answer`: Structured into three explicit components:
  1. **What was verified**: Clear citation of partial metrics or facts confirmed from authorized reports.
  2. **What remains uncertain**: Specific rationale for escalation (e.g. scope divergence, forecast window extrapolation, or data deficit).
  3. **Analyst Follow-Up**: Assurance that a senior market research analyst has been assigned.

### Example Escalated Response:

```json
{
  "answer": "Methodological Conflict Notice: Authorized reports provide differing figures for this inquiry.\n\n**What was verified:** Both figures were verified against authorized sources: Report R-101 reports USD 4.21 B (Full System), while Report R-102 reports USD 3.87 B (Hardware endpoints only).\n\n**What remains uncertain:** Neither figure is solely correct, and the system will not silently average them or select one without methodological justification.\n\n**Analyst Follow-Up:** A senior market research analyst will review your inquiry to provide scope reconciliation. Your escalation ticket reference is **ESC-0004**.",
  "citations": [...],
  "confidence": 0.60,
  "conflicts": [...],
  "derived_values": {},
  "escalated": true,
  "client_id": "C-01",
  "conversation_id": null,
  "escalation_ticket": "ESC-0004"
}
```

---

## 5. Duplicate Submission & Graceful Failure Handling

1. **Duplicate Suppression**: If a client re-submits an inquiry matching an existing open ticket, `EscalationService` detects the open ticket and reuses the existing `ticket_id` rather than inserting redundant rows into MySQL.
2. **Database Failure Resilience**: If MySQL is unreachable or fails to persist a record, `EscalationService` catches the exception and returns `ticket_id: None`. The response informs the client that an analyst will review the inquiry manually, and `escalation_ticket` is set to `null` without fabricating fictitious ticket numbers.

---

## 6. Authorized API Endpoints

### `GET /escalations`
Retrieves tickets from MySQL with mandatory authentication and optional filtering.

- **Headers**: `X-API-Key: atlas-dev-key-2026`
- **Query Parameters**:
  - `client_id`: (optional) Filters tickets for a verified client. Rejects nonexistent clients with `404 Not Found`.
  - `status`: (optional) Filters by `'open'`, `'resolved'`, etc.
  - `skip` / `limit`: Pagination controls.
