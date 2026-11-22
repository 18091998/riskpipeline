from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests


class LLMClient:
    """Client for talking to a local Ollama server (or OpenAI-compatible endpoint)."""
    def __init__(
        self,
        model: str = "qwen2.5:1.5b",
        base_url: str = "http://localhost:11434/v1",
        api_key_env: str = "LLM_API_KEY",
        temperature: float = 0.2,
        timeout_seconds: int = 45,
        max_retries: int = 1,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "LLMClient":
        llm_cfg = config.get("model") or config.get("llm") or {}
        return cls(
            model=llm_cfg.get("name") or llm_cfg.get("model") or "qwen2.5:1.5b",
            base_url=llm_cfg.get("endpoint") or llm_cfg.get("base_url") or "http://localhost:11434/v1",
            api_key_env=llm_cfg.get("api_key_env", "LLM_API_KEY"),
            temperature=float(llm_cfg.get("temperature", 0.2)),
            timeout_seconds=int(llm_cfg.get("timeout_seconds", 45)),
            max_retries=int(llm_cfg.get("max_retries", 1)),
        )