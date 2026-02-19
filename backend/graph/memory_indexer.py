# backend/graph/memory_indexer.py
"""Hybrid retrieval indexer — Milvus (vector) + BM25 (keyword) via EnsembleRetriever."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _import_ensemble_retriever():
    """Import EnsembleRetriever directly from its module file.

    Works around a version-mismatch issue where ``langchain.retrievers.__init__``
    tries to import ``langchain_core.memory`` (removed in langchain-core >= 1.0).
    By loading ``ensemble.py`` via *importlib* we skip the broken ``__init__``.
    """
    mod_name = "langchain.retrievers.ensemble"
    if mod_name in sys.modules:
        return sys.modules[mod_name].EnsembleRetriever

    # Attempt a normal import first (works when versions are aligned).
    try:
        from langchain.retrievers.ensemble import EnsembleRetriever  # noqa: WPS433

        return EnsembleRetriever
    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback: load the file directly via importlib spec.
    origin = Path(importlib.util.find_spec("langchain").origin).parent / "retrievers" / "ensemble.py"
    if not origin.exists():
        raise ImportError("Cannot locate langchain/retrievers/ensemble.py")

    spec = importlib.util.spec_from_file_location(mod_name, str(origin))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod.EnsembleRetriever


class MemoryIndexer:
    """Manages hybrid retrieval over memory and knowledge files."""

    def __init__(
        self,
        base_dir: str | Path,
        embeddings=None,
        storage_dir: str | Path | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.embeddings = embeddings
        self.storage_dir = Path(storage_dir) if storage_dir else self.base_dir / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=256,
            chunk_overlap=32,
            separators=["\n## ", "\n### ", "\n- ", "\n", " "],
        )
        self._retriever = None

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def _load_documents(self) -> list[Document]:
        """Load all indexable documents from memory and knowledge directories."""
        docs: list[Document] = []

        # Load MEMORY.md
        memory_path = self.base_dir / "memory" / "MEMORY.md"
        if memory_path.is_file():
            content = memory_path.read_text(encoding="utf-8")
            if content.strip():
                docs.extend(
                    self.splitter.create_documents(
                        [content],
                        metadatas=[{"source": "memory/MEMORY.md"}],
                    )
                )

        # Load daily logs
        logs_dir = self.base_dir / "memory" / "logs"
        if logs_dir.is_dir():
            for log_file in sorted(logs_dir.glob("*.md")):
                content = log_file.read_text(encoding="utf-8")
                if content.strip():
                    docs.extend(
                        self.splitter.create_documents(
                            [content],
                            metadatas=[{"source": f"memory/logs/{log_file.name}"}],
                        )
                    )

        # Load knowledge directory
        knowledge_dir = self.base_dir / "knowledge"
        if knowledge_dir.is_dir():
            for f in sorted(knowledge_dir.glob("**/*")):
                if f.is_file() and f.suffix in (".md", ".txt", ".json"):
                    content = f.read_text(encoding="utf-8")
                    if content.strip():
                        rel = f.relative_to(knowledge_dir)
                        docs.extend(
                            self.splitter.create_documents(
                                [content],
                                metadatas=[{"source": f"knowledge/{rel}"}],
                            )
                        )

        return docs

    # ------------------------------------------------------------------
    # Index building
    # ------------------------------------------------------------------

    def build_index(self) -> Any:
        """Build or rebuild the hybrid retriever."""
        docs = self._load_documents()
        if not docs:
            self._retriever = None
            return None

        # Try to build vector + BM25 hybrid retriever
        try:
            return self._build_hybrid_retriever(docs)
        except Exception:
            # Fall back to BM25 only if vector store fails
            return self._build_bm25_only(docs)

    def _build_hybrid_retriever(self, docs: list[Document]) -> Any:
        """Build EnsembleRetriever with Milvus + BM25."""
        if not self.embeddings:
            return self._build_bm25_only(docs)

        from langchain_milvus import Milvus

        db_path = str(self.storage_dir / "milvus_memory.db")
        vector_store = Milvus.from_documents(
            docs,
            self.embeddings,
            connection_args={"uri": db_path},
            collection_name="memory",
            drop_old=True,
        )
        vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3})

        from langchain_community.retrievers import BM25Retriever

        bm25_retriever = BM25Retriever.from_documents(docs, k=3)

        EnsembleRetriever = _import_ensemble_retriever()
        self._retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.7, 0.3],
        )
        return self._retriever

    def _build_bm25_only(self, docs: list[Document]) -> Any:
        """Fallback: BM25 only retriever."""
        from langchain_community.retrievers import BM25Retriever

        self._retriever = BM25Retriever.from_documents(docs, k=3)
        return self._retriever

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def retriever(self):
        return self._retriever
