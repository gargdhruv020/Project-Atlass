"""
Project Atlas - Database Inspection Script
Connects to the existing MySQL database 'project-atlas' in read-only mode,
retrieves schema details, table structures, indexes, foreign keys, row counts,
and safe sample records (masking sensitive fields), then generates docs/database-inspection.md.
"""

import os
import sys
import urllib.parse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "project-atlas")

# Sensitive column name patterns to mask
SENSITIVE_PATTERNS = {
    "password", "secret", "token", "hash", "key", "credential",
    "auth", "pwd", "ssn", "credit_card", "card", "cvv", "salt"
}
CONTACT_PATTERNS = {"email", "phone", "mobile", "contact", "address"}

def mask_value(col_name: str, value):
    """Mask sensitive or confidential data."""
    if value is None:
        return "NULL"
    val_str = str(value)
    col_lower = col_name.lower()
    
    for pat in SENSITIVE_PATTERNS:
        if pat in col_lower:
            return "******** [MASKED]"
            
    for pat in CONTACT_PATTERNS:
        if pat in col_lower:
            if "@" in val_str:
                parts = val_str.split("@")
                masked_user = parts[0][:2] + "***" if len(parts[0]) > 2 else "***"
                return f"{masked_user}@{parts[1]}"
            elif len(val_str) > 4:
                return val_str[:2] + "****" + val_str[-2:]
            return "**** [MASKED]"
            
    return val_str

def get_engine():
    """Create SQLAlchemy engine using pymysql with encoded credentials."""
    if not DB_PASSWORD:
        print("[WARNING] DB_PASSWORD is empty in .env. Attempting connection without password.")
        
    encoded_user = urllib.parse.quote_plus(DB_USER)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    url = f"mysql+pymysql://{encoded_user}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)

