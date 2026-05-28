"""Configuration loading from TOML."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelConfig:
    """One model entry in the bench."""

    id: str
    display_name: str
    ollama_tag: str
    notes: str = ""


@dataclass
class BenchConfig:
    """Top-level bench configuration."""

    ollama_base_url: str
    models: list[ModelConfig]

    @classmethod
    def load(cls, path: str | Path = "config.toml") -> BenchConfig:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        if "ollama" not in data or "base_url" not in data["ollama"]:
            raise ValueError("config missing [ollama] base_url")
        if "models" not in data or not data["models"]:
            raise ValueError("config has no [[models]] entries")
        return cls(
            ollama_base_url=data["ollama"]["base_url"],
            models=[ModelConfig(**m) for m in data["models"]],
        )
