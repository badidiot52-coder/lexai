"""LEXAI CLI: an interactive chat loop over a pluggable brain."""

from __future__ import annotations

import sys
from typing import List, Optional

from .brain import Brain, OpenAICompatBrain, SYSTEM_PROMPT
from .config import BrainConfig, ConfigError, load_integrations_config
from .integrations import get_registry

BANNER = r"""
  _  _____  __
 | || _\ \/ /
 | ||  _>  <
 |___|/_/\_\  v0.1
LEXAI: your personal AI assistant
Type /help for commands.
"""

HELP_TEXT = """Commands:
  /help          show this help
  /clear         reset the conversation
  /status        show brain model and active integrations
  /quit (or /exit, Ctrl+D)  leave"""


class Session:
    """Holds conversation state and wires brain + integrations together."""

    def __init__(self, brain: Brain):
        self.brain = brain
        self.history: List[dict] = []

    def send(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        reply = self.brain.reply(self.history)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def clear(self) -> None:
        self.history = []
        self.brain.reset()


def _integration_status() -> str:
    registry = get_registry()
    config = load_integrations_config()
    declared = config.entries.keys()
    if not declared:
        return "no integrations declared (integrations.yaml)"
    return ", ".join(sorted(declared)) + " (declared, activation ships in a later version)"


def run(brain: Optional[Brain] = None) -> int:
    """Run the interactive CLI. Returns a process exit code."""
    if brain is None:
        try:
            config = BrainConfig.from_env()
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        brain = OpenAICompatBrain(config)

    session = Session(brain)
    print(BANNER)
    while True:
        try:
            user_text = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("bye!")
            return 0
        if not user_text:
            continue
        if user_text.startswith("/"):
            command = user_text.split()[0].lower()
            if command in ("/quit", "/exit"):
                print("bye!")
                return 0
            if command == "/clear":
                session.clear()
                print("conversation cleared.")
                continue
            if command == "/help":
                print(HELP_TEXT)
                continue
            if command == "/status":
                model = getattr(getattr(brain, "config", None), "model", "unknown")
                print(f"brain: {model}")
                print(f"integrations: {_integration_status()}")
                continue
            print(f"unknown command {command!r}; /help lists commands.")
            continue
        try:
            reply = session.send(user_text)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"lexai > {reply}")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()