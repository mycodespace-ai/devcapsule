"""Seed generator for the Java + Spring Boot + PostgreSQL 17 customer pitch E2E scenario.

Generates a Maven Spring Boot 3.4.5 project ('CapsuleSprint') configured with
<maven.compiler.release>21</maven.compiler.release> so it compiles and runs
cleanly under OpenJDK 25 inside DevCapsule, using Spring's fluent JdbcClient
against PostgreSQL 17 and serving an interactive single-page web UI.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

__all__ = [
    "POM_XML",
    "SPRINT_CONTROLLER_JAVA",
    "TYPED_JAVA_SNIPPET",
    "materialize",
]

POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.4.5</version>
        <relativePath/>
    </parent>

    <groupId>io.devcapsule.demo</groupId>
    <artifactId>capsule-sprint</artifactId>
    <version>0.1.0</version>
    <name>CapsuleSprint</name>
    <description>DevCapsule Spring Boot + PostgreSQL 17 Customer Pitch Demo</description>

    <properties>
        <maven.compiler.release>21</maven.compiler.release>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-jdbc</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""

MAVEN_CONFIG = "-Dmaven.repo.local=.m2/repository\n"

APPLICATION_PROPERTIES = """server.port=${APP_PORT:18085}
spring.application.name=capsule-sprint
spring.datasource.url=${SPRING_DATASOURCE_URL:jdbc:postgresql://127.0.0.1:15432/sprintdb}
spring.datasource.username=${SPRING_DATASOURCE_USERNAME:postgres}
spring.datasource.password=${SPRING_DATASOURCE_PASSWORD:postgres}
spring.sql.init.mode=always
logging.level.root=WARN
logging.level.io.devcapsule.demo=INFO
logging.level.org.springframework.boot.web.embedded.tomcat=INFO
"""

SCHEMA_SQL = """CREATE TABLE IF NOT EXISTS sprint_items (
    id SERIAL PRIMARY KEY,
    code VARCHAR(24) NOT NULL,
    title TEXT NOT NULL,
    service VARCHAR(48) NOT NULL DEFAULT 'Core API',
    resolved BOOLEAN NOT NULL DEFAULT FALSE
);
"""

APPLICATION_JAVA = """package io.devcapsule.demo;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.simple.JdbcClient;

@SpringBootApplication
public class CapsuleSprintApplication {

    public static void main(String[] args) {
        SpringApplication.run(CapsuleSprintApplication.class, args);
    }

    @Bean
    CommandLineRunner seedDatabase(JdbcClient jdbc) {
        return args -> {
            Long count = jdbc.sql("SELECT COUNT(*) FROM sprint_items")
                    .query(Long.class)
                    .single();
            if (count == 0) {
                jdbc.sql("INSERT INTO sprint_items (code, title, service, resolved) VALUES "
                        + "('CAP-101', 'Bootstrap isolated IntelliJ + Java 25 capsule', 'Platform', true), "
                        + "('CAP-102', 'Wire HikariCP pool to PostgreSQL 17', 'Database', true)")
                        .update();
            }
        };
    }
}
"""

SPRINT_ITEM_JAVA = """package io.devcapsule.demo;

public record SprintItem(
        Long id,
        String code,
        String title,
        String service,
        boolean resolved
) {}
"""

CREATE_ITEM_REQUEST_JAVA = """package io.devcapsule.demo;

public record CreateItemRequest(
        String title,
        String service
) {}
"""

RESOLVE_REQUEST_JAVA = """package io.devcapsule.demo;

public record ResolveRequest(
        boolean resolved
) {}
"""

# Note: createItem (@PostMapping("/api/items")) is intentionally left with a single
# placeholder line at line 45 so IntelliJ IDEA live-types the JdbcClient INSERT ... RETURNING
# implementation during the recorded demo!
SPRINT_CONTROLLER_JAVA = """package io.devcapsule.demo;

import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class SprintController {

    private final JdbcClient jdbc;

    public SprintController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        String pgVersion = jdbc.sql("SHOW server_version").query(String.class).single();
        Long total = jdbc.sql("SELECT COUNT(*) FROM sprint_items").query(Long.class).single();
        return Map.of("ok", true, "postgres", pgVersion, "java", Runtime.version().toString(), "items", total);
    }

    @GetMapping("/api/items")
    public List<SprintItem> listItems() {
        return jdbc.sql("SELECT id, code, title, service, resolved FROM sprint_items ORDER BY id ASC")
                .query(SprintItem.class)
                .list();
    }

    @PostMapping("/api/items")
    @ResponseStatus(HttpStatus.CREATED)
    public SprintItem createItem(@RequestBody CreateItemRequest req) {
        String nextCode = "CAP-" + (101 + jdbc.sql("SELECT COUNT(*) FROM sprint_items").query(Long.class).single());
        // Live IDE demo: insert sprint item into PostgreSQL and return mapped record
        throw new ResponseStatusException(HttpStatus.NOT_IMPLEMENTED, "Live demo placeholder");
    }

    @PatchMapping("/api/items/{id}")
    public SprintItem toggleResolved(@PathVariable Long id, @RequestBody ResolveRequest patch) {
        return jdbc.sql("UPDATE sprint_items SET resolved = :resolved WHERE id = :id "
                        + "RETURNING id, code, title, service, resolved")
                .param("resolved", patch.resolved())
                .param("id", id)
                .query(SprintItem.class)
                .optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found"));
    }
}
"""

TYPED_JAVA_SNIPPET = """        return jdbc.sql("INSERT INTO sprint_items (code, title, service) VALUES (:code, :title, :svc) RETURNING id, code, title, service, resolved")
                .param("code", nextCode)
                .param("title", req.title().trim())
                .param("svc", req.service())
                .query(SprintItem.class)
                .single();
