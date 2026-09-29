"""Configuration loading for LEXAI.

Two concerns live here:
1. LLM connection settings, read from environment variables.
2. Integration declarations, read from integrations.yaml.

YAML is parsed with PyYAML when installed; otherwise a small stdlib
fallback handles the subset LEXAI's config needs (nested mappings,
scalars, and inline/block string lists). The fallback keeps LEXAI's
runtime dependencies at zero.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigError(Exception):
    """Raised when LEXAI cannot determine how to run itself.

    The CLI catches this and prints the message directly, so messages
    here are user-facing: keep them clear and actionable.
    """


@dataclass(frozen=True)
class BrainConfig:
    """Connection settings for the OpenAI-compatible chat backend."""

    api_base: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "BrainConfig":
        env = dict(os.environ) if env is None else env
        missing = [
            name
            for name in ("LEXAI_API_BASE", "LEXAI_API_KEY", "LEXAI_MODEL")
            if not env.get(name, "").strip()
        ]
        if missing:
            raise ConfigError(
                "LEXAI is missing required environment variables: "
                + ", ".join(missing)
                + "\n\nSet them before starting, for example:\n"
                "  export LEXAI_API_BASE=https://api.openai.com/v1\n"
                "  export LEXAI_API_KEY=sk-...\n"
                "  export LEXAI_MODEL=gpt-4o-mini\n\n"
                "Any OpenAI-compatible endpoint works (OpenAI, Groq, "
                "OpenRouter, Ollama, LM Studio, ...). You can also put "
                "them in a .env file next to the project."
            )
        return cls(
            api_base=env["LEXAI_API_BASE"].strip().rstrip("/"),
            api_key=env["LEXAI_API_KEY"].strip(),
            model=env["LEXAI_MODEL"].strip(),
        )


def _parse_scalar(text: str) -> Any:
    stripped = text.strip()
    if stripped in ("null", "~", ""):
        return None
    if stripped == "{}":
        return {}
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ("'", '"'):
        return stripped[1:-1]
    if stripped.startswith("["):
        if not stripped.endswith("]"):
            raise ConfigError(f"unclosed list value: {stripped!r}")
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    if stripped in ("true", "True"):
        return True
    if stripped in ("false", "False"):
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return stripped


def _parse_simple_yaml(text: str) -> Any:
    """Minimal YAML subset parser: mappings, scalars, block/inline lists.

    Raises ConfigError on anything it cannot handle, so the caller can
    tell the user the file needs PyYAML or a simpler structure.
    """
    lines = [
        (index, line)
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return {}
    base_indent = len(lines[0][1]) - len(lines[0][1].lstrip(" "))
    if base_indent != 0:
        raise ConfigError("integrations.yaml: top level must not be indented")
    return _parse_block([(text, n) for n, text in lines], indent=0)[0]


def _parse_block(lines: List[tuple], indent: int) -> tuple:
    """Parse consecutive lines at `indent` into a dict or list.

    Each line is a (content, line_number) pair. Returns (value, index)
    where index is the number of lines consumed.
    """
    first = lines[0][0].lstrip()
    if first.startswith("- "):
        items: List[Any] = []
        pos = 0
        while pos < len(lines):
            content, lineno = lines[pos]
            pad = len(content) - len(content.lstrip(" "))
            if pad < indent or not content.lstrip().startswith("- "):
                break
            if pad != indent:
                raise ConfigError(f"integrations.yaml line {lineno}: bad indentation")
            items.append(_parse_scalar(content.lstrip()[2:]))
            pos += 1
        return items, pos

    result: Dict[str, Any] = {}
    pos = 0
    while pos < len(lines):
        content, lineno = lines[pos]
        pad = len(content) - len(content.lstrip(" "))
        if pad < indent:
            break
        if pad != indent:
            raise ConfigError(f"integrations.yaml line {lineno}: bad indentation")
        stripped = content.strip()
        if ":" not in stripped:
            raise ConfigError(f"integrations.yaml line {lineno}: expected 'key: value'")
        key, _, raw = stripped.partition(":")
        key = key.strip().strip("'\"")
        raw = raw.strip()
        pos += 1
        if raw:
            result[key] = _parse_scalar(raw)
        elif pos < len(lines):
            # Nested block: its indent is whatever the next line actually uses.
            nxt, nxt_lineno = lines[pos]
            nxt_indent = len(nxt) - len(nxt.lstrip(" "))
            if nxt_indent > indent:
                result[key], consumed = _parse_block(lines[pos:], nxt_indent)
                pos += consumed
                continue
            result[key] = None
        else:
            result[key] = None
    return result, pos





def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_simple_yaml(text)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"integrations.yaml is not valid YAML: {exc}") from exc


@dataclass(frozen=True)
class IntegrationsConfig:
    """Parsed contents of integrations.yaml.

    `entries` maps integration name -> its raw config mapping. No
    integration code runs from here by itself; the registry decides
    which declared integrations are actually activated.
    """

    entries: Dict[str, Dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "IntegrationsConfig":
        if not path.exists():
            return cls(entries={})
        data = _load_yaml(path.read_text(encoding="utf-8"))
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigError("integrations.yaml must contain a mapping at the top level")
        raw = data.get("integrations")
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ConfigError(
                "'integrations' in integrations.yaml must be a mapping of name -> config"
            )
        entries = {}
        for name, value in raw.items():
            if value is None:
                value = {}
            if not isinstance(value, dict):
                raise ConfigError(
                    f"Integration '{name}' must map to a config mapping (or be empty)"
                )
            entries[str(name)] = value
        return cls(entries=entries)


def load_integrations_config(project_root: Optional[Path] = None) -> IntegrationsConfig:
    root = Path(project_root) if project_root else _project_root()
    return IntegrationsConfig.load(root / "integrations.yaml")


def _project_root() -> Path:
    """Project root is the nearest ancestor containing integrations.yaml, else cwd."""
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "integrations.yaml").exists():
            return candidate
    return cwd