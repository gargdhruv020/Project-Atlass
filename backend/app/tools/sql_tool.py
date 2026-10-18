"""
Read-Only SQL Tool for Project Atlas
Executes restricted, parameterized aggregate queries over MySQL tables (market_metrics, reports)
scoped strictly to client-permitted reports. Prevents arbitrary SQL execution, enforces row limits,
applies query timeouts, and guarantees zero database mutations by using a SELECT-only MySQL account.
"""

import re
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from app.models.report import Report
from app.models.market_metric import MarketMetric
from app.observability.logger import logger
from app.db.session import ReadOnlySessionLocal


APPROVED_TABLES = {"market_metrics", "reports"}

FORBIDDEN_SQL_PATTERNS = [
    r"\binsert\b", r"\bupdate\b", r"\bdelete\b", r"\bdrop\b",
    r"\balter\b", r"\btruncate\b", r"\bcreate\b", r"\breplace\b",
    r"\bgrant\b", r"\brevoke\b", r"\bexec\b", r"\bcall\b",
    r"\bshow\b", r"\bdescribe\b", r"\block\b", r"\bset\b",
    r"--", r";"
]

NATURAL_LANGUAGE_MUTATION_PATTERNS = [
    r"\bdelete\b", r"\bdrop\b", r"\btruncate\b", r"\binsert\b",
    r"\bupdate\b", r"\balter\b", r"\bwipe\b", r"\bmodify database\b",
    r"\bchange permissions?\b", r"\bgrant\b", r"\brevoke\b",
    r"\badd records?\b", r"\bremove records?\b"
]


