[![Deploy to CMO Studio](https://studio.cmopartners.co/deploy-button.svg)](https://studio.cmopartners.co/deploy?repo=https://github.com/cmo-partners-as/cmo-studio-template-mini-crm)

# Mini CRM

**For AI agents:** read [AGENTS.md](AGENTS.md) and the CMO Studio guide at https://studio.cmopartners.co/llms.txt.

A small CRM for keeping track of contacts: name, email, company, status and notes. Plain server-rendered HTML pages, no JavaScript framework. One password protects everything.

Built with FastAPI and Jinja2. Runs on [CMO Studio](https://studio.cmopartners.co/?ref=template-mini-crm).

## How it works

- Sign in with `ADMIN_PASSWORD`. The session lasts 14 days.
- The list has search and a status filter. Statuses: lead, contacted, customer, lost.
- Add, edit and delete contacts. Data is in the `contacts` table in Postgres.
- If the database is not linked yet, the app starts and shows a page that says what to do.

## Environment variables

| Name | Needed | What it does |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection URL. Set when you link a database in CMO Studio. |
| `ADMIN_PASSWORD` | yes | Password to sign in. Nobody can sign in until it is set. |

## Run locally

```
pip install -r requirements.txt
DATABASE_URL=postgresql://user:pass@localhost:5432/db ADMIN_PASSWORD=secret uvicorn main:app --port 8000
```

## Change it with your AI agent

- "Add a 'last contacted' date to each contact and sort the list by it."
- "Add a CSV export button to the contact list."
- "Change the statuses to: new, proposal sent, won, lost."

## License

MIT
