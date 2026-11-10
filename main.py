"""Mini CRM: contacts with server-rendered HTML, protected by ADMIN_PASSWORD."""
import hashlib
import hmac
import logging
import os
import secrets

import psycopg
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg.rows import dict_row
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("crm")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUSES = ["lead", "contacted", "customer", "lost"]

app = FastAPI(title="Mini CRM", docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

_password = os.environ.get("ADMIN_PASSWORD", "")
_session_secret = hashlib.sha256(("crm-session:" + (_password or secrets.token_hex(16))).encode()).hexdigest()
app.add_middleware(SessionMiddleware, secret_key=_session_secret, max_age=14 * 86400, same_site="lax")

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'lead',
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_db_ready = False
_db_error = None


def ensure_db():
    global _db_ready, _db_error
    if _db_ready:
        return True
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            conn.execute(SCHEMA)
        _db_ready, _db_error = True, None
    except Exception as exc:
        _db_error = str(exc)
        log.exception("Database setup failed")
    return _db_ready


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10, row_factory=dict_row)


def render(request, name, status_code=200, **ctx):
    ctx.setdefault("statuses", STATUSES)
    ctx.setdefault("signed_in", bool(request.session.get("ok")))
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


class Stop(Exception):
    """Raised by gate() to answer with a ready-made response."""

    def __init__(self, response):
        self.response = response


@app.exception_handler(Stop)
async def stop_handler(request, exc):
    return exc.response


def gate(request: Request):
    """Database first, then password, then login."""
    if not ensure_db():
        raise Stop(render(request, "setup.html", has_url=bool(os.environ.get("DATABASE_URL")), error=_db_error))
    if not _password:
        raise Stop(render(request, "no_password.html"))
    if not request.session.get("ok"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@app.get("/login")
def login_page(request: Request):
    if not ensure_db():
        return render(request, "setup.html", has_url=bool(os.environ.get("DATABASE_URL")), error=_db_error)
    if not _password:
        return render(request, "no_password.html")
    return render(request, "login.html", error=None)


@app.post("/login")
def login(request: Request, password: str = Form("")):
    if _password and hmac.compare_digest(password.encode(), _password.encode()):
        request.session["ok"] = True
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", status_code=401, error="Wrong password.")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", dependencies=[Depends(gate)])
def home(request: Request, q: str = "", status: str = ""):
    sql = "SELECT * FROM contacts WHERE true"
    params = []
    if q:
        sql += " AND (name ILIKE %s OR email ILIKE %s OR company ILIKE %s OR notes ILIKE %s)"
        params += [f"%{q}%"] * 4
    if status in STATUSES:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY updated_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, count(*) AS n FROM contacts GROUP BY status")}
    return render(request, "list.html", rows=rows, q=q, status=status, counts=counts)


@app.get("/contacts/new", dependencies=[Depends(gate)])
def new_form(request: Request):
    return render(request, "form.html", contact={"status": "lead"}, action="/contacts", title="New contact", error=None)


def clean(name, email, company, status, notes):
    return (
        name.strip()[:200],
        email.strip()[:254],
        company.strip()[:200],
        status if status in STATUSES else "lead",
        notes.strip()[:5000],
    )


@app.post("/contacts", dependencies=[Depends(gate)])
def create(request: Request, name: str = Form(""), email: str = Form(""), company: str = Form(""),
           status: str = Form("lead"), notes: str = Form("")):
    values = clean(name, email, company, status, notes)
    if not values[0]:
        contact = dict(zip(["name", "email", "company", "status", "notes"], values))
        return render(request, "form.html", status_code=400, contact=contact, action="/contacts",
                      title="New contact", error="Name is required.")
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO contacts (name, email, company, status, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id", values
        ).fetchone()
    return RedirectResponse(f"/contacts/{row['id']}", status_code=303)


def get_contact(contact_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return row


@app.get("/contacts/{contact_id}", dependencies=[Depends(gate)])
def edit_form(request: Request, contact_id: int, saved: int = 0):
    return render(request, "form.html", contact=get_contact(contact_id), action=f"/contacts/{contact_id}",
                  title="Contact", error=None, saved=bool(saved), can_delete=True)


@app.post("/contacts/{contact_id}", dependencies=[Depends(gate)])
def update(request: Request, contact_id: int, name: str = Form(""), email: str = Form(""), company: str = Form(""),
           status: str = Form("lead"), notes: str = Form("")):
    get_contact(contact_id)
    values = clean(name, email, company, status, notes)
    if not values[0]:
        contact = dict(zip(["name", "email", "company", "status", "notes"], values))
        return render(request, "form.html", status_code=400, contact=contact, action=f"/contacts/{contact_id}",
                      title="Contact", error="Name is required.", can_delete=True)
    with connect() as conn:
        conn.execute(
            "UPDATE contacts SET name=%s, email=%s, company=%s, status=%s, notes=%s, updated_at=now() WHERE id=%s",
            (*values, contact_id),
        )
    return RedirectResponse(f"/contacts/{contact_id}?saved=1", status_code=303)


@app.post("/contacts/{contact_id}/delete", dependencies=[Depends(gate)])
def delete(contact_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
    return RedirectResponse("/", status_code=303)
