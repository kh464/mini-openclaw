import json
import tempfile
from pathlib import Path


def test_config_defaults():
    from config import AppConfig
    cfg = AppConfig()
    assert cfg.agent_engine == "langgraph"
    assert cfg.memory_backend == "native"
    assert cfg.vector_store == "milvus"
    assert cfg.rag_mode is False
    assert cfg.llm.provider == "zhipu"
    assert cfg.llm.model == "glm-4.7-flash"
    assert cfg.embedding.provider == "siliconflow"
    assert cfg.embedding.model == "BAAI/bge-m3"


def test_config_save_and_load():
    from config import AppConfig, load_config, save_config

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        cfg = AppConfig()
        cfg.rag_mode = True
        save_config(cfg, path)

        loaded = load_config(path)
        assert loaded.rag_mode is True
        assert loaded.llm.provider == "zhipu"


def test_config_partial_update():
    from config import AppConfig, load_config, save_config

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        # Write partial config
        path.write_text(json.dumps({"agent_engine": "raw_loop"}))
        loaded = load_config(path)
        assert loaded.agent_engine == "raw_loop"
        # Defaults preserved
        assert loaded.llm.model == "glm-4.7-flash"
