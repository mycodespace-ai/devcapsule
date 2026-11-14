"""Seed files and typed code snippets for the FastAPI + PostgreSQL + React Todo capsule demo."""
from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "API_PORT",
    "BACKEND_TYPED_SNIPPET",
    "DB_URL",
    "PG_PORT",
    "VITE_PORT",
    "write_seed_project",
]

PG_PORT = 15432
API_PORT = 18080
VITE_PORT = 15173
DB_URL = f"postgresql://devcapsule:devcapsule@127.0.0.1:{PG_PORT}/tododb"

VSCODE_SETTINGS = {
    "workbench.colorTheme": "Default Dark Modern",
    "workbench.startupEditor": "none",
    "workbench.tips.enabled": False,
    "workbench.welcomePage.walkthroughs.openOnInstall": False,
    "security.workspace.trust.enabled": False,
    "telemetry.telemetryLevel": "off",
    "update.mode": "none",
    "extensions.ignoreRecommendations": True,
    "window.zoomLevel": 0.5,
    "editor.fontSize": 15,
    "terminal.integrated.fontSize": 14,
    "editor.minimap.enabled": False,
    "editor.autoIndent": "none",
    "editor.autoClosingBrackets": "never",
    "editor.autoClosingQuotes": "never",
    "editor.autoSurround": "never",
    "editor.quickSuggestions": {
        "other": "off",
        "comments": "off",
        "strings": "off",
    },
    "editor.suggestOnTriggerCharacters": False,
    "editor.acceptSuggestionOnEnter": "off",
    "editor.parameterHints.enabled": False,
    "editor.hover.enabled": False,
}

BACKEND_MAIN_INITIAL = f'''"""FastAPI + PostgreSQL 17 backend for the CapsuleTask Todo application."""
from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg

DB_URL = os.environ.get("DATABASE_URL", "{DB_URL}")


class TodoCreate(BaseModel):
    title: str
    category: str = "Engineering"


class TodoPatch(BaseModel):
    completed: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with psycopg.connect(DB_URL) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Engineering',
                completed BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        if count == 0:
            conn.cursor().executemany(
                "INSERT INTO todos (title, category, completed) VALUES (%s, %s, %s)",
                [
                    ("Provision isolated DevCapsule workspace", "Platform", False),
                    ("Connect FastAPI service to PostgreSQL 17", "Database", True),
                ],
            )
    yield


app = FastAPI(title="CapsuleTask API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, object]:
    with psycopg.connect(DB_URL) as conn:
        pg_ver = conn.execute("SHOW server_version").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
    return {{"ok": True, "postgres": pg_ver, "todos": total}}


@app.get("/api/todos")
def list_todos() -> list[dict[str, object]]:
    with psycopg.connect(DB_URL) as conn:
        rows = conn.execute(
            "SELECT id, title, category, completed FROM todos ORDER BY id ASC"
        ).fetchall()
    return [
        {{"id": r[0], "title": r[1], "category": r[2], "completed": r[3]}}
        for r in rows
    ]


@app.post("/api/todos", status_code=201)
def create_todo(payload: TodoCreate) -> dict[str, object]:
    # Live IDE demo: insert task into PostgreSQL and return created row

@app.patch("/api/todos/{{todo_id}}")
def toggle_todo(todo_id: int, patch: TodoPatch) -> dict[str, object]:
    with psycopg.connect(DB_URL) as conn:
        row = conn.execute(
            "UPDATE todos SET completed = %s WHERE id = %s RETURNING id, title, category, completed",
            (patch.completed, todo_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {{"id": row[0], "title": row[1], "category": row[2], "completed": row[3]}}
'''

BACKEND_TYPED_SNIPPET = (
    "    with psycopg.connect(DB_URL) as conn:\n"
    "        row = conn.execute(\n"
    "            'INSERT INTO todos (title, category) VALUES (%s, %s) RETURNING id, title, category, completed',\n"
    "            (payload.title.strip(), payload.category),\n"
    "        ).fetchone()\n"
    "    return {'id': row[0], 'title': row[1], 'category': row[2], 'completed': row[3]}\n"
)

FRONTEND_PACKAGE_JSON = {
    "name": "capsuletask-ui",
    "private": True,
    "version": "0.1.0",
    "type": "module",
    "scripts": {
        "dev": f"vite --host 127.0.0.1 --port {VITE_PORT} --strictPort",
    },
    "dependencies": {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.3.4",
        "vite": "^5.4.11",
    },
}

FRONTEND_VITE_CONFIG = f"""import {{ defineConfig }} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({{
  plugins: [react()],
  server: {{
    host: '127.0.0.1',
    port: {VITE_PORT},
    strictPort: true,
    proxy: {{
      '/api': 'http://127.0.0.1:{API_PORT}',
    }},
  }},
}});
"""

