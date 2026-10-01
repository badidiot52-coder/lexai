# LEXAI

A personal AI assistant with a pluggable brain and an integration-ready architecture.

LEXAI is a command-line chat agent that talks to any OpenAI-compatible chat API. Nothing about a specific provider is baked in: you point it at a base URL, an API key, and a model through environment variables, and it runs. On top of the core sits an integration layer (a base class plus a registry plus a YAML config) designed so services like Gmail and Calendar can be dropped in later without touching the core.

## Features

- Pluggable brain: any OpenAI-compatible `/chat/completions` endpoint (OpenAI, Groq, OpenRouter, Together, local Ollama / LM Studio, ...)
- Zero provider lock-in: the default brain uses only the Python standard library for transport
- In-memory conversation history with `/clear` support
- Integration layer ready for Gmail, Calendar, and more (declared in `integrations.yaml`, activated in a future version)
- Clean error messages when configuration is missing or the API misbehaves

## Setup

```bash
git clone https://github.com/badidiot52-coder/lexai.git
cd lexai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

LEXAI reads three environment variables:

| Variable | Meaning | Example |
|---|---|---|
| `LEXAI_API_BASE` | Base URL of an OpenAI-compatible API (no trailing slash needed) | `https://api.openai.com/v1` |
| `LEXAI_API_KEY` | API key for that endpoint | `sk-...` |
| `LEXAI_MODEL` | Model name to use | `gpt-4o-mini` |

Any OpenAI-compatible endpoint works. Examples: `https://api.openai.com/v1`, `https://api.groq.com/openai/v1`, `https://openrouter.ai/api/v1`, `http://localhost:11434/v1` (Ollama).

You can export them in your shell or put them in a `.env`-style setup (the loader reads the process environment).

## Usage

```bash
python -m lexai
```

```
you > what can you do?
lexai > ...
```

Commands: `/help`, `/clear` (reset conversation), `/status` (show model and integrations), `/quit`.

## Project layout

```
lexai/
  lexai/
    __init__.py            package metadata
    config.py              env-var config + integrations.yaml loader
    brain.py               pluggable Brain + OpenAI-compatible implementation
    integrations/__init__.py  Integration base class and registry
    cli.py                 interactive chat loop
    __main__.py            `python -m lexai` entry point
  tests/                   pytest suite (config loader, registry)
  integrations.yaml        integration declarations
```

## Roadmap

- **v0.1 (this release):** core agent: chat loop, pluggable brain, integration contracts
- **Integrations:** connect LEXAI to real services, starting with Gmail (email reading and drafting), then Calendar and more. The `Integration` base class, registry, and `integrations.yaml` are already in place; integrations register themselves and get activated from config.
- **Tool use:** expose active integrations to the brain as callable tools
- **Persistence:** optional conversation and memory storage
- **Config profiles:** multiple brains (e.g. a fast local model and a strong cloud model)

## Development

```bash
pip install -r requirements.txt
pytest
```

## License

MIT