"""

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CapsuleSprint — Spring Boot + PostgreSQL 17</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, -apple-system, sans-serif; }
    body { margin: 0; background: #0b1120; color: #e2e8f0; }
    .wrap { max-width: 960px; margin: 36px auto; padding: 0 24px; }
    .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
    h1 { margin: 0; font-size: 28px; letter-spacing: -0.02em; }
    .sub { color: #94a3b8; font-size: 14px; margin-top: 4px; }
    .badges { display: flex; gap: 10px; }
    .badge { padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 600;
             background: rgba(16, 185, 129, 0.14); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .badge.java { background: rgba(245, 158, 11, 0.14); color: #fbbf24; border-color: rgba(251, 191, 36, 0.3); }
    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 22px; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px 20px; }
    .card .lbl { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8; }
    .card .val { font-size: 28px; font-weight: 700; margin-top: 6px; }
    form { display: flex; gap: 12px; background: #111827; border: 1px solid #1f2937;
           padding: 14px; border-radius: 12px; margin-bottom: 22px; }
    input { flex: 1; background: #0b1120; border: 1px solid #334155; color: #f8fafc;
            padding: 11px 14px; border-radius: 8px; font-size: 15px; }
    select { background: #0b1120; border: 1px solid #334155; color: #f8fafc;
             padding: 11px 14px; border-radius: 8px; font-size: 14px; }
    button.primary { background: #2563eb; color: #fff; border: none; border-radius: 8px;
                     padding: 11px 20px; font-size: 14px; font-weight: 600; cursor: pointer; }
    .bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .bar span { font-size: 14px; font-weight: 600; color: #cbd5e1; }
    button.ghost { background: transparent; color: #cbd5e1; border: 1px solid #334155;
                   border-radius: 8px; padding: 7px 14px; font-size: 13px; cursor: pointer; }
    .list { display: flex; flex-direction: column; gap: 10px; }
    .row { display: flex; align-items: center; gap: 14px; background: #111827;
           border: 1px solid #1f2937; border-radius: 10px; padding: 14px 18px; }
    .chk { width: 22px; height: 22px; border-radius: 6px; border: 2px solid #475569;
           display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 14px; }
    .chk.done { background: #10b981; border-color: #10b981; color: #052e16; font-weight: 800; }
    .code { font-family: ui-monospace, monospace; font-size: 13px; color: #60a5fa; font-weight: 600; }
    .title { flex: 1; font-size: 15px; }
    .title.done { text-decoration: line-through; color: #64748b; }
    .svc { font-size: 12px; padding: 4px 10px; border-radius: 6px; background: #1e293b; color: #93c5fd; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>CapsuleSprint</h1>
        <div class="sub">DevCapsule Enterprise Java Workspace · Spring Boot 3.4 + JdbcClient + PostgreSQL 17</div>
      </div>
      <div class="badges">
        <div class="badge java" id="java-badge">Java · Loading</div>
        <div class="badge" id="pg-badge">PostgreSQL · Connecting</div>
      </div>
    </div>

    <div class="stats">
      <div class="card"><div class="lbl">Total Sprint Items</div><div class="val" id="stat-total">0</div></div>
      <div class="card"><div class="lbl">Open</div><div class="val" id="stat-open">0</div></div>
      <div class="card"><div class="lbl">Resolved</div><div class="val" id="stat-resolved">0</div></div>
    </div>

    <form id="create-form">
      <input id="title-input" placeholder="Add a Spring Boot engineering item persisted in PostgreSQL..." autocomplete="off" />
      <select id="service-select">
        <option value="Spring API">Spring API</option>
        <option value="PostgreSQL">PostgreSQL</option>
        <option value="Platform">Platform</option>
      </select>
      <button type="submit" class="primary" id="add-btn">Create Item</button>
    </form>

    <div class="bar">
      <span id="sync-label">Persisted Sprint Backlog</span>
      <button type="button" class="ghost" id="refresh-btn">Refresh from DB</button>
    </div>

    <div class="list" id="item-list"></div>
  </div>

  <script>
    let items = [];

    function render(syncNote) {
      document.getElementById('stat-total').textContent = items.length;
      const resolved = items.filter(i => i.resolved).length;
      document.getElementById('stat-open').textContent = items.length - resolved;
      document.getElementById('stat-resolved').textContent = resolved;
      if (syncNote) {
        document.getElementById('sync-label').textContent = `Persisted Sprint Backlog (${syncNote})`;
      }
      const root = document.getElementById('item-list');
      root.innerHTML = '';
      for (const item of items) {
        const row = document.createElement('div');
        row.className = 'row';
        row.innerHTML = `
          <div class="chk ${item.resolved ? 'done' : ''}" data-id="${item.id}">${item.resolved ? '✓' : ''}</div>
          <span class="code">${item.code}</span>
          <span class="title ${item.resolved ? 'done' : ''}">${item.title}</span>
          <span class="svc">${item.service}</span>
        `;
        row.querySelector('.chk').addEventListener('click', () => toggleItem(item));
        root.appendChild(row);
      }
    }

    async function loadAll(label = 'Synced from PostgreSQL') {
      const [hRes, iRes] = await Promise.all([fetch('/api/health'), fetch('/api/items')]);
      const health = await hRes.json();
      items = await iRes.json();
      document.getElementById('java-badge').textContent = `Java ${health.java} · Spring Boot`;
      document.getElementById('pg-badge').textContent = `● PostgreSQL ${health.postgres} · Connected`;
      render(`${label} (${items.length} rows)`);
    }

    async function toggleItem(item) {
      const res = await fetch(`/api/items/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved: !item.resolved }),
      });
      const updated = await res.json();
      items = items.map(x => x.id === updated.id ? updated : x);
      render('Updated in PostgreSQL');
    }

    document.getElementById('create-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('title-input');
      const svc = document.getElementById('service-select').value;
      if (!input.value.trim()) return;
      const res = await fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: input.value, service: svc }),
      });
      if (res.ok) {
        const created = await res.json();
        items = [...items, created];
        input.value = '';
        render(`Saved ${created.code} to PostgreSQL`);
      }
    });

    document.getElementById('refresh-btn').addEventListener('click', () => loadAll('Reloaded from PostgreSQL'));
    loadAll('Initial load');
  </script>
</body>
</html>
"""

