"""Pluggable "brain" for LEXAI.

The brain is what turns conversation history into a reply. The default
implementation talks to any OpenAI-compatible chat completions API
(OpenAI, Groq, OpenRouter, Together, local Ollama/LM Studio, ...),
configured purely through environment variables. Swap in a different
Brain subclass to change how LEXAI thinks without touching the CLI.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Optional

from .config import BrainConfig, ConfigError

SYSTEM_PROMPT = (
    "You are LEXAI, a personal AI assistant. You are helpful, direct, and "
    "conversational. Keep answers focused; offer to take action when it "
    "makes sense."
)


class Brain(ABC):
    """Anything that can produce assistant replies from a message history."""

    @abstractmethod
    def reply(self, history: List[dict]) -> str:
        """Given [{'role': ..., 'content': ...}, ...], return the assistant text."""

    def reset(self) -> None:
        """Called when the user clears the conversation. Optional hook."""


class OpenAICompatBrain(Brain):
    """Calls an OpenAI-compatible /chat/completions endpoint.

    Only the Python standard library is used for transport, so LEXAI has
    no hard dependency on any provider SDK and no provider is hardcoded.
    """

    def __init__(self, config: BrainConfig, system_prompt: str = SYSTEM_PROMPT, timeout: float = 120.0):
        self.config = config
        self.system_prompt = system_prompt
        self.timeout = timeout

    def _messages(self, history: List[dict]) -> List[dict]:
        return [{"role": "system", "content": self.system_prompt}, *history]

    def reply(self, history: List[dict]) -> str:
        payload = {
            "model": self.config.model,
            "messages": self._messages(history),
        }
        url = f"{self.config.api_base}/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise ConfigError(
                f"The chat API returned HTTP {exc.code} from {url}. "
                f"Check LEXAI_API_KEY and LEXAI_MODEL. Details: {detail or 'no body'}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ConfigError(
                f"Could not reach the chat API at {url}: {exc.reason}. "
                "Check LEXAI_API_BASE and your network connection."
            ) from exc
        except TimeoutError as exc:
            raise ConfigError(f"The chat API at {url} timed out.") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ConfigError(
                f"The chat API returned an unexpected response shape: {json.dumps(body)[:500]}"
            ) from None
        if not isinstance(content, str):
            raise ConfigError("The chat API returned a non-text message content.")
        return content.strip()