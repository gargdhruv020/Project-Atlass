"""
Project Atlas - Report Ingestion CLI Script
Scans documents directory, processes PDF, HTML, and Markdown files,
extracts metadata, validates required fields, chunks documents,
and synchronizes with local persistent ChromaDB.
"""

import sys
import json
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.core.config import settings
from app.ingestion.pipeline import ReportIngestionPipeline
from app.observability.logger import logger

def main():
    docs_dir = Path(settings.DOCUMENTS_DIR) / "sample_reports"
    if not docs_dir.exists():
        docs_dir = Path(settings.DOCUMENTS_DIR)

    print("=" * 70)
    print("PROJECT ATLAS - REPORT INGESTION PIPELINE")
    print("=" * 70)
    print(f"Target Directory: {docs_dir.resolve()}")
    print(f"ChromaDB Path   : {settings.CHROMA_PERSIST_DIRECTORY}")
    print("=" * 70)

    pipeline = ReportIngestionPipeline(chunk_size=400, chunk_overlap=40)
    summary = pipeline.execute_pipeline(docs_dir, load_to_chroma=True)

    summary_dict = summary.to_dict()

    print("\nINGESTION SUMMARY:")
    print(f"- Total Reports Discovered : {summary_dict['total_reports_discovered']}")
    print(f"- Total Reports Processed  : {summary_dict['total_reports_processed']}")
    print(f"- Total Chunks Created     : {summary_dict['total_chunks_created']}")
    print(f"- Extraction Errors        : {len(summary_dict['extraction_errors'])}")
    print(f"- Missing Metadata Warnings: {len(summary_dict['missing_metadata_warnings'])}")

    print("\nPROCESSED REPORTS:")
    for r in summary_dict["processed_reports"]:
        print(f"  • [{r['report_id']}] {r['title']} ({r['file_name']}) - {r['chunks_count']} chunk(s) | Sector: {r['sector']} | Region: {r['region']}")

    if summary_dict["missing_metadata_warnings"]:
        print("\nMISSING METADATA WARNINGS:")
        for w in summary_dict["missing_metadata_warnings"]:
            print(f"  ⚠ {w['file_name']} (Report: {w['report_id']}) missing: {w['missing_fields']}")

    if summary_dict["extraction_errors"]:
        print("\nEXTRACTION ERRORS:")
        for e in summary_dict["extraction_errors"]:
            print(f"  ✖ {e['file_name']}: {e['error']}")

    print("\n" + "=" * 70)
    print("Ingestion Pipeline Execution Completed Successfully.")
    print("=" * 70)

    # Save summary report to docs/
    report_file = BASE_DIR / "docs" / "ingestion-summary.json"
    report_file.write_text(json.dumps(summary_dict, indent=2), encoding="utf-8")
    print(f"Summary JSON saved to: {report_file.relative_to(BASE_DIR)}")

if __name__ == "__main__":
    main()