FRONTEND_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CapsuleTask — FastAPI + PostgreSQL + React</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

FRONTEND_MAIN_JSX = """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(<App />);
"""

FRONTEND_STYLES_CSS = """* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f172a;
  color: #f8fafc;
}
.shell {
  max-width: 920px;
  margin: 0 auto;
  padding: 28px 32px;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #1e293b;
}
.brand h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: -0.02em;
}
.brand p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #94a3b8;
}
.db-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #34d399;
  font-size: 13px;
  font-weight: 600;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 12px 16px;
}
.stat-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; }
.stat-val { font-size: 24px; font-weight: 700; margin-top: 4px; color: #f1f5f9; }
.composer {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  background: #1e293b;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #334155;
}
.composer input {
  flex: 1;
  padding: 11px 14px;
  border-radius: 8px;
  border: 1px solid #475569;
  background: #0f172a;
  color: #f8fafc;
  font-size: 15px;
}
.composer select {
  padding: 11px 12px;
  border-radius: 8px;
  border: 1px solid #475569;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 14px;
}
.btn-primary {
  padding: 11px 20px;
  border-radius: 8px;
  border: none;
  background: #3b82f6;
  color: #ffffff;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}
.btn-secondary {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #475569;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.list-header h2 { margin: 0; font-size: 15px; color: #cbd5e1; }
.todo-list { display: flex; flex-direction: column; gap: 10px; }
.todo-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #1e293b;
  border: 1px solid #334155;
}
.todo-row.done { opacity: 0.72; background: #172033; }
.todo-check {
  width: 22px;
  height: 22px;
  cursor: pointer;
  accent-color: #10b981;
}
.todo-title { flex: 1; font-size: 15px; font-weight: 500; }
.todo-row.done .todo-title { text-decoration: line-through; color: #94a3b8; }
.badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.16);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.35);
}
.row-id { font-family: monospace; font-size: 12px; color: #64748b; }
"""

FRONTEND_APP_INITIAL = """import React, { useEffect, useState } from 'react';

export default function App() {
  const [todos, setTodos] = useState([]);
  const [pgVersion, setPgVersion] = useState('connecting...');
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Engineering');
  const [syncStamp, setSyncStamp] = useState('Initial load');

  async function loadAll(label = 'Synced from PostgreSQL') {
    const [healthRes, todosRes] = await Promise.all([
      fetch('/api/health'),
      fetch('/api/todos'),
    ]);
    const health = await healthRes.json();
    const rows = await todosRes.json();
    setPgVersion(`PostgreSQL ${health.postgres}`);
    setTodos(rows);
    setSyncStamp(`${label} (${rows.length} rows)`);
  }

  useEffect(() => {
    loadAll('Initial load');
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!title.trim()) return;
    // Live IDE demo: POST new task to FastAPI and append returned PostgreSQL row

  }

  async function handleToggle(todo) {
    const res = await fetch(`/api/todos/${todo.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed: !todo.completed }),
    });
    const updated = await res.json();
    setTodos((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setSyncStamp(`Updated row #${updated.id} in PostgreSQL`);
  }

  const doneCount = todos.filter((t) => t.completed).length;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>CapsuleTask</h1>
          <p>DevCapsule Full-Stack Workspace · FastAPI + PostgreSQL + React</p>
        </div>
        <div className="db-pill" role="status">
          <span className="dot" />
          <span>{pgVersion} · Connected</span>
        </div>
      </header>

      <section className="stats">
        <div className="stat-card">
          <div className="stat-label">Total Tasks</div>
          <div className="stat-val" data-testid="stat-total">{todos.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open</div>
          <div className="stat-val" data-testid="stat-open">{todos.length - doneCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Completed</div>
          <div className="stat-val" data-testid="stat-done">{doneCount}</div>
        </div>
      </section>

      <form className="composer" onSubmit={handleCreate}>
        <input
          aria-label="New task title"
          placeholder="Add an engineering task persisted in PostgreSQL..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select
          aria-label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="Engineering">Engineering</option>
          <option value="Database">Database</option>
          <option value="Launch">Launch</option>
        </select>
        <button type="submit" className="btn-primary">Add Task</button>
      </form>

      <div className="list-header">
        <h2>Persisted Tasks ({syncStamp})</h2>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => loadAll('Reloaded from PostgreSQL')}
        >
          Refresh from DB
        </button>
      </div>

      <div className="todo-list">
        {todos.map((todo) => (
          <div key={todo.id} className={`todo-row ${todo.completed ? 'done' : ''}`}>
            <input
              type="checkbox"
              className="todo-check"
              aria-label={`Complete ${todo.title}`}
              checked={todo.completed}
              onChange={() => handleToggle(todo)}
            />
            <span className="todo-title">{todo.title}</span>
            <span className="badge">{todo.category}</span>
            <span className="row-id">pg#{todo.id}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

FRONTEND_TYPED_SNIPPET = (
    "    const res = await fetch('/api/todos', {\n"
    "      method: 'POST',\n"
    "      headers: { 'Content-Type': 'application/json' },\n"
    "      body: JSON.stringify({ title, category }),\n"
    "    });\n"
    "    const created = await res.json();\n"
    "    setTodos((prev) => [...prev, created]);\n"
    "    setTitle('');\n"
)

RUN_STACK_SH = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export DATABASE_URL="{DB_URL}"
echo "=== [1/3] Checking PostgreSQL 17 via DevCapsule psql component ==="
psql "$DATABASE_URL" -c "SELECT version();" -t | head -n 1

echo "=== [2/3] Starting FastAPI (Uvicorn on 127.0.0.1:{API_PORT}) ==="
nohup ./backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port {API_PORT} </dev/null > /tmp/fastapi.log 2>&1 &
echo $! > /tmp/fastapi.pid

for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:{API_PORT}/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
curl -fsS http://127.0.0.1:{API_PORT}/api/health && echo ""

echo "=== [3/3] Starting React + Vite dev server (127.0.0.1:{VITE_PORT}) ==="
nohup npm --prefix frontend run dev </dev/null > /tmp/vite.log 2>&1 &
echo $! > /tmp/vite.pid

for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:{VITE_PORT}/ >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

echo "=== Initial rows in PostgreSQL todos table ==="
psql "$DATABASE_URL" -c "SELECT id, category, completed, title FROM todos ORDER BY id;"
echo "STACK_READY api=http://127.0.0.1:{API_PORT} ui=http://localhost:{VITE_PORT}"
"""

