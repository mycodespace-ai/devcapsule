# E2E Scenario Script: FastAPI + PostgreSQL 17 + React Todo Application

Scenario `todo-fastapi-postgres-react`, on the DevCapsule surface `codium`.
Its recording and its presentation are written to
`devcapsule-src/tests/e2e/evidence/todo-fastapi-postgres-react/`.

## Goal

This end-to-end test shows that one isolated capsule is enough for full-stack
work. The editor, Python, Node, the PostgreSQL client and the browser all come
from what the project declares; the developer installs none of them.

## Stack And Capabilities

- **Editor:** VSCodium, the project's `frontend-ide`
- **Backend:** Python 3.12, FastAPI and `psycopg`, `backend/main.py` on `127.0.0.1:18080`
- **Frontend:** Node.js 22, React and Vite, `frontend/src/App.jsx` on `127.0.0.1:15173`, proxying `/api` to `:18080`
- **Database:** PostgreSQL 17 in a container the test starts beside the capsule, database `tododb`, table `todos`, on `127.0.0.1:15432`
- **Browser:** Chromium, from `browser-automation`, on the capsule's desktop

## What It Illustrates

- The project declares its needs (`python`, `node`, `postgresql-client`, `browser-automation` and a frontend IDE) and the capsule provides them.
- The editor, its terminal and the browser share one contained desktop, shown in your browser. The capsule uses no display of the host.
- Backend, frontend and database tools work together inside the capsule: FastAPI on `:18080`, Vite on `:15173`, `psql` against PostgreSQL 17.
- The result is checked from outside: after the recording, the test reads the same four rows from the API and from PostgreSQL.

## Steps

1. **Open the workspace in VSCodium inside the capsule.**
   - *User action:* Launch the project's capsule, trust the workspace when VSCodium asks, and look at the project: `.devcapsule/`, `backend/` and `frontend/`.
   - *Expected observation:* VSCodium fills the capsule's `1600×1000` desktop with the workspace loaded and trusted.

2. **Implement `POST /api/todos` in the FastAPI backend.**
   - *User action:* Quick-open `backend/main.py` (`Ctrl+P`), go to line 75 (`Ctrl+G`) inside `create_todo`, type the parameterized `INSERT INTO todos … RETURNING` query and the JSON response, and save (`Ctrl+S`).
   - *Expected observation:* `backend/main.py` holds the finished insert handler, saved, with no unsaved mark on its tab.

3. **Implement `handleCreate` in the React frontend.**
   - *User action:* Quick-open `frontend/src/App.jsx` (`Ctrl+P`), go to line 30 (`Ctrl+G`) inside `handleCreate`, type the `fetch('/api/todos', { method: 'POST', … })` request and the `setTodos` update, and save (`Ctrl+S`).
   - *Expected observation:* `frontend/src/App.jsx` holds the finished `fetch` call and state update, saved.

4. **Check PostgreSQL 17 and start the stack from the editor's terminal.**
   - *User action:* Open VSCodium's integrated terminal (`` Ctrl+` ``) and run `./run-stack.sh`: it checks PostgreSQL 17 with `psql`, starts Uvicorn on `:18080` and starts Vite on `:15173`.
   - *Expected observation:* The terminal prints the PostgreSQL 17 version, the two seeded rows as `psql` reads them, and `STACK_READY`.

5. **Open the application in Chromium on the capsule's desktop.**
   - *User action:* Launch Chromium on the capsule's own display, beside VSCodium, at `http://127.0.0.1:15173`.
   - *Expected observation:* **CapsuleTask** shows `PostgreSQL 17.11 · Connected`, its counters, and the two seeded tasks, `pg#1` and `pg#2`.

6. **Create two tasks and complete one in the browser.**
   - *User action:* Type *Record FastAPI + React customer pitch demo* and click **Add Task**; type *Verify PostgreSQL 17 persistence across reloads*, choose the *Database* category and click **Add Task**; then tick the checkbox of `pg#1`.
   - *Expected observation:* Both tasks appear at once with the identifiers PostgreSQL gave them, `pg#3` and `pg#4`, and the counters read 4 tasks, 2 completed.

7. **Reload from PostgreSQL and ask the database directly.**
   - *User action:* Click **Refresh from DB**, switch to VSCodium's terminal and run `./query-db.sh`, then return to **CapsuleTask**.
   - *Expected observation:* `psql` and the browser agree: four rows, `1` to `4`, with completion flags `t, t, f, f`.
