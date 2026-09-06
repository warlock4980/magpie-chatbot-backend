# magpie-chatbot-backend

Chat backend for **Magpie Studios** — one Flask process that serves the chat
widgets on [magpiestudios.app](https://magpiestudios.app) and
[grubtruck.app](https://grubtruck.app), plus the Magpie Studios static site.
User messages are proxied to the Anthropic API (Claude Haiku 4.5) with a
per-product knowledge base and a shared set of brand-safety redaction rules
baked into the system prompt.

## What it does

- Answers visitor questions about Magpie Studios products (MacJanitor) and
  GrubTrucks from curated public knowledge files — one identity per product,
  same server.
- Layers redaction rules on top of the knowledge so the bot deflects rather
  than discusses private topics (names, internal tooling, financials, etc.).
- Logs each Q&A turn (anonymized — no IP, no user ID) to an append-only JSONL
  file for weekly review.
- Ships a companion script, `summarize_chats.py`, that feeds the past week of
  logs to Claude and prints a markdown report: recurring questions, weak
  answers, suggested knowledge-base additions, and redaction near-misses.

## Architecture

```
browser widget ──POST /chat or /chat-grub──▶ Flask (chatbot_server.py)
                                               │  system prompt =
                                               │    knowledge .md file
                                               │    + redaction rules
                                               │    + reply constraints
                                               ▼
                                        Anthropic API (claude-haiku-4-5)
                                               │
                                               ▼
                                    JSON reply + JSONL turn log
```

- **Flask + flask-cors** — CORS locked to the production domains and
  localhost; served by gunicorn in production (see `Procfile`).
- **System prompt assembly** — `chatbot_knowledge.md` (Magpie) or
  `grubtrucks_knowledge.md` (GrubTrucks) is loaded at startup and combined
  with shared redaction rules; only the public contact email differs per
  product.
- **Conversation state** — the client sends recent history with each request;
  the server keeps the last 10 turns and caps replies at 400 tokens.
- **Logging** — best-effort JSONL append (timestamp, product, token counts,
  message text); a logging failure never blocks a reply.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat` | Chat for magpiestudios.app (Magpie identity) |
| `POST` | `/chat-grub` | Chat for grubtruck.app (GrubTrucks identity) |
| `GET` | `/health` | Status, model, knowledge-base and log sizes |
| `GET` | `/admin/logs` | Download the JSONL conversation log (bearer auth) |
| `GET` | `/` and `/<path>` | Magpie Studios static site |

Chat request body: `{"message": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}`
(history optional). Response: `{"reply": "...", "model": "...", "input_tokens": n, "output_tokens": n}`.
Messages are capped at 2,000 characters.

## Run locally

```bash
pip install -r requirements.txt
# put env vars in .env (loaded automatically, no python-dotenv needed)
# or export them in your shell
python chatbot_server.py
# → http://localhost:5000
```

Smoke test:

```bash
curl -s http://localhost:5000/health
curl -s -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is MacJanitor?"}'
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Anthropic API access for chat and summaries |
| `ADMIN_TOKEN` | no | Bearer token protecting `GET /admin/logs`; unset = endpoint open |
| `CHAT_LOG_PATH` | no | Where to write the JSONL log (default: `./chat_log.jsonl`) |
| `PORT` | no | Listen port (default: `5000`) |

## Deploy

Render/Heroku-style PaaS: connect the repo, let it detect Python + `Procfile`
(gunicorn, 2 workers), pin from `runtime.txt`, and set the environment
variables above in the dashboard.

## Files

- `chatbot_server.py` — the whole server: routes, system-prompt assembly, logging
- `chatbot_knowledge.md` / `grubtrucks_knowledge.md` — curated public knowledge per product
- `summarize_chats.py` — weekly log review via Claude (`--days`, `--log`, `--max-turns`)
- `Procfile`, `runtime.txt`, `requirements.txt` — deploy config