QUERY_DB_SH = f"""#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export DATABASE_URL="{DB_URL}"
psql "$DATABASE_URL" -c "SELECT id, category, completed, title FROM todos ORDER BY id;"
"""


def write_seed_project(workspace: Path) -> dict[str, int]:
    """Write initial Todo project files into ``workspace`` and return exact target edit lines."""
    (workspace / ".vscode").mkdir(parents=True, exist_ok=True)
    (workspace / ".vscode" / "settings.json").write_text(
        json.dumps(VSCODE_SETTINGS, indent=2) + "\n", encoding="utf-8"
    )
    (workspace / "backend").mkdir(parents=True, exist_ok=True)
    (workspace / "backend" / "__init__.py").write_text("", encoding="utf-8")
    (workspace / "backend" / "main.py").write_text(BACKEND_MAIN_INITIAL, encoding="utf-8")

    (workspace / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "frontend" / "package.json").write_text(
        json.dumps(FRONTEND_PACKAGE_JSON, indent=2) + "\n", encoding="utf-8"
    )
    (workspace / "frontend" / "vite.config.js").write_text(FRONTEND_VITE_CONFIG, encoding="utf-8")
    (workspace / "frontend" / "index.html").write_text(FRONTEND_INDEX_HTML, encoding="utf-8")
    (workspace / "frontend" / "src" / "main.jsx").write_text(FRONTEND_MAIN_JSX, encoding="utf-8")
    (workspace / "frontend" / "src" / "styles.css").write_text(FRONTEND_STYLES_CSS, encoding="utf-8")
    (workspace / "frontend" / "src" / "App.jsx").write_text(FRONTEND_APP_INITIAL, encoding="utf-8")

    for name, body in (("run-stack.sh", RUN_STACK_SH), ("query-db.sh", QUERY_DB_SH)):
        p = workspace / name
        p.write_text(body, encoding="utf-8")
        p.chmod(0o755)

    backend_lines = BACKEND_MAIN_INITIAL.splitlines()
    backend_marker = next(
        idx + 2 for idx, line in enumerate(backend_lines) if "# Live IDE demo:" in line
    )
    frontend_lines = FRONTEND_APP_INITIAL.splitlines()
    frontend_marker = next(
        idx + 2 for idx, line in enumerate(frontend_lines) if "// Live IDE demo:" in line
    )
    return {"backend_edit_line": backend_marker, "frontend_edit_line": frontend_marker}


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        info = write_seed_project(Path(d))
        print("Edit lines:", info)
        # Verify completed backend compiles cleanly when BACKEND_TYPED_SNIPPET is inserted!
        lines = (Path(d) / "backend" / "main.py").read_text().splitlines(keepends=True)
        idx = info["backend_edit_line"] - 1
        completed = "".join(lines[:idx] + [BACKEND_TYPED_SNIPPET] + lines[idx:])
        compile(completed, "backend/main.py", "exec")
        print("Compiled completed backend/main.py successfully!")
