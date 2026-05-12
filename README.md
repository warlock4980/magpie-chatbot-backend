# magpie-chatbot-backend

Backend for the chat widget on https://magpiestudios.app. Proxies user
messages to Anthropic Claude Haiku 4.5 with a curated Magpie Studios
knowledge base and strict redaction rules.

## Files

- `chatbot_server.py` — Flask app, serves `/chat` (POST) and `/health` (GET)
- `chatbot_knowledge.md` — curated public knowledge loaded into system prompt
- `requirements.txt` — Python deps
- `Procfile` — start command for Render/Heroku-style PaaS
- `runtime.txt` — Python version pin

## Deploy

1. Push this repo to GitHub.
2. https://dashboard.render.com → New → Web Service → connect repo.
3. Render auto-detects Python + Procfile.
4. Add environment variable: `ANTHROPIC_API_KEY` (from console.anthropic.com).
5. Free tier is fine; spins down after 15 min idle (~30s cold start).

## Local dev

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python chatbot_server.py
# → http://localhost:5001
```
