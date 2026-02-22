"""
LLM provider factory: load config and create provider-specific clients.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class LLMFactoryError(Exception):
    """Raised when LLM factory configuration or creation fails."""


@dataclass
class ProviderConfig:
    """Provider configuration from YAML."""

    name: str
    type: str
    model: str
    params: Dict[str, Any]


DEFAULT_PROVIDERS_PATH = "llm/providers.yaml"


def load_providers_config(path: str = DEFAULT_PROVIDERS_PATH) -> Dict[str, Any]:
    """Load and validate providers YAML config."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"providers.yaml not found: {cfg_path}")

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LLMFactoryError("Invalid providers.yaml: root must be a mapping")

    if "providers" not in data or not isinstance(data["providers"], dict):
        raise LLMFactoryError("Invalid providers.yaml: missing 'providers' mapping")

    if "default" not in data:
        raise LLMFactoryError("Invalid providers.yaml: missing 'default' provider key")

    return data


def get_provider_config(
    provider_name: Optional[str] = None,
    path: str = DEFAULT_PROVIDERS_PATH,
) -> ProviderConfig:
    """Get provider config by name or default."""
    data = load_providers_config(path=path)

    default_name = data["default"]
    providers: Dict[str, Any] = data["providers"]

    name = provider_name or default_name
    if name not in providers:
        raise LLMFactoryError(
            f"Provider '{name}' not found. Available: {list(providers.keys())}"
        )

    p = providers[name]
    if not isinstance(p, dict):
        raise LLMFactoryError(f"Provider '{name}' config must be a mapping")

    p_type = str(p.get("type", "")).strip()
    model = str(p.get("model", "")).strip()
    if not p_type:
        raise LLMFactoryError(f"Provider '{name}' missing required field: type")
    if not model:
        raise LLMFactoryError(f"Provider '{name}' missing required field: model")

    params = dict(p)
    params.pop("type", None)
    params.pop("model", None)

    return ProviderConfig(name=name, type=p_type, model=model, params=params)


# ---------------------------------------------------------------------------
# Provider clients (thin adapters)
# ---------------------------------------------------------------------------


class BaseLLMClient:
    """Base interface for LLM clients."""

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    """OpenAI chat completions adapter."""

    def __init__(self, api_key: str, model: str, **params: Any) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMFactoryError(
                "OpenAI SDK not installed. Install with: pip install openai"
            ) from e

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._params = params

    def generate(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": prompt}],
            temperature=self._params.get("temperature", 0.2),
            max_tokens=self._params.get("max_tokens"),
        )
        return resp.choices[0].message.content or ""


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude adapter."""

    def __init__(self, api_key: str, model: str, **params: Any) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise LLMFactoryError(
                "Anthropic SDK not installed. Install with: pip install anthropic"
            ) from e

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._params = params

    def generate(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._params.get("max_output_tokens", 1024),
            temperature=self._params.get("temperature", 0.2),
            messages=[{"role": "user", "content": prompt}],
        )
        parts = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()


class GeminiClient(BaseLLMClient):
    """Google Gemini adapter."""

    def __init__(self, api_key: str, model: str, **params: Any) -> None:
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise LLMFactoryError(
                "Gemini SDK not installed. Install with: pip install google-generativeai"
            ) from e

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._params = params

    def generate(self, prompt: str) -> str:
        generation_config = {
            "temperature": self._params.get("temperature", 0.2),
            "max_output_tokens": self._params.get("max_output_tokens", 1024),
        }
        resp = self._model.generate_content(prompt, generation_config=generation_config)
        return (resp.text or "").strip()


def create_llm_client(
    provider_name: Optional[str] = None,
    providers_path: str = DEFAULT_PROVIDERS_PATH,
    *,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> BaseLLMClient:
    """Create LLM client from provider config. Secrets must come from env, not YAML."""
    cfg = get_provider_config(provider_name=provider_name, path=providers_path)

    p_type = cfg.type.lower().strip()

    if p_type == "openai":
        if not openai_api_key:
            raise LLMFactoryError("Missing openai_api_key (load from env)")
        return OpenAIClient(api_key=openai_api_key, model=cfg.model, **cfg.params)

    if p_type in ("anthropic", "claude"):
        if not anthropic_api_key:
            raise LLMFactoryError("Missing anthropic_api_key (load from env)")
        return AnthropicClient(api_key=anthropic_api_key, model=cfg.model, **cfg.params)

    if p_type in ("gemini", "google"):
        if not gemini_api_key:
            raise LLMFactoryError("Missing gemini_api_key (load from env)")
        return GeminiClient(api_key=gemini_api_key, model=cfg.model, **cfg.params)

    raise LLMFactoryError(
        f"Unsupported provider type: '{cfg.type}'. "
        "Supported: openai, anthropic, gemini"
    )
