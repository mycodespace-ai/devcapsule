# E2E Scenario Script: Java 25 + Spring Boot + PostgreSQL 17 In IntelliJ IDEA

Scenario `springboot-postgres-java`, on the DevCapsule surface `intellij`.
Its recording and its presentation are written to
`devcapsule-src/tests/e2e/evidence/springboot-postgres-java/`.

## Goal

Demonstrate a Java backend and web UI workflow inside an isolated **DevCapsule**
container combining **IntelliJ IDEA** (`java-ide`), **OpenJDK 25** + **Maven**
(`java`), **PostgreSQL 17** client tools (`postgresql-client`), and **Chromium**
(`browser-automation`), recording human-paced Java coding in IntelliJ IDEA and
live browser verification against PostgreSQL 17.

## Stack And Capabilities

- **Capabilities:** `java-ide`, `java`, `postgresql-client`, `browser-automation`
- **Database:** PostgreSQL 17 (`sprintdb`, table `sprint_items`, `127.0.0.1:15432`)
- **Application server:** Spring Boot `3.4.5` (`<maven.compiler.release>21</maven.compiler.release>`) with fluent `JdbcClient` on `http://127.0.0.1:18085`

## Steps

1. **Open the Maven Spring Boot project in IntelliJ IDEA inside DevCapsule.**
   - *User action:* Launch the project capsule, accept workspace trust if prompted, and display the `capsule-sprint` Maven project on the `1600×1000` capsule desktop.
   - *Expected observation:* IntelliJ IDEA displays the indexed Maven project tree (`pom.xml`, `src/main/java/io/devcapsule/demo/SprintController.java`) with clean syntax highlighting.

2. **Navigate to `SprintController.java` at `@PostMapping("/api/items")`.**
   - *User action:* Open Go to File (`Ctrl+Shift+N`), filter to `SprintController.java`, press `Enter`, jump to line `38` (`Ctrl+G`), and delete the `NOT_IMPLEMENTED` placeholder line (`Ctrl+Y`).
   - *Expected observation:* The editor focuses inside `createItem(@RequestBody CreateItemRequest req)` below the `// Live demo placeholder:` marker.

3. **Type the parameterized PostgreSQL `INSERT ... RETURNING` query using `JdbcClient` and save.**
   - *User action:* Type the fluent `jdbc.sql("INSERT INTO sprint_items ...")` implementation at human cadence and save (`Ctrl+S`).
   - *Expected observation:* `SprintController.java` saves cleanly on disk with zero unresolved symbols or syntax errors.

4. **Verify PostgreSQL 17 and start Spring Boot from IntelliJ's integrated terminal.**
   - *User action:* Open IntelliJ's integrated Terminal (`Alt+F12`) and run `./run-stack.sh` to check PostgreSQL 17 via `psql`, compile offline (`mvn -o -q compile`), and start Spring Boot (`:18085`).
   - *Expected observation:* The terminal prints the PostgreSQL 17 banner, the two seeded rows (`CAP-101`, `CAP-102`), and `STACK_READY: Spring Boot listening on http://127.0.0.1:18085`.

5. **Open the CapsuleSprint web application in Chromium on the capsule desktop.**
   - *User action:* Launch Chromium in `--app=http://127.0.0.1:18085` mode on the capsule X11 display.
   - *Expected observation:* **CapsuleSprint** renders with `Java 25 · Spring Boot`, `PostgreSQL 17 · Connected`, metric cards (`Total: 2`, `Open: 0`, `Resolved: 2`), and `CAP-101` / `CAP-102`.

6. **Create two new sprint items and toggle resolution state in the browser.**
   - *User action:* Focus the item input, type `"Implement Spring Boot JdbcClient endpoint"`, click **Create Item** (`CAP-103`); type `"Verify PostgreSQL 17 transaction durability"`, click **Create Item** (`CAP-104`); then toggle `CAP-103` to resolved.
   - *Expected observation:* `CAP-103` (resolved) and `CAP-104` (open) render immediately, updating the counters to `Total: 4`, `Open: 1`, `Resolved: 3`.

7. **Reload from PostgreSQL and confirm durable rows via `psql` in IntelliJ's terminal.**
   - *User action:* Click **Refresh from DB**, switch to IntelliJ's terminal to run `./query-db.sh`, and return to **CapsuleSprint** for the final poster frame.
   - *Expected observation:* Both `psql` and the browser UI display all four rows (`CAP-101`..`CAP-104`) and their exact `resolved` booleans (`t, t, t, f`).
