# E2E Scenario Script: FastAPI + PostgreSQL 17 + React Todo Application

## Goal

Demonstrate a full-stack web development session inside a single isolated
**DevCapsule** container combining **VSCodium** (`frontend-ide`), **Python 3.12**
(`FastAPI` + `psycopg`), **PostgreSQL 17** client tools (`psql`), **Node.js 22**
(`React` + `Vite`), and **Chromium** (`browser-automation`), recording both
human-paced code editing in the IDE and live interaction in the browser.

## Stack And Capabilities

- **Scenario ID:** `todo-fastapi-postgres-react`
- **DevCapsule surface:** `codium` (`frontend-ide`, `python`, `node`, `postgresql-client`, `browser-automation`)
- **Database:** PostgreSQL 17 (`tododb`, table `todos`, `127.0.0.1:15432`)
- **Backend:** Python FastAPI (`backend/main.py` on `http://127.0.0.1:18080`)
- **Frontend:** React + Vite (`frontend/src/App.jsx` on `http://127.0.0.1:15173`, proxying `/api` to `:18080`)
- **Recorded evidence path:** `devcapsule-src/tests/e2e/evidence/todo-fastapi-postgres-react/scenario-video.webm`

## Steps

1. **Open the workspace in VSCodium inside DevCapsule.**
   - *User action:* Launch the project capsule, trust the workspace if prompted, and focus VSCodium showing `.devcapsule/`, `backend/`, and `frontend/`.
   - *Expected observation:* VSCodium renders on the `1600×1000` capsule desktop with the workspace loaded.

2. **Implement `POST /api/todos` in `backend/main.py`.**
   - *User action:* Quick-open `backend/main.py` (`Ctrl+P`), jump to line `75` (`Ctrl+G`) inside `@app.post("/api/todos")`, type the parameterized `INSERT INTO todos (title, category) VALUES (%s, %s) RETURNING id, title, category, completed` query and JSON response, and save (`Ctrl+S`).
   - *Expected observation:* `backend/main.py` shows the completed PostgreSQL insert handler with no unsaved indicator and compiles cleanly on disk.

3. **Implement `handleCreate` in `frontend/src/App.jsx`.**
   - *User action:* Quick-open `frontend/src/App.jsx` (`Ctrl+P`), jump to line `30` (`Ctrl+G`) inside `handleCreate`, type the `fetch('/api/todos', { method: 'POST', ... })` request and `setTodos` state update, and save (`Ctrl+S`).
   - *Expected observation:* `frontend/src/App.jsx` shows the completed `fetch` call and state update saved on disk.

4. **Verify PostgreSQL 17 and start FastAPI + Vite from VSCodium's integrated terminal.**
   - *User action:* Open VSCodium's integrated terminal (`Ctrl+\``) and run `./run-stack.sh` to verify PostgreSQL 17 connectivity via `psql`, start Uvicorn (`:18080`), and start Vite (`:15173`).
   - *Expected observation:* The terminal prints the PostgreSQL 17 banner, the initial seeded rows from `psql`, and `STACK_READY`.

5. **Open the CapsuleTask React application in Chromium on the capsule desktop.**
   - *User action:* Launch Chromium on the capsule X11 display pointing at `http://127.0.0.1:15173` alongside VSCodium.
   - *Expected observation:* **CapsuleTask** renders with `PostgreSQL 17 Connected`, header counters, and the two initial seeded tasks (`pg#1`, `pg#2`).

6. **Create two new tasks and toggle completion in the browser.**
   - *User action:* Click the task input box, type `"Record FastAPI + React customer pitch demo"`, click **Add Task** (`pg#3`); then type `"Verify PostgreSQL 17 persistence across reloads"`, select category `"Database"`, click **Add Task** (`pg#4`); then click the completion checkbox on `pg#1`.
   - *Expected observation:* Both new tasks appear immediately with PostgreSQL IDs `pg#3` and `pg#4`, and the header counters update to `Total: 4`, `Done: 2`.

7. **Reload from PostgreSQL and confirm durable database state via `psql`.**
   - *User action:* Click **Refresh from DB** in the React UI, switch back to VSCodium's terminal to run `./query-db.sh`, and return to **CapsuleTask** for the final poster frame.
   - *Expected observation:* Both `psql` and the browser UI show all four persisted rows (`1`..`4`) and their completion flags (`t, t, f, f`).