RUN_STACK_SH = """#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export PGPASSWORD="${SPRING_DATASOURCE_PASSWORD:-postgres}"

echo "==> Checking PostgreSQL 17 connection via psql..."
psql -h 127.0.0.1 -p 15432 -U postgres -d sprintdb -c "SELECT version();" -t | head -n 1

echo "==> Compiling & starting Spring Boot 3.4 (offline Maven cache)..."
mvn -o -q compile
nohup mvn -o -q spring-boot:run > /tmp/springboot.log 2>&1 &

for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:18085/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "==> Seeded rows in sprint_items:"
psql -h 127.0.0.1 -p 15432 -U postgres -d sprintdb -c "SELECT id, code, service, resolved, title FROM sprint_items ORDER BY id;"
echo "STACK_READY: Spring Boot listening on http://127.0.0.1:18085"
"""

QUERY_DB_SH = """#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export PGPASSWORD="${SPRING_DATASOURCE_PASSWORD:-postgres}"
psql -h 127.0.0.1 -p 15432 -U postgres -d sprintdb -c "SELECT id, code, service, resolved, title FROM sprint_items ORDER BY id;"
"""


def materialize(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / ".mvn").mkdir(parents=True, exist_ok=True)
    (workspace / ".mvn" / "maven.config").write_text(MAVEN_CONFIG, encoding="utf-8")
    (workspace / "pom.xml").write_text(POM_XML, encoding="utf-8")

    java_dir = workspace / "src" / "main" / "java" / "io" / "devcapsule" / "demo"
    java_dir.mkdir(parents=True, exist_ok=True)
    (java_dir / "CapsuleSprintApplication.java").write_text(APPLICATION_JAVA, encoding="utf-8")
    (java_dir / "SprintItem.java").write_text(SPRINT_ITEM_JAVA, encoding="utf-8")
    (java_dir / "CreateItemRequest.java").write_text(CREATE_ITEM_REQUEST_JAVA, encoding="utf-8")
    (java_dir / "ResolveRequest.java").write_text(RESOLVE_REQUEST_JAVA, encoding="utf-8")
    controller_path = java_dir / "SprintController.java"
    controller_path.write_text(SPRINT_CONTROLLER_JAVA, encoding="utf-8")

    res_dir = workspace / "src" / "main" / "resources"
    static_dir = res_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "application.properties").write_text(APPLICATION_PROPERTIES, encoding="utf-8")
    (res_dir / "schema.sql").write_text(SCHEMA_SQL, encoding="utf-8")
    (static_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")

    for name, body in (("run-stack.sh", RUN_STACK_SH), ("query-db.sh", QUERY_DB_SH)):
        script = workspace / name
        script.write_text(body, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    lines = SPRINT_CONTROLLER_JAVA.splitlines()
    placeholder_line = next(
        idx for idx, line in enumerate(lines, 1) if "Live demo placeholder" in line
    )
    return {
        "workspace": str(workspace),
        "controller_file": "src/main/java/io/devcapsule/demo/SprintController.java",
        "controller_placeholder_line": placeholder_line,
        "typed_java_lines": len(TYPED_JAVA_SNIPPET.splitlines()),
    }


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/springboot-seed-check")
    print(json.dumps(materialize(target), indent=2))