def inspect_database():
    """Perform read-only inspection of the database."""
    print(f"Connecting to MySQL database '{DB_NAME}' at {DB_HOST}:{DB_PORT} as user '{DB_USER}'...")
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Basic version and db info
            db_res = conn.execute(text("SELECT DATABASE();")).scalar()
            version_res = conn.execute(text("SELECT VERSION();")).scalar()
            
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        view_names = inspector.get_view_names()
        
        print("\n" + "=" * 60)
        print("DATABASE CONNECTION SUCCESSFUL")
        print("=" * 60)
        print(f"Database Name : {db_res}")
        print(f"MySQL Version : {version_res}")
        print(f"Total Tables  : {len(table_names)}")
        if view_names:
            print(f"Total Views   : {len(view_names)}")
        print("=" * 60)
        
        tables_data = []
        
        with engine.connect() as conn:
            for table in table_names:
                # Row count
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`;")).scalar()
                except Exception as e:
                    count = f"Error: {e}"
                
                # Columns
                columns = inspector.get_columns(table)
                pk_constraint = inspector.get_pk_constraint(table)
                pks = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
                
                # Foreign keys
                fks = inspector.get_foreign_keys(table)
                
                # Indexes
                indexes = inspector.get_indexes(table)
                
                # Safe sample data (LIMIT 2)
                samples = []
                try:
                    sample_query = text(f"SELECT * FROM `{table}` LIMIT 2;")
                    result = conn.execute(sample_query)
                    keys = result.keys()
                    for row in result.fetchall():
                        masked_row = {k: mask_value(k, getattr(row, k, None) if hasattr(row, k) else row._mapping[k]) for k in keys}
                        samples.append(masked_row)
                except Exception as e:
                    samples = [{"error": f"Could not fetch sample: {e}"}]
                
                tables_data.append({
                    "name": table,
                    "row_count": count,
                    "columns": columns,
                    "primary_keys": pks,
                    "foreign_keys": fks,
                    "indexes": indexes,
                    "samples": samples
                })
        
        # Display summary to console
        print("\nTABLES AND ROW COUNTS:")
        for td in tables_data:
            print(f" - {td['name']}: {td['row_count']} rows")
            
        # Write Markdown Report
        docs_dir = BASE_DIR / "docs"
        docs_dir.mkdir(exist_ok=True)
        report_path = docs_dir / "database-inspection.md"
        
        write_markdown_report(report_path, db_res, version_res, tables_data, view_names)
        print(f"\nInspection report saved successfully to: {report_path.relative_to(BASE_DIR)}")
        return True, tables_data
        
    except SQLAlchemyError as e:
        print("\n" + "!" * 60)
        print("DATABASE CONNECTION FAILED")
        print("!" * 60)
        print(f"Error Details: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify MySQL server is currently running.")
        print(f"2. Check host ({DB_HOST}) and port ({DB_PORT}).")
        print(f"3. Confirm username ({DB_USER}) and password in .env are correct.")
        print(f"4. Confirm database '{DB_NAME}' exists and the user has SELECT privileges.")
        print("!" * 60)
        return False, None

def write_markdown_report(report_path: Path, db_name: str, version: str, tables_data: list, view_names: list):
    """Generate detailed markdown documentation of the inspected database."""
    lines = [
        "# Database Inspection Report: Project Atlas",
        "",
        f"- **Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Database Name**: `{db_name}`",
        f"- **MySQL Version**: `{version}`",
        f"- **Host**: `{DB_HOST}:{DB_PORT}`",
        f"- **User**: `{DB_USER}`",
        f"- **Total Tables**: {len(tables_data)}",
        "",
        "## Summary of Tables & Row Counts",
        "",
        "| Table Name | Row Count | Primary Key | Foreign Keys | Indexes |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for t in tables_data:
        pk_str = ", ".join(f"`{k}`" for k in t["primary_keys"]) if t["primary_keys"] else "None"
        fk_count = len(t["foreign_keys"])
        idx_count = len(t["indexes"])
        lines.append(f"| `{t['name']}` | {t['row_count']} | {pk_str} | {fk_count} | {idx_count} |")
        
    if view_names:
        lines.extend([
            "",
            "## Views",
            ""
        ])
        for v in view_names:
            lines.append(f"- `{v}`")

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Table Specifications",
        ""
    ])
    
    for t in tables_data:
        lines.extend([
            f"### Table: `{t['name']}`",
            f"- **Row Count**: {t['row_count']}",
            "",
            "#### Columns",
            "",
            "| Column Name | Type | Nullable | Default | Primary Key | Auto Increment |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ])
        for col in t["columns"]:
            name = col["name"]
            col_type = str(col["type"])
            nullable = "YES" if col.get("nullable") else "NO"
            default = str(col.get("default", "")) if col.get("default") is not None else "None"
            is_pk = "YES" if name in t["primary_keys"] else "NO"
            is_ai = "YES" if col.get("autoincrement") else "NO"
            lines.append(f"| `{name}` | `{col_type}` | {nullable} | {default} | {is_pk} | {is_ai} |")
            
        if t["foreign_keys"]:
            lines.extend([
                "",
                "#### Foreign Keys / Relationships",
                "",
                "| Constrained Columns | Referred Table | Referred Columns |",
                "| :--- | :--- | :--- |"
            ])
            for fk in t["foreign_keys"]:
                c_cols = ", ".join(fk.get("constrained_columns", []))
                r_tbl = fk.get("referred_table", "")
                r_cols = ", ".join(fk.get("referred_columns", []))
                lines.append(f"| `{c_cols}` | `{r_tbl}` | `{r_cols}` |")
                
        if t["indexes"]:
            lines.extend([
                "",
                "#### Indexes",
                "",
                "| Index Name | Column(s) | Unique |",
                "| :--- | :--- | :--- |"
            ])
            for idx in t["indexes"]:
                idx_name = idx.get("name")
                cols = ", ".join(idx.get("column_names", []))
                unique = "YES" if idx.get("unique") else "NO"
                lines.append(f"| `{idx_name}` | `{cols}` | {unique} |")
                
        if t["samples"]:
            lines.extend([
                "",
                "#### Safe Sample Data (Masked)",
                "",
                "```json",
                __import__("json").dumps(t["samples"], indent=2, default=str),
                "```",
                ""
            ])
            
        lines.append("---")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    success, _ = inspect_database()
    sys.exit(0 if success else 1)
