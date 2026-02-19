"""Provider base types."""

from dataclasses import dataclass, field


@dataclass
class ProviderSpec:
    name: str
    llm_class: str
    env_key: str | None
    display_name: str
    default_model: str
    supports_embedding: bool = False
    embedding_class: str | None = None
    api_base_default: str = ""
    manages_own_base: bool = False  # True = SDK handles endpoint internally, don't pass base_url
    api_key_alias: str = ""  # Non-standard kwarg name for API key (e.g. "zhipuai_api_key")
    extra_init_kwargs: dict = field(default_factory=dict)
