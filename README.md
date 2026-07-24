# r4blog

r4blog is a multi-user Django application for encrypted Markdown posts, notes and projects. It preserves the red-card visual identity and White/Reading/Colorful themes of the original Flask application while adding accounts, private content, profiles, integrity revisions and a token-authenticated API.

## Features

- Separate `Post`, `Note` and `Project` tables built from a shared abstract model
- Separate append-only revision tables with SHA-256 hash chaining
- Fernet-encrypted Markdown at rest in SQLite
- Public content plus owner/admin-only private content
- Manual Markdown and UTF-8 `.md` uploads with a required first H1
- Title, slug and permission-scoped decrypted-body search
- Web create/update/download/soft-delete workflows
- Static-avatar profiles, registration, login/logout and password reset
- Separate REST endpoints for post, note and project create/update/download
- Persistent White, Reading and Colorful themes
- Responsive home, list, detail, profile, About Us and API Guide pages
- Persistent English/Turkish interface selector for core navigation and actions

## Local setup

Python 3.13 is recommended for the current Django 6 project.

```bash
cd new/r4blog
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Generate a Fernet key and put its complete output in `.env` as `CONTENT_ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate and set a separate strong `DJANGO_SECRET_KEY`, then initialize and run the application:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The in-app API documentation is at `/api-guide/`.

## Tests and checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The tests cover encryption, H1/file validation, slug collisions, revision immutability and atomicity, web object permissions, search leakage, profiles, soft deletion, token lifecycle and all three API resource types.

## Content rules

- The first non-empty line must be exactly one Markdown H1, for example `# My title`.
- Title and slug/tag are server-derived. A title change during update changes the slug.
- Slug collisions within one content type become `slug-2`, `slug-3`, and so on.
- Submit either manual Markdown or one UTF-8 `.md` file, never both.
- Content is limited to 2 MB.
- Markdown supports fenced code, tables, links, lists, blockquotes and external images.
- Categories and separate keyword/tag tables are intentionally not used; the slug is the displayed tag.

## Avatars

Allowed avatars are centrally declared in `accounts/constants.py` as an `(internal key, label)` choice and a matching static path. Add a new SVG/PNG under `static/blog/avatars/`, add its key to `AVATAR_CHOICES`, and map the key in `AVATAR_PATHS`. Arbitrary user file uploads and arbitrary paths are not accepted.

## Encryption and search

Markdown bodies and revision snapshots are encrypted before they reach SQLite. Titles, slugs, visibility and hashes remain plaintext so the application can route, list and verify records. Back up `CONTENT_ENCRYPTION_KEY` securely: losing it makes all existing content unrecoverable. Do not change the key without implementing a controlled rotation migration.

Because bodies are encrypted, SQLite cannot use plaintext full-text search. r4blog first narrows candidates to records the requester may see, decrypts only those records in the application process, searches title/slug/body case-insensitively and then paginates. This is deliberately suitable for the current small SQLite deployment, not a large corpus. A larger installation should add a carefully designed protected search index or another search architecture.

## Revision integrity

Every create and update writes an encrypted snapshot to the type-specific revision table in the same database transaction. Each revision records the actor, UTC time, plaintext content SHA-256, previous chain hash and a new chain hash over canonical metadata. Revision models reject application-level update/delete operations and Django admin exposes them read-only. Soft-deleting visible content retains all revisions.

This is an application-level tamper-evidence mechanism. A database administrator can ultimately replace the whole database, and the chain is not an independent notary, blockchain or trusted external timestamp. Export a chain head to an independent trusted timestamp service if third-party date proof is required.

## Security warning: raw HTML

The product specification explicitly requires Markdown raw HTML to remain enabled and unsanitized. In a multi-user site this permits **stored cross-site scripting (XSS)**: a malicious author can publish HTML/JavaScript that runs in a reader's same-origin session. This can undermine CSRF protection and account confidentiality. Do not deploy registrations to untrusted users with this behavior unchanged. Before a public production launch, either sanitize rendered HTML with a strict allowlist or render untrusted content in an appropriately sandboxed, separate origin.

Web forms retain Django CSRF protection, private responses use no-store/private cache headers, API mutations require tokens, object-level checks are applied before decryption, file limits are enforced on the server, and encrypted bodies are omitted from admin lists.

## API summary

Authenticate at `POST /api/v1/auth/token/` with username/password, then send `Authorization: Token <token>`. Revoke at `POST /api/v1/auth/revoke/`.

For each plural resource (`posts`, `notes`, `projects`):

- `POST /api/v1/<resource>/` — create owned content
- `PUT|PATCH /api/v1/<resource>/<slug>/` — update owned content
- `GET /api/v1/<resource>/<slug>/download/` — download Markdown

Public downloads are anonymous. Private downloads require the owner or staff/admin. The API intentionally has no list, JSON detail, delete or revision endpoint. See `/api-guide/` for copy-ready curl examples and validation rules.

## Production checklist

- Set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY` and exact `DJANGO_ALLOWED_HOSTS`.
- Store the Fernet key in a secrets manager and back it up separately from the database.
- Configure HTTPS, secure cookies, HSTS, a production email backend and static-file serving.
- Resolve the raw HTML/XSS warning before admitting untrusted authors.
- Run `python manage.py check --deploy` and review every warning.
- Back up both SQLite and the encryption key; test restoration.