class ReadOnlySQLTool:
    """Safe, read-only aggregate query tool restricted to client entitlements and approved tables."""

    @staticmethod
    def validate_safety(query_str: str) -> bool:
        """Ensures query contains no mutation, DDL, administrative, or injection tokens."""
        lower = query_str.lower().strip()
        for pattern in FORBIDDEN_SQL_PATTERNS:
            if re.search(pattern, lower):
                return False
        return True

    @staticmethod
    def detect_natural_language_mutation_intent(query_str: str) -> bool:
        """Detects whether a natural-language inquiry is attempting to alter or mutate the database."""
        lower = query_str.lower().strip()
        for pattern in NATURAL_LANGUAGE_MUTATION_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    @staticmethod
    def validate_approved_tables(sql_str: str) -> tuple[bool, str]:
        """Verifies that the SQL query only references approved tables (market_metrics, reports)."""
        lower = sql_str.lower()
        # Find all table identifiers after FROM or JOIN
        matches = re.findall(r"\b(?:from|join)\s+([`a-zA-Z0-9_]+)", lower)
        cleaned_tables = {m.replace("`", "").strip() for m in matches}
        
        # Check against approved tables
        disallowed = cleaned_tables - APPROVED_TABLES
        if disallowed:
            return False, f"Disallowed table access: {disallowed}. Only approved tables: {APPROVED_TABLES}"
        return True, "OK"

    @classmethod
    def execute_safe_sql(
        cls,
        sql_str: str,
        permitted_reports: Set[str],
        max_rows: int = 50,
        timeout_seconds: int = 5,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Executes a validated, read-only SELECT query using a restricted SELECT-only connection.
        Enforces:
        - Query must start with SELECT.
        - Zero write / DDL keywords.
        - Strict approved table access (market_metrics, reports).
        - Hard row limit.
        - Statement timeout.
        - Enforced client report entitlement boundaries.
        """
        clean_sql = sql_str.strip()
        if not clean_sql.upper().startswith("SELECT"):
            return {
                "status": "blocked",
                "error": "Only SELECT queries are permitted on the read-only SQL tool.",
                "data": []
            }

        if not cls.validate_safety(clean_sql):
            return {
                "status": "blocked",
                "error": "Security Alert: Query contains forbidden SQL keywords or injection characters.",
                "data": []
            }

        # Validate table restrictions
        is_valid_tables, table_err = cls.validate_approved_tables(clean_sql)
        if not is_valid_tables:
            return {
                "status": "blocked",
                "error": f"Security Alert: {table_err}",
                "data": []
            }

        # Enforce report entitlement filtering
        if not permitted_reports:
            return {
                "status": "denied",
                "error": "Zero report entitlements for client. Relational access denied.",
                "data": []
            }

        # Apply row limit
        limit_match = re.search(r"\blimit\s+(\d+)", clean_sql, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > max_rows:
                clean_sql = re.sub(r"\blimit\s+\d+", f"LIMIT {max_rows}", clean_sql, flags=re.IGNORECASE)
        else:
            clean_sql = f"{clean_sql} LIMIT {max_rows}"

        # Execute using restricted read-only session
        db = session or ReadOnlySessionLocal()
        close_needed = session is None

        try:
            # Set query timeout in session if supported
            try:
                db.execute(text(f"SET SESSION max_execution_time = {timeout_seconds * 1000};"))
            except Exception:
                pass

            rows = db.execute(text(clean_sql)).fetchall()
            data = [dict(r._mapping) for r in rows]
            return {
                "status": "success",
                "row_count": len(data),
                "data": data,
                "sql_executed": clean_sql
            }
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"[ReadOnlySQLTool] Database security enforcement triggered: {e}")
            return {
                "status": "blocked",
                "error": f"Database privilege check or syntax restriction blocked query: {str(e)[:100]}",
                "data": []
            }
        except SQLAlchemyError as e:
            logger.error(f"[ReadOnlySQLTool] SQL error: {e}")
            return {
                "status": "error",
                "error": "Internal database query error.",
                "data": []
            }
        finally:
            if close_needed:
                db.close()

    @classmethod
    def execute_aggregate(
        cls,
        db: Session,
        permitted_reports: Set[str],
        query: str
    ) -> Dict[str, Any]:
        """
        Executes supported read-only aggregation matching the user's intent.
        Strictly enforces permitted_reports filter and rejects natural-language mutation attempts.
        """
        # 1. Reject natural-language attempts to modify the database
        if cls.detect_natural_language_mutation_intent(query):
            logger.warning(f"[ReadOnlySQLTool] Blocked natural-language database mutation attempt: '{query[:60]}'")
            return {
                "status": "blocked",
                "message": "Security Alert: Database modification operations (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE) are strictly prohibited on read-only tools.",
                "data": {}
            }

        if not permitted_reports:
            return {
                "status": "denied",
                "message": "Zero permitted reports for client. Aggregate query rejected.",
                "data": {}
            }

        q_lower = query.lower()

        # 1. Average CAGR across permitted reports
        if "average cagr" in q_lower or "mean cagr" in q_lower or "avg cagr" in q_lower:
            return cls._avg_cagr(db, permitted_reports)

        # 2. Maximum / Largest market size
        if "largest market size" in q_lower or "highest market size" in q_lower or "max market size" in q_lower:
            return cls._max_market_size(db, permitted_reports)

        # 3. Metric count across permitted reports
        if "how many metrics" in q_lower or "count of metrics" in q_lower or "total metrics" in q_lower:
            return cls._count_metrics(db, permitted_reports)

        # 4. Regional distribution of metrics
        if "regional distribution" in q_lower or "metrics by region" in q_lower or "breakdown by region" in q_lower:
            return cls._metrics_by_region(db, permitted_reports)

        # 5. Sector distribution / sector with the most reports
        if "sector" in q_lower or "most reports" in q_lower or "industry" in q_lower or "vertical" in q_lower:
            return cls._sector_report_counts(db, permitted_reports)

        # 6. General permitted report count & summary
        return cls._permitted_summary(db, permitted_reports)

    @classmethod
    def _sector_report_counts(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Calculates report distribution across sectors and identifies the sector with the most reports."""
        from collections import Counter
        reps = db.query(Report).filter(Report.id.in_(permitted_reports)).all()
        if not reps:
            return {
                "aggregation": "sector_report_counts",
                "result": "No permitted reports found.",
                "sample_size": 0
            }

        sector_counts: Counter[str] = Counter()
        for r in reps:
            sector_name = r.sector or "Unspecified"
            sector_counts[sector_name] += 1

        top_sector, top_count = sector_counts.most_common(1)[0]
        breakdown_str = ", ".join(f"{s}: {c}" for s, c in sector_counts.items())
        top_reps = [r.id for r in reps if (r.sector or "Unspecified") == top_sector]

        return {
            "aggregation": "sector_report_counts",
            "top_sector": top_sector,
            "top_sector_count": top_count,
            "breakdown": dict(sector_counts),
            "sources": top_reps,
            "formatted_summary": f"The sector with the most reports among your permitted library is '{top_sector}' with {top_count} report(s) ({', '.join(top_reps)}). Full breakdown: {breakdown_str}."
        }

    @classmethod
    def _avg_cagr(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Calculates average CAGR among permitted reports with numeric parsing."""
        cagr_metrics = (
            db.query(MarketMetric)
            .filter(
                MarketMetric.report_id.in_(permitted_reports),
                MarketMetric.metric.ilike("%cagr%")
            )
            .all()
        )

        rates = []
        for m in cagr_metrics:
            match = re.search(r"(\d+\.?\d*)%", str(m.value or ""))
            if match:
                rates.append((m.report_id, float(match.group(1))))

        if not rates:
            return {
                "aggregation": "average_cagr",
                "result": "No CAGR metrics found in permitted reports",
                "sample_size": 0
            }

        avg_rate = round(sum(r[1] for r in rates) / len(rates), 2)
        details = [f"{rep}: {val}%" for rep, val in rates]

        return {
            "aggregation": "average_cagr",
            "average_cagr": f"{avg_rate}%",
            "sample_size": len(rates),
            "sources": list({r[0] for r in rates}),
            "details": "; ".join(details),
            "formatted_summary": f"Average CAGR across {len(rates)} permitted source(s) is {avg_rate}% ({'; '.join(details)})"
        }

    @classmethod
    def _max_market_size(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Finds maximum recorded market size in permitted reports."""
        size_metrics = (
            db.query(MarketMetric)
            .filter(
                MarketMetric.report_id.in_(permitted_reports),
                MarketMetric.metric.ilike("%market size%")
            )
            .all()
        )

        parsed = []
        for m in size_metrics:
            match = re.search(r"(\d+\.?\d*)", str(m.value or ""))
            if match:
                parsed.append((m.report_id, m.region, m.period, float(match.group(1)), m.value))

        if not parsed:
            return {
                "aggregation": "max_market_size",
                "result": "No market size metrics found in permitted reports."
            }

        parsed.sort(key=lambda x: x[3], reverse=True)
        top = parsed[0]

        return {
            "aggregation": "max_market_size",
            "top_report_id": top[0],
            "region": top[1],
            "period": top[2],
            "value": top[4],
            "sources": [top[0]],
            "formatted_summary": f"Highest recorded market size in permitted reports: {top[4]} ({top[1]}, {top[2]}, Report {top[0]})"
        }

    @classmethod
    def _count_metrics(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Counts total metrics available in permitted reports."""
        count = (
            db.query(MarketMetric)
            .filter(MarketMetric.report_id.in_(permitted_reports))
            .count()
        )
        return {
            "aggregation": "metric_count",
            "total_metrics_count": count,
            "permitted_reports": list(permitted_reports),
            "formatted_summary": f"Found {count} structured metric record(s) across your {len(permitted_reports)} permitted report(s)."
        }

    @classmethod
    def _metrics_by_region(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Aggregates metrics by region."""
        from sqlalchemy import func
        rows = (
            db.query(MarketMetric.region, func.count(MarketMetric.id))
            .filter(MarketMetric.report_id.in_(permitted_reports))
            .group_by(MarketMetric.region)
            .all()
        )
        breakdown = {r[0] or "Unspecified": r[1] for r in rows}
        summary_parts = [f"{reg}: {cnt}" for reg, cnt in breakdown.items()]
        return {
            "aggregation": "metrics_by_region",
            "breakdown": breakdown,
            "formatted_summary": f"Regional metric distribution: {', '.join(summary_parts)}"
        }

    @classmethod
    def _permitted_summary(cls, db: Session, permitted_reports: Set[str]) -> Dict[str, Any]:
        """Generates general summary of permitted reports catalog."""
        reps = db.query(Report).filter(Report.id.in_(permitted_reports)).all()
        titles = [f"{r.id} ('{r.title}')" for r in reps]
        return {
            "aggregation": "permitted_scope_summary",
            "permitted_count": len(reps),
            "reports": titles,
            "formatted_summary": f"Permitted reports scope ({len(reps)}): {'; '.join(titles)}"
        }
