# backend/tests/test_memory_indexer.py
import tempfile
from pathlib import Path


def test_load_documents():
    from graph.memory_indexer import MemoryIndexer

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "memory").mkdir()
        (base / "memory" / "logs").mkdir()
        (base / "memory" / "MEMORY.md").write_text(
            "# Memory\n\n## Facts\n- Python is great\n- FastAPI rocks"
        )
        (base / "memory" / "logs" / "2026-02-19.md").write_text(
            "- User prefers dark mode\n"
        )
        (base / "knowledge").mkdir()
        (base / "knowledge" / "guide.md").write_text("# Guide\n\nUse Python 3.10+")
        (base / "storage").mkdir()

        indexer = MemoryIndexer(base_dir=td)
        docs = indexer._load_documents()
        assert len(docs) > 0
        sources = [d.metadata["source"] for d in docs]
        assert any("MEMORY.md" in s for s in sources)
        assert any("guide.md" in s for s in sources)


def test_build_bm25_index():
    from graph.memory_indexer import MemoryIndexer

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "memory").mkdir()
        (base / "memory" / "logs").mkdir()
        (base / "memory" / "MEMORY.md").write_text(
            "# Memory\n\n- Python programming language\n- FastAPI web framework"
        )
        (base / "knowledge").mkdir()
        (base / "storage").mkdir()

        indexer = MemoryIndexer(base_dir=td, embeddings=None)
        retriever = indexer.build_index()
        assert retriever is not None
        # Test retrieval
        results = retriever.invoke("Python")
        assert len(results) > 0


def test_empty_knowledge():
    from graph.memory_indexer import MemoryIndexer

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "memory").mkdir()
        (base / "memory" / "logs").mkdir()
        (base / "memory" / "MEMORY.md").write_text("")
        (base / "knowledge").mkdir()
        (base / "storage").mkdir()

        indexer = MemoryIndexer(base_dir=td)
        result = indexer.build_index()
        assert result is None
