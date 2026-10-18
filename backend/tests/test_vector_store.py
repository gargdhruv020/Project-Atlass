"""
Vector Store Service Unit & Security Tests
Tests insertion, semantic retrieval, metadata preservation, deduplication,
persistence across restarts, and MySQL client entitlement security boundaries.
"""

from pathlib import Path
import pytest
from app.retrieval.vector_store import VectorStoreService
from app.ingestion.document_parser import DocumentChunk

@pytest.fixture
def temp_chroma_service(tmp_path):
    """Fixture providing a temporary, isolated VectorStoreService instance."""
    persist_dir = tmp_path / "chroma_test_data"
    service = VectorStoreService(
        persist_dir=str(persist_dir),
        collection_name="test_market_reports"
    )
    return service

def test_chunk_insertion_and_count(temp_chroma_service):
    """Verify chunks can be inserted into ChromaDB and count is accurate."""
    chunks = [
        DocumentChunk(
            chunk_id="R-TEST_p1_c0_abc123",
            content="Ultrasonic smart water meters demonstrate high dynamic range.",
            metadata={"report_id": "R-TEST", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
        ),
        DocumentChunk(
            chunk_id="R-TEST_p1_c1_def456",
            content="Cellular NB-IoT battery lifetime exceeds 10 years in typical operations.",
            metadata={"report_id": "R-TEST", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
        )
    ]
    upserted = temp_chroma_service.add_or_update_chunks(chunks)
    assert upserted == 2
    assert temp_chroma_service.count() == 2

def test_semantic_retrieval_and_metadata_preservation(temp_chroma_service):
    """Verify semantic similarity search returns matched content and all required metadata."""
    chunks = [
        DocumentChunk(
            chunk_id="R-101_p1_c0_aaa",
            content="Water metering telemetry architecture and leak analytics.",
            metadata={"report_id": "R-101", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
        ),
        DocumentChunk(
            chunk_id="R-104_p1_c0_bbb",
            content="Commercial building HVAC chillers and rooftop heat pump systems.",
            metadata={"report_id": "R-104", "sector": "Building Infrastructure", "region": "North America", "year": "2025", "page": 1}
        )
    ]
    temp_chroma_service.add_or_update_chunks(chunks)

    # Search for water metering
    results = temp_chroma_service.similarity_search("leak analytics in municipal water systems", n_results=1)
    assert len(results) == 1
    top_result = results[0]
    assert "Water metering" in top_result["content"]

    # Verify all required metadata fields are preserved
    meta = top_result["metadata"]
    assert meta["report_id"] == "R-101"
    assert meta["sector"] == "Utilities"
    assert meta["region"] == "Global"
    assert meta["year"] == "2025"
    assert meta["page"] == 1

def test_metadata_filtering(temp_chroma_service):
    """Verify similarity search respects where metadata filters."""
    chunks = [
        DocumentChunk(
            chunk_id="R-101_p1_c0",
            content="Energy consumption monitoring in utilities sector.",
            metadata={"report_id": "R-101", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
        ),
        DocumentChunk(
            chunk_id="R-104_p1_c0",
            content="Energy consumption monitoring in commercial buildings.",
            metadata={"report_id": "R-104", "sector": "Building Infrastructure", "region": "North America", "year": "2025", "page": 1}
        )
    ]
    temp_chroma_service.add_or_update_chunks(chunks)

    filtered_res = temp_chroma_service.similarity_search(
        query="energy monitoring",
        n_results=5,
        where={"sector": "Building Infrastructure"}
    )
    assert len(filtered_res) == 1
    assert filtered_res[0]["metadata"]["report_id"] == "R-104"

def test_deduplication_and_idempotency(temp_chroma_service):
    """Verify repeated insertion with stable chunk IDs does not create duplicates."""
    chunk = DocumentChunk(
        chunk_id="R-101_p1_c0_stable",
        content="Unique market research narrative text.",
        metadata={"report_id": "R-101", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
    )

    # First insertion
    temp_chroma_service.add_or_update_chunks([chunk])
    assert temp_chroma_service.count() == 1

    # Second insertion of identical chunk
    temp_chroma_service.add_or_update_chunks([chunk])
    assert temp_chroma_service.count() == 1

def test_persistence_across_service_restarts(tmp_path):
    """Verify chunks persist on disk and are available when a new service client initializes."""
    persist_dir = tmp_path / "persistent_chroma"

    # Client 1: write chunk and shutdown
    service_1 = VectorStoreService(persist_dir=str(persist_dir), collection_name="persist_test")
    service_1.add_or_update_chunks([
        DocumentChunk(
            chunk_id="R-PERSIST_01",
            content="Persistent test text surviving restart.",
            metadata={"report_id": "R-PERSIST", "sector": "Energy", "region": "Global", "year": "2025", "page": 1}
        )
    ])
    assert service_1.count() == 1
    del service_1

    # Client 2: re-open same directory
    service_2 = VectorStoreService(persist_dir=str(persist_dir), collection_name="persist_test")
    assert service_2.count() == 1
    chunk = service_2.get_chunk_by_id("R-PERSIST_01")
    assert chunk is not None
    assert "Persistent test text" in chunk["content"]

def test_security_entitled_similarity_search(temp_chroma_service, db):
    """
    CRITICAL SECURITY TEST:
    Verify that ChromaDB vector search enforces client purchase entitlements via MySQL.
    - C-01 owns R-101 and R-103 (+ public R-102).
    - C-02 owns R-103 (+ public R-102) BUT NOT R-101.
    - C-02 must NEVER receive content from R-101.
    """
    chunks = [
        DocumentChunk(
            chunk_id="R-101_secure_01",
            content="Proprietary paid research findings for Smart Water Meters.",
            metadata={"report_id": "R-101", "sector": "Utilities", "region": "Global", "year": "2025", "page": 1}
        ),
        DocumentChunk(
            chunk_id="R-102_public_01",
            content="Public utility industry outlook and AMR overview.",
            metadata={"report_id": "R-102", "sector": "Utilities", "region": "Global", "year": "2024", "page": 1}
        ),
        DocumentChunk(
            chunk_id="R-103_secure_01",
            content="Residential water purifier filtration study.",
            metadata={"report_id": "R-103", "sector": "Consumer Durables", "region": "Global", "year": "2025", "page": 1}
        )
    ]
    temp_chroma_service.add_or_update_chunks(chunks)

    # 1. Client C-01 queries water meters (has purchased R-101)
    results_c01 = temp_chroma_service.entitled_similarity_search(
        db=db,
        client_id="C-01",
        query="smart water meters",
        n_results=3
    )
    c01_report_ids = [r["metadata"]["report_id"] for r in results_c01]
    assert "R-101" in c01_report_ids

    # 2. Client C-02 queries water meters (HAS NOT purchased R-101)
    results_c02 = temp_chroma_service.entitled_similarity_search(
        db=db,
        client_id="C-02",
        query="smart water meters",
        n_results=3
    )
    c02_report_ids = [r["metadata"]["report_id"] for r in results_c02]
    # R-101 MUST be absent from C-02 results
    assert "R-101" not in c02_report_ids
    # But public report R-102 or purchased R-103 may be present
    for rep in c02_report_ids:
        assert rep in ["R-102", "R-103"]

def test_collection_health_status(temp_chroma_service):
    """Verify health check returns diagnostic statistics without leaking credentials."""
    status = temp_chroma_service.get_health_status()
    assert status["status"] == "available"
    assert "total_chunks" in status
    assert "Ollama" in status["embedding_model"]
