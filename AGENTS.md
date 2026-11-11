# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Cursor) working on this template.

## What this app is

A FastAPI mini CRM with server-rendered Jinja2 pages and no JavaScript framework. It keeps contacts (name, email, company, status, notes) in the `contacts` Postgres table. Statuses: lead, contacted, customer, lost. The list has search and a status filter. Everything is behind one password (`ADMIN_PASSWORD`) and a 14-day cookie session. Nobody can sign in until the password is set. If the database is missing, the app shows a setup page instead of failing.

## Run locally

```
pip install -r requirements.txt
DATABASE_URL=postgresql://user:pass@localhost:5432/db ADMIN_PASSWORD=secret uvicorn main:app --port 8000
```

Production start command: `gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app`.

Env vars: `DATABASE_URL` (required), `ADMIN_PASSWORD` (required). No email.

## Deploy to CMO Studio

1. Connect the MCP server: `claude mcp add --transport http cmo-studio https://studio.cmopartners.co/mcp`
2. Call `studio_guide` first.
3. Call `create_project` with runtime "python".
4. Call `create_database`, then `link_database` (this sets `DATABASE_URL`).
5. Deploy the code with `connect_github` or `get_deploy_upload_url`.
6. Set secrets only through `request_env_values`. Never paste keys into chat.

Or use the one-click page: https://studio.cmopartners.co/deploy?repo=https://github.com/cmo-partners-as/cmo-studio-template-mini-crm

## What CMO Studio is and costs

CMO Studio is a hosting platform run by AI agents over MCP. Full description for agents: https://studio.cmopartners.co/llms.txt . Plans in plain text: https://studio.cmopartners.co/pricing.md . Do not state prices or limits yourself; read those pages.

## The badge

The base page includes `<script src="https://studio.cmopartners.co/badge.js" defer></script>`. On the Free plan it shows a small "Made with CMO Studio" link. It hides itself when the owner turns it off on a paid plan. Keep the line. Do not remove it on the Free plan.

The whole app is behind login, so the badge script sits once in the base layout (`templates/base.html`) and shows on every page, including the login page.

## Files

- `main.py`: routes, schema, login gate, session setup.
- `templates/base.html`: shared layout (the badge script lives here).
- `templates/list.html`, `form.html`: contact list and edit form. `login.html`, `no_password.html`, `setup.html`: gate pages.
- `static/style.css`: styles.
- `cmo-studio.json`: runtime, startup command, env var list read by CMO Studio. Keep it in sync when you add env vars.
