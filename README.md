# Expense Tracker

Full-stack demo expense tracker showcasing shared Python business logic, a REST API, React frontend, CLI, and Tkinter desktop app. All interfaces reuse the same services and JSON storage to keep behavior consistent.

---

## Architecture at a Glance

```
┌────────────────┐        ┌───────────────────┐
│ React frontend │  HTTP  │                   │
│   (Vite/TS)    │───────▶│                   │
└────────────────┘        │                   │
                          │                   │
┌────────────────┐        │   Flask API       │        ┌────────────────────┐
│ Tkinter app    │ direct │ (Gunicorn server) │        │ JSON storage files │
│ (desktop)      │───────▶│                   │◀──────▶│   (data/*.json)    │
└────────────────┘        │                   │        └────────────────────┘
                          │   Shared services │
┌────────────────┐        │   & dataclasses   │
│ CLI (argparse) │ direct │                   │
└────────────────┘        └───────────────────┘
```

Key points:

1. `common/` holds the shared domain logic (services, models, validators, storage).
2. `api/` exposes the Flask REST interface.
3. `desktop/` contains the Tkinter GUI.
4. `expense_tracker/cli.py` provides the command-line entry point.
5. Frontend sources live under `web/` (if present) or an external SPA hitting the API.

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm 10+

### Clone the repository

```bash
git clone <repo-url> expense-tracker-fullstack-monorepo
cd expense-tracker-fullstack-monorepo
git submodule update --init --recursive  # omit if no submodules
```

> Replace `<repo-url>` with the HTTPS or SSH path of your fork. Pull updates later with `git pull`.

### Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> The CLI, Tkinter app, and Flask API will write JSON files under `data/` by default. Create it if you want predictable paths: `mkdir -p data`.

---

## Directory Layout

The project is structured as follows:

- `api/`: Flask API implementation
- `common/`: Shared domain logic (services, models, validators, storage)
- `desktop/`: Tkinter GUI implementation
- `docker/`: Docker compose setup for containerization
- `expense_tracker/`: CLI implementation
- `web/`: Optional React frontend implementation

## How to Run the App

### 1. CLI

1. Activate your Python virtual environment (see "Python environment" above).
2. Run commands such as:

   ```bash
   python -m expense_tracker.cli expense add 23.50 USD groceries debit_card 2024-06-01T10:00:00
   python -m expense_tracker.cli income list --source salary
   ```

   Use `--data-dir` to target a custom storage directory. The CLI supports `add`, `list`, `edit`, and `delete` for both expenses and incomes, plus a `balance` command for summaries.

### 2. Desktop

1. Activate the Python environment.
2. Launch the Tkinter app:

   ```bash
   python -m desktop.app.tkapp --data-dir data
   ```

   The UI reads and writes JSON files in the specified data directory, providing tabs for expenses and incomes with live totals.

### 3. Web (Docker Compose)

1. Ensure Docker and Docker Compose are installed.
2. From the repository root, build and start the containers:

   ```bash
   cd docker
   docker compose up --build -d
   ```

3. Once running, open <http://localhost:5173> to interact with the web UI. The backend API is available at <http://localhost:5000}. Configure builds with `VITE_API_BASE_URL` if deploying separately.
4. The web UI mirrors the desktop experience with forms, tables, and summary metrics.
5. Stop the containers with `docker compose down`. JSON data persists in the named `data` volume.

### 4. REST API

1. Activate the Python environment and run:

   ```bash
   export FLASK_APP=api.app:create_app
   flask run --debug
   ```

2. The server exposes:

   - `GET /expenses`, `POST /expenses`, `PUT /expenses/<id>`, `DELETE /expenses/<id>`
   - `GET /incomes`, `POST /incomes`, `PUT /incomes/<id>`, `DELETE /incomes/<id>`
   - `GET /summary` for balance totals

   Payloads follow the schemas enforced by `ExpenseService` and `IncomeService`; dates must be ISO 8601 strings.

---

## Known Limitations

1. JSON storage lacks concurrency control—simultaneous writes from multiple interfaces could clash.
2. No authentication or user accounts; data is shared globally.
3. Frontend uses Vite preview server in Docker; consider a dedicated production web server for static assets.
4. Validation assumes UTC timestamps; no timezone localization in the UI.
5. Tkinter UI offers basic CRUD only—no filtering or editing yet.

---

## Future Improvements

1. Swap JSON storage for a small relational database (SQLite/PostgreSQL) with migrations.
2. Add authentication and per-user ledgers.
3. Introduce richer analytics (category charts, trendlines) in React and Tkinter apps.
4. Package CLI as an installable entry point via `pipx`.
5. Automate tests for API and frontend hooks (pytest + React Testing Library).
6. Harden Docker setup with multi-stage builds generating static frontend output served by Nginx.

---

Feel free to open issues or iterate further—this project is designed as a foundation for exploring multi-interface application architecture.