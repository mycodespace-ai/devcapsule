// The console's script. Each page names itself with data-page on <body>;
// the matching renderer fetches the page's document from /api and builds the
// DOM with textContent. Records use markdown-it with raw HTML disabled;
// Graphviz output is displayed as an image, never inserted into the DOM.
// The presentation page has its own script, presentation.js, beside this one,
// which gives it the console bar and the bell.
(function () {
  "use strict";

  async function api(path) {
    const response = await fetch(path, { credentials: "same-origin" });
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    if (!response.ok) {
      const detail = body && body.error ? body.error + (body.stderr ? "\n" + body.stderr : "") : "HTTP " + response.status;
      throw new Error(path + ": " + detail);
    }
    return body;
  }

  function el(tag, attributes, children) {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes || {})) {
      if (name === "text") node.textContent = value;
      else node.setAttribute(name, value);
    }
    for (const child of children || []) node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    return node;
  }

  function scalar(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function facts(pairs) {
    const list = el("dl", { class: "facts" });
    for (const [label, value] of pairs) {
      list.appendChild(el("dt", { text: label }));
      list.appendChild(el("dd", { text: scalar(value) }));
    }
    return list;
  }

  function table(columns, rows) {
    const head = el("tr", {}, columns.map((column) => el("th", { text: column.label })));
    const body = rows.map((row) => el("tr", {}, columns.map((column) =>
      el("td", { text: scalar(typeof column.key === "function" ? column.key(row) : row[column.key]) }))));
    return el("table", { class: "data" }, [el("thead", {}, [head]), el("tbody", {}, body)]);
  }

  function tree(value) {
    if (value === null || typeof value !== "object") return el("span", { class: "scalar", text: scalar(value) });
    const entries = Array.isArray(value) ? value.map((item, index) => [String(index), item]) : Object.entries(value);
    return el("ul", { class: "tree" }, entries.map(([key, item]) => {
      const child = el("li", {}, [el("span", { class: "key", text: key + ": " })]);
      child.appendChild(tree(item));
      return child;
    }));
  }

  function components(object) {
    return table([{ key: "name", label: "Component" }, { key: "version", label: "Version" }],
      Object.entries(object || {}).map(([name, version]) => ({ name, version })));
  }

  function fail(container, error) {
    container.replaceChildren(el("div", { class: "failure", text: String(error.message || error) }));
  }

  function section(container, title, node) {
    container.appendChild(el("h2", { text: title }));
    container.appendChild(node);
  }

  // The configuration channel (answer 7 of the CLI UX work order): a request is
  // the tokens of one `devcapsule project config` command, written for the
  // launcher, which records it for the next launch, refuses it, or keeps it for
  // the user's confirmation on the host when it widens what the capsule reaches.
  function requestForms(pending) {
    const list = el("div", { class: "requests" });
    const note = el("p", { class: "notice",
      text: "Sending a request does not apply it. Read the launcher's outcome below. Changes affect the next launch; "
        + "this running capsule stays unchanged. Access grants, forgotten denials, host environment bindings, trust, mounts "
        + "and Docker options need confirmation on the host. Anything inside this capsule can write requests." });
    list.appendChild(note);
    for (const row of pending) {
      if (row.kind === "console") {
        list.appendChild(el("p", { text: row.pending + ". Confirm on the host: " + row.command }));
        continue;
      }
      list.appendChild(requestForm(row.kind + " " + row.name + ": " + row.pending, row.request || ""));
    }
    list.appendChild(requestForm("Another change", ""));
    return list;
  }

  function requestForm(label, prefilled) {
    const input = el("input", { type: "text", name: "command", value: prefilled, size: "60",
      placeholder: "config tokens, for example: ide python-ide" });
    const button = el("button", { type: "submit", text: "Send to the launcher" });
    const status = el("span", { class: "request-status" });
    const form = el("form", { class: "request" }, [el("label", { text: label }), el("code", { text: "config " }), input, button, status]);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      status.textContent = "sending…";
      try {
        const response = await fetch("/api/configuration/requests", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: input.value }),
        });
        if (!response.ok) {
          status.textContent = "refused: " + (await response.text()).trim();
          return;
        }
        const written = (await response.json()).request;
        status.textContent = "sent as " + written.id + (written.widening ? "; waits for your confirmation on the host" : "");
        const requests = document.getElementById("requests");
        if (requests) await refreshRequests(requests);
      } catch (error) {
        status.textContent = "failed: " + error.message;
      } finally {
        button.disabled = false;
      }
    });
    return form;
  }

  async function refreshRequests(container, attempt = 0) {
    const listing = await api("/api/configuration/requests");
    container.replaceChildren();
    if (!listing.requests.length) {
      container.appendChild(el("p", { text: "Nothing asked on the console since launch." }));
      return;
    }
    container.appendChild(table([
      { key: "id", label: "Request" }, { key: "command", label: "Command" }, { key: "requested", label: "Asked" },
      { key: (row) => row.result ? row.result.status : "waiting for the launcher", label: "Outcome" },
      { key: (row) => row.result ? row.result.text : "", label: "What the launcher said" },
    ], listing.requests));
    if (listing.requests.some((row) => !row.result)) {
      if (attempt >= 60) {
        container.appendChild(el("p", { class: "notice", text:
          "The launcher has not answered. No change is confirmed. Inspect configuration on the host before sending again." }));
      } else {
        setTimeout(() => refreshRequests(container, attempt + 1).catch((error) => {
          container.appendChild(el("p", { class: "failure", text: "Cannot read the launcher outcome: " + error.message }));
        }), 2000);
      }
    }
  }

  const pages = {
    async home(container) {
      const identity = await api("/api/identity");
      const project = identity.project || {};
      const checkout = identity.checkout || {};
      const base = identity.base || {};
      const set = identity["version-set"] || {};
      container.replaceChildren(facts([
        ["Context", identity.context],
        ["Project", [project.creator, project.slug].filter(Boolean).join("/") + (project.name ? " — " + project.name : "")],
        ["Checkout", checkout.name ? checkout.name + " at " + (checkout["launcher-path"] || "") : checkout["launcher-path"]],
        ["Runtime path", checkout["runtime-path"]],
        ["Version set", set.identity ? set.identity + " (" + set.origin + ")" : null],
        ["Base", base.reference ? base.reference + (base["build-mnemonic"] ? " — " + base["build-mnemonic"] : "") : null],
        ["Console", identity["console-version"]],
      ]));
    },

    async configuration(container) {
      const listing = await api("/api/configuration");
      const checkout = listing.checkout || {};
      container.replaceChildren();
      if (listing.rows) {
        const atLaunch = listing.at ? "At launch, " + listing.at : null;
        container.appendChild(facts([
          ["Context", atLaunch || listing.context],
          ["Checkout", checkout.name],
          ["Launcher path", checkout["launcher-path"]],
          ["Checkout input", checkout.input],
        ]));
        section(container, atLaunch ? "What the launcher derived at launch" : "What the next launch uses", table([
          { key: "kind", label: "Kind" }, { key: "name", label: "Name" }, { key: "effective", label: "Effective" },
          { key: "source", label: "Source" }, { key: "pending", label: "Pending" },
        ], listing.rows));
        const exposures = listing.rows.filter((row) => row.exposure);
        if (exposures.length) {
          section(container, "Host access: what each grant permits", table([
            { key: "name", label: "Access" }, { key: "exposure", label: "DevCapsule exposure" },
            { key: (row) => row.reason || "No project recommendation", label: "Project reason" },
          ], exposures));
        }
        const pending = listing.rows.filter((row) => row.pending);
        if (listing.channel) {
          section(container, "Pending, next launch", requestForms(pending));
          const requests = el("div", { id: "requests" });
          section(container, "Asked on the console since launch", requests);
          await refreshRequests(requests);
        } else {
          section(container, "Pending, next launch", el("p", { class: "notice",
            text: "This capsule has no usable configuration channel. Inspect or change configuration on the host: "
              + (listing["launcher-command"] || "devcapsule project config show") }));
        }
        return;
      }
      container.appendChild(el("p", { class: "notice",
        text: "Read-only launcher configuration for the next launch. Host paths and permissions are recorded choices, not observations of this session." }));
      container.appendChild(facts([
        ["Context", listing.context],
        ["Checkout", checkout.name],
        ["Launcher path", checkout["launcher-path"]],
        ["Runtime path", checkout["runtime-path"]],
      ]));
      section(container, "The mounted checkout record", tree(checkout.record));
      section(container, "To change configuration, outside this capsule", el("p", {}, [el("code", { text: listing["launcher-command"] })]));
    },

    async versions(container) {
      const document_ = await api("/api/versions");
      container.replaceChildren();
      const describe = (set) => {
        const block = el("div");
        block.appendChild(facts([["Version set", set.identity], ["Origin", set.origin], ["Platform", set.platform], ["Base", set.base],
          ["Local base override", set["local-base-override"]]].filter(([, value]) => value !== undefined)));
        block.appendChild(components(set.components));
        return block;
      };
      if (document_.context === "running capsule") {
        section(container, "Running session", describe(document_.running));
        if (document_["next-launch"]) {
          section(container, "Selected for next launch", describe(document_["next-launch"]));
          container.appendChild(el("p", { class: "notice", text: document_["selection-changed"]
            ? "Selection has changed; this running session remains on its launch-time version set."
            : "Same software selection as this session." }));
        } else {
          section(container, "Selected for next launch", el("p", { class: "failure", text: "Unavailable: " + document_["next-launch-unavailable"] }));
        }
        section(container, "To inspect or change the selection, outside this capsule", el("p", {}, [el("code", { text: document_["launcher-command"] })]));
        return;
      }
      section(container, "Selected for the next launch", describe(document_.selected));
      const recommendation = document_["project-recommendation"];
      if (recommendation) {
        container.appendChild(el("p", { class: "notice", text: "Project recommendation: " + recommendation.status + (recommendation.detail ? " — " + recommendation.detail : "") }));
      }
      const validation = document_.validation || {};
      section(container, "Validation", el("ul", {}, [
        ...(validation.evidence || []).map((item) => el("li", { text: "DevCapsule validation: " + item })),
        ...(validation["not-yet-validated"] || []).map((item) => el("li", { text: "Not yet validated: " + item })),
      ]));
      const use = document_["local-use"] || {};
      container.appendChild(el("p", { text: use["zero-exit-launch-recorded"]
        ? "Local use: a zero-exit launch is recorded (not comprehensive validation)." : "Local use: no successful launch recorded." }));
    },

    async project(container) {
      const info = await api("/api/project");
      const project = info.project || {};
      const checkout = info.checkout || {};
      container.replaceChildren(facts([
        ["Context", info.context],
        ["Project", [project.creator, project.slug].filter(Boolean).join("/") + (project.name ? " — " + project.name : "")],
        ["Checkout", checkout.name],
        ["Launcher path", checkout["launcher-path"]],
        ["Runtime path", checkout["runtime-path"]],
        ["Base", info.base ? [info.base.reference, info.base["build-mnemonic"]].filter(Boolean).join(" — ") : null],
        ["Running selection", info["running-selection"]],
      ].filter(([, value]) => value !== undefined)));
      section(container, "Components", components(info.components));
      if (info["next-launch-components"]) section(container, "Components selected for the next launch", components(info["next-launch-components"]));
      section(container, "Environment", table([
        { key: "name", label: "Variable" }, { key: "value", label: "Value" }, { key: "purpose", label: "Purpose" }, { key: "source", label: "Source" },
      ], info.environment || []));
      section(container, "Persistence", table([
        { key: "name", label: "Name" }, { key: "path", label: "Path in the capsule" }, { key: "backing", label: "Backing on the host" },
        { key: "kind", label: "Kind" }, { key: "scope", label: "Scope" }, { key: "lifecycle", label: "Lifecycle" },
      ], info.persistence || []));
      section(container, "Temporary", el("ul", {}, (info.temporary || []).map((item) => el("li", { text: scalar(item) }))));
      section(container, "Notes", el("ul", {}, (info.notes || []).map((item) => el("li", { text: item }))));
    },
  };

  function bytes(value) {
    if (value === null || value === undefined) return "—";
    const units = ["B", "KiB", "MiB", "GiB", "TiB"];
    let number = value, unit = 0;
    while (number >= 1024 && unit < units.length - 1) { number /= 1024; unit += 1; }
    return (unit === 0 ? number : number.toFixed(1)) + " " + units[unit];
  }

  function meter(label, value, percent, detail) {
    const fill = el("span");
    if (percent !== null && percent !== undefined) {
      fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
      if (percent >= 90) fill.classList.add("hot");
    }
    return el("div", { class: "meter" }, [
      el("div", { class: "label", text: label }),
      el("div", { class: "value", text: value }),
      el("div", { class: "bar" }, [fill]),
      el("div", { class: "detail", text: detail }),
    ]);
  }

  pages.processes = async function (container) {
    const REFRESH_MS = 3000;
    let paused = false;
    let timer = null;
    let refreshing = false;
    let lastStatus = "Loading…";
    const meters = el("div", { class: "meters" });
    const status = el("span", { text: "Loading…" });
    const button = el("button", { type: "button", text: "Pause" });
    const table = el("div");
    button.addEventListener("click", () => {
      paused = !paused;
      button.textContent = paused ? "Resume" : "Pause";
      if (timer !== null) { clearTimeout(timer); timer = null; }
      status.textContent = lastStatus + (paused ? " · paused" : "");
      if (!paused) refresh();
    });
    container.replaceChildren(meters, el("div", { class: "toolbar" }, [button, status]), table);

    async function refresh() {
      if (paused || refreshing) return;
      refreshing = true;
      if (timer !== null) { clearTimeout(timer); timer = null; }
      try {
        const [resources, listing] = await Promise.all([api("/api/resources"), api("/api/processes")]);
        if (paused) return;
        const cpu = resources.cpu || {}, memory = resources.memory || {}, pids = resources.pids || {};
        meters.replaceChildren(
          meter("CPU", cpu.percent === null || cpu.percent === undefined ? "—" : cpu.percent + " %", cpu.percent,
            resources.available
              ? "of " + cpu["available-cpus"] + (cpu["limit-cpus"] ? " CPUs (cgroup quota)" : " CPUs (no readable quota)") +
                "; " + (cpu["usage-seconds"] === null ? "" : cpu["usage-seconds"] + " s used since start")
              : "the capsule's cgroup is not readable here"),
          meter("Memory", bytes(memory["current-bytes"]), memory.percent,
            (memory["limit-bytes"] != null ? "of " + bytes(memory["limit-bytes"]) + " limit" : "limit unavailable or unlimited") +
            (memory["anon-bytes"] !== null && memory["anon-bytes"] !== undefined
              ? "; anonymous " + bytes(memory["anon-bytes"]) + ", file " + bytes(memory["file-bytes"]) : "")),
          meter("Tasks (threads)", scalar(pids.current), pids.current != null && pids.max > 0 ? (pids.current / pids.max) * 100 : null,
            (pids.max != null ? "of " + pids.max + " task limit" : "limit unavailable or unlimited") +
            "; " + listing.count + " processes listed"),
        );
        table.replaceChildren(table_(listing.processes));
        lastStatus = "Sampled " + resources["sampled-at"] + " over " + resources["interval-seconds"] + " s";
        status.textContent = lastStatus;
      } catch (error) {
        if (!paused) {
          meters.replaceChildren();
          lastStatus = "Refresh failed";
          status.textContent = lastStatus;
          fail(table, error);
        }
      } finally {
        refreshing = false;
        if (!paused) timer = setTimeout(refresh, REFRESH_MS);
      }
    }

    function table_(rows) {
      // Only the command wraps; every other column keeps its word whole.
      const columns = [
        { key: "pid", label: "PID", class: "num" }, { key: "user", label: "User", class: "keep" },
        { key: "name", label: "Name", class: "keep" }, { key: "cpu-percent", label: "CPU %", class: "num" },
        { key: (row) => bytes(row["rss-bytes"]), label: "RSS", class: "num" },
        { key: "status", label: "Status", class: "keep" }, { key: "command", label: "Command", class: "" },
      ];
      const head = el("tr", {}, columns.map((column) => el("th", { class: column.class, text: column.label })));
      const body = rows.map((row) => el("tr", {}, columns.map((column) =>
        el("td", { class: column.class, text: scalar(typeof column.key === "function" ? column.key(row) : row[column.key]) }))));
      return el("table", { class: "data" }, [el("thead", {}, [head]), el("tbody", {}, body)]);
    }

    await refresh();
  };

  async function text(path) {
    const response = await fetch(path, { credentials: "same-origin" });
    const body = await response.text();
    if (!response.ok) throw new Error(path + ": " + (body.trim() || "HTTP " + response.status));
    return body;
  }

  // A relative link inside a record names a file in the project; resolve it
  // against the record's directory. Absolute URLs, root paths and fragments
  // are left alone. Decode URL paths once before resolving dot components.
  // An invalid local target becomes an inert fragment, never a browser-relative URL.
  function resolveRecordLink(from, href) {
    if (!href || /^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("/") || href.startsWith("#")) return null;
    const match = /^([^?#]*)(\?[^#]*)?(#.*)?$/.exec(href);
    const fragment = match[3] || "";
    let target;
    try { target = decodeURIComponent(match[1]); } catch (_) { return { path: null, fragment: "" }; }
    if (target.includes("\0") || target.startsWith("/")) return { path: null, fragment: "" };
    if (target === "") return { path: from, fragment };
    const directory = from.includes("/") ? from.slice(0, from.lastIndexOf("/")).split("/") : [];
    const parts = directory.concat(target.split("/"));
    const resolved = [];
    for (const part of parts) {
      if (part === "" || part === ".") continue;
      if (part === "..") { if (resolved.length === 0) return { path: null, fragment: "" }; resolved.pop(); continue; }
      resolved.push(part);
    }
    return { path: resolved.join("/"), fragment };
  }

  function rawRecordUrl(resolved) {
    return "/api/project/raw?path=" + encodeURIComponent(resolved.path) + resolved.fragment;
  }

  // Where a link in a record leads: a Markdown file to Records, anything else
  // to its /files address, where the Files page plays a recording and sends
  // every other file on to the raw route.
  function recordUrl(resolved) {
    if (resolved.path === null) return "#";
    const segments = resolved.path.split("/").map(encodeURIComponent).join("/");
    return (resolved.path.toLowerCase().endsWith(".md") ? "/records/" : "/files/") + segments + resolved.fragment;
  }

  function recordRenderer(from) {
    const md = window.markdownit({ html: false, linkify: false, typographer: false });
    const fence = md.renderer.rules.fence;
    md.renderer.rules.fence = (tokens, index, options, env, self) => {
      const token = tokens[index];
      if (token.info.trim().split(/\s+/)[0] === "dot") {
        return '<div class="diagram"><pre class="dot-source">' + md.utils.escapeHtml(token.content) + "</pre></div>\n";
      }
      return fence(tokens, index, options, env, self);
    };
    const rewrite = (attribute) => (tokens, index, options, env, self) => {
      const token = tokens[index];
      const value = token.attrGet(attribute);
      const resolved = resolveRecordLink(from, value);
      if (resolved !== null) token.attrSet(attribute, recordUrl(resolved));
      return self.renderToken(tokens, index, options);
    };
    md.renderer.rules.link_open = rewrite("href");
    const image = md.renderer.rules.image;
    md.renderer.rules.image = (tokens, index, options, env, self) => {
      const resolved = resolveRecordLink(from, tokens[index].attrGet("src"));
      if (resolved !== null) tokens[index].attrSet("src", resolved.path === null ? "" : rawRecordUrl(resolved));
      return image(tokens, index, options, env, self);
    };
    // Heading IDs make the records' table-of-contents links usable. Read
    // inline text, including code and image labels, without formatting marks.
    md.core.ruler.push("record_heading_ids", (state) => {
      const used = new Set();
      for (let index = 0; index < state.tokens.length; index++) {
        const token = state.tokens[index];
        if (token.type !== "heading_open") continue;
        const inline = state.tokens[index + 1];
        const label = (inline.children || []).map((child) =>
          ["text", "code_inline", "image"].includes(child.type) ? child.content :
            ["softbreak", "hardbreak"].includes(child.type) ? " " : "").join("");
        const base = label.toLowerCase().replace(/[^\p{L}\p{M}\p{N}_\-\s]/gu, "").replace(/\s/g, "-");
        let id = base;
        for (let suffix = 1; used.has(id); suffix++) id = base + "-" + suffix;
        used.add(id);
        token.attrSet("id", "record-heading-" + id);
      }
    });
    return md;
  }

  function scrollToRecordFragment(article) {
    let fragment;
    try { fragment = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return; }
    if (!fragment) return;
    // Prefix IDs to avoid collisions with the console's own DOM identifiers.
    const target = document.getElementById("record-heading-" + fragment);
    if (target && article.contains(target)) target.scrollIntoView();
  }

  async function drawDiagrams(container) {
    const sources = Array.from(container.querySelectorAll(".diagram pre.dot-source"));
    if (sources.length === 0) return;
    let viz;
    try { viz = await window.Viz.instance(); } catch (error) {
      for (const source of sources) source.replaceWith(el("div", { class: "diagram-error", text: "Graphviz did not load: " + error.message }));
      return;
    }
    for (const source of sources) {
      try {
        // DOT URL/href attributes can contain javascript: URLs. SVG image
        // mode disables scripts, links and external resources by construction.
        const svg = viz.renderString(source.textContent, { format: "svg", engine: "dot" });
        const drawing = el("img", {
          src: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
          alt: "Graphviz diagram",
        });
        // Establish the image size before the page scrolls to a heading.
        await drawing.decode();
        source.replaceWith(drawing);
      } catch (error) {
        source.replaceWith(el("div", { class: "diagram-error", text: "DOT did not render: " + error.message }), source);
      }
    }
  }

  pages.records = async function (container) {
    const path = decodeURIComponent(window.location.pathname.replace(/^\/records\/?/, "")) || "index.md";
    // Breadcrumbs: the front page, then each directory, then the file.
    const crumbs = el("p", { class: "crumbs" });
    crumbs.appendChild(el("a", { href: "/records", text: "index.md" }));
    if (path !== "index.md") {
      path.split("/").forEach((part) => {
        crumbs.appendChild(document.createTextNode(" › "));
        crumbs.appendChild(el("span", { text: part }));
      });
    }
    crumbs.appendChild(document.createTextNode(" · "));
    crumbs.appendChild(el("a", { href: "/api/project/raw?path=" + encodeURIComponent(path), text: "raw" }));
    const article = el("article", { class: "record" });
    container.replaceChildren(crumbs, article);
    document.getElementById("record-path").textContent = path;
    document.title = path + " · DevCapsule console";
    const source = await text("/api/project/file?path=" + encodeURIComponent(path));
    article.innerHTML = recordRenderer(path).render(source);
    await drawDiagrams(article);
    scrollToRecordFragment(article);
    window.addEventListener("hashchange", () => scrollToRecordFragment(article));
    // Clicking the current fragment again does not emit hashchange.
    article.addEventListener("click", (event) => {
      const link = event.target.closest && event.target.closest("a[href]");
      if (link && link.hash && link.href === window.location.href) scrollToRecordFragment(article);
    });
  };

  function encodeSegments(path) {
    return path.split("/").map(encodeURIComponent).join("/");
  }

  function rawFileUrl(path) {
    return "/api/project/raw?path=" + encodeURIComponent(path);
  }

  // Whether a file is played by this page. `type` is the media type the tree
  // route gives for a file entry; the server is the one place that decides
  // what a file is served as. Chrome refuses to play a recording opened as a
  // raw document, because the raw route's policy forbids that document every
  // fetch, its own player's included; an element in a console page is not
  // under that policy.
  function played(type) {
    return typeof type === "string" && (type.startsWith("video/") || type.startsWith("audio/"));
  }

  // Where a file opens: a Markdown file in Records, a recording on its own
  // /files address, anything else as the raw file. Without `type` the answer
  // for a recording is the raw address.
  function fileViewUrl(path, type) {
    if (path.toLowerCase().endsWith(".md")) return "/records/" + encodeSegments(path);
    return played(type) ? "/files/" + encodeSegments(path) : rawFileUrl(path);
  }

  // The breadcrumbs of a project path: every directory links to its listing.
  // `file`, when given, is the name that ends the path and is not a link.
  function fileCrumbs(directory, file) {
    const crumbs = el("p", { class: "crumbs" }, [el("a", { href: "/files", text: "project" })]);
    const parts = directory ? directory.split("/") : [];
    parts.forEach((part, index) => {
      crumbs.appendChild(document.createTextNode(" › "));
      crumbs.appendChild(el("a", { href: "/files/" + encodeSegments(parts.slice(0, index + 1).join("/")), text: part }));
    });
    if (file !== undefined) {
      crumbs.appendChild(document.createTextNode(" › "));
      crumbs.appendChild(el("span", { text: file }));
    }
    return crumbs;
  }

  // The media type of the regular file at `path`, read from the listing of
  // the directory that holds it; null when that listing cannot be read or
  // has no such file.
  async function fileType(path) {
    const cut = path.lastIndexOf("/");
    const directory = cut < 0 ? "" : path.slice(0, cut);
    const name = path.slice(cut + 1);
    const response = await fetch(
      directory ? "/api/project/tree?path=" + encodeURIComponent(directory) : "/api/project/tree",
      { credentials: "same-origin" });
    if (!response.ok) return null;
    const entry = (await response.json()).entries.find((candidate) => candidate.kind === "file" && candidate.name === name);
    return entry ? entry.type : null;
  }

  // One recording in the page: its breadcrumbs, the player and the download link.
  function showRecording(container, path, type) {
    const cut = path.lastIndexOf("/");
    const player = el(type.startsWith("video/") ? "video" : "audio",
      { class: "recording", controls: "", preload: "metadata", src: rawFileUrl(path) });
    container.replaceChildren(
      fileCrumbs(cut < 0 ? "" : path.slice(0, cut), path.slice(cut + 1)),
      player,
      el("p", {}, [el("a", { class: "muted", href: rawFileUrl(path) + "&download=1", text: "download" })]));
  }

  pages.files = async function (container) {
    const rawTail = window.location.pathname.replace(/^\/files\/?/, "").replace(/\/+$/, "");
    const requested = rawTail ? rawTail.split("/").map(decodeURIComponent).join("/") : "";
    const heading = document.getElementById("files-title");
    if (heading) heading.textContent = requested || "Files";
    document.title = (requested || "Files") + " · DevCapsule console";
    const treeUrl = requested ? "/api/project/tree?path=" + encodeURIComponent(requested) : "/api/project/tree";
    const response = await fetch(treeUrl, { credentials: "same-origin" });
    const bodyText = await response.text();
    if (!response.ok) {
      // The address names a file: play a recording here, open anything else where it is viewed.
      if (response.status === 404 && requested && bodyText.includes("is not a directory in the project")
          && typeof window.location.replace === "function") {
        const type = await fileType(requested);
        if (played(type)) showRecording(container, requested, type);
        else window.location.replace(fileViewUrl(requested) + (window.location.hash || ""));
        return;
      }
      throw new Error(treeUrl + ": " + (bodyText.trim() || "HTTP " + response.status));
    }
    const listing = JSON.parse(bodyText);
    const directory = listing.path || "";
    const label = directory || "Files";
    if (heading) heading.textContent = label;
    document.title = label + " · DevCapsule console";
    const crumbs = fileCrumbs(directory);
    if (!listing.entries.length) {
      container.replaceChildren(crumbs, el("p", { class: "notice", text: "This directory is empty." }));
      return;
    }
    // A folder that holds a presentation.json is a recorded scenario: offer its slides.
    const presented = listing.entries.some((entry) => entry.kind === "file" && entry.name === "presentation.json");
    const presentation = presented ? [el("p", { class: "notice" }, [
      "This folder is a recorded scenario. ",
      el("a", { href: "/presentations/" + encodeSegments(directory), text: "Open its presentation" }),
      ".",
    ])] : [];
    const head = el("tr", {}, [
      el("th", { text: "Name" }),
      el("th", { class: "num", text: "Size" }),
      el("th", { class: "keep", text: "Modified" }),
    ]);
    const rows = listing.entries.map((entry) => {
      const entryPath = directory ? directory + "/" + entry.name : entry.name;
      const rawUrl = rawFileUrl(entryPath);
      let nameNodes;
      if (entry.kind === "directory") {
        nameNodes = [el("a", { href: "/files/" + encodeSegments(entryPath), text: entry.name + "/" })];
      } else if (entry.kind === "file") {
        nameNodes = [
          el("a", { href: fileViewUrl(entryPath, entry.type), text: entry.name }),
          " · ",
          el("a", { class: "muted", href: rawUrl + "&download=1", text: "download" }),
        ];
      } else if (entry.kind === "link") {
        nameNodes = [el("a", { href: rawUrl, text: entry.name })];
      } else {
        nameNodes = [el("span", { text: entry.name })];
      }
      return el("tr", {}, [
        el("td", {}, nameNodes),
        el("td", { class: "num", text: bytes(entry.size) }),
        el("td", { class: "keep", text: scalar(entry.modified) }),
      ]);
    });
    container.replaceChildren(crumbs, ...presentation,
      el("table", { class: "data" }, [el("thead", {}, [head]), el("tbody", {}, rows)]));
  };

  // Decision pages (deliverable 5): the list, and one decision as a form.
  // The form's submit is the console's one write; everything else reads.
  pages.decisions = async function (container) {
    const id = decodeURIComponent(window.location.pathname.replace(/^\/decisions\/?/, ""));
    if (!id) {
      const listing = await api("/api/decisions");
      if (listing.decisions.length === 0) {
        container.replaceChildren(el("p", { class: "notice", text: "No decision is waiting. An agent asks by writing a decision document into the capsule's decisions directory; see DECISIONS.md in the console's source." }));
        return;
      }
      container.replaceChildren(table([
        { key: (row) => row.title || row.id, label: "Decision" },
        { key: "asked-by", label: "Asked by" }, { key: "asked-at", label: "Asked at" },
        { key: "items", label: "Items", class: "num" },
        { key: (row) => row.error ? "malformed: " + row.error : (row["answered-at"] ? "answered " + row["answered-at"] : "waiting"), label: "State" },
      ], listing.decisions));
      for (const [index, row] of listing.decisions.entries()) {
        const cell = container.querySelectorAll("tbody tr")[index].firstChild;
        cell.replaceChildren(el("a", { href: "/decisions/" + encodeURIComponent(row.id), text: cell.textContent }));
      }
      return;
    }
    const { decision, answer } = await api("/api/decisions/" + encodeURIComponent(id));
    document.title = decision.title + " · DevCapsule console";
    const md = recordRenderer("");
    const head = el("div", {}, [el("h2", { text: decision.title })]);
    head.appendChild(facts([["Asked by", decision["asked-by"]], ["Asked at", decision["asked-at"]],
      ["Answered", answer ? answer["answered-at"] : "not yet"]]));
    const context = el("div", { class: "record" });
    context.innerHTML = md.render(decision.context || "");
    const form = el("form", { class: "decision" });
    for (const item of decision.items) {
      const previous = answer && Object.hasOwn(answer.answers, item.key) ? answer.answers[item.key] : null;
      const block = el("fieldset", { class: "item" }, [el("legend", { text: item.title })]);
      const summary = el("div", { class: "record" });
      summary.innerHTML = md.render(item.summary || "");
      block.appendChild(summary);
      if (item.records.length) {
        block.appendChild(el("p", { class: "crumbs" }, [document.createTextNode("Records: ")].concat(
          item.records.flatMap((record, index) => {
            const resolved = resolveRecordLink("", record);
            const link = el("a", { href: resolved ? recordUrl(resolved) : "#", text: record, target: "_blank" });
            return index ? [document.createTextNode(" · "), link] : [link];
          }))));
      }
      for (const option of item.options) {
        const input = el("input", { type: item.multiple ? "checkbox" : "radio", name: item.key, value: option.key });
        if (previous && previous.chosen.includes(option.key)) input.checked = true;
        const label = el("label", { class: "option" }, [input, el("strong", { text: " " + option.label })]);
        if (option.summary) {
          const text = el("span", { class: "option-summary" });
          text.innerHTML = " " + md.renderInline(option.summary);
          label.appendChild(text);
        }
        block.appendChild(label);
      }
      const note = el("input", { type: "text", name: item.key + ":note", placeholder: "Note for this item (optional)" });
      if (previous && previous.note) note.value = previous.note;
      block.appendChild(el("div", { class: "note" }, [note]));
      form.appendChild(block);
    }
    const overall = el("textarea", { name: ":note", rows: "3", placeholder: "Overall note (optional)" });
    if (answer && answer.note) overall.value = answer.note;
    const submit = el("button", { type: "submit", text: answer ? "Submit again" : "Submit the answer" });
    const result = el("span", { class: "muted" });
    form.appendChild(el("div", { class: "note" }, [overall]));
    form.appendChild(el("div", { class: "toolbar" }, [submit, result]));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const answers = {};
      for (const item of decision.items) {
        const chosen = Array.from(form.querySelectorAll('input[name="' + CSS.escape(item.key) + '"]:checked')).map((input) => input.value);
        const noteValue = form.querySelector('input[name="' + CSS.escape(item.key + ":note") + '"]').value.trim();
        if (chosen.length || noteValue) answers[item.key] = { chosen, note: noteValue };
      }
      submit.disabled = true;
      result.textContent = "Writing…";
      try {
        const response = await fetch("/api/decisions/" + encodeURIComponent(id) + "/answer", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answers, note: overall.value.trim() }),
        });
        const bodyText = await response.text();
        if (!response.ok) throw new Error(bodyText.trim() || "HTTP " + response.status);
        const written = JSON.parse(bodyText).answer;
        result.textContent = "Answer written at " + written["answered-at"] + "; the asking agent reads it from the decisions directory.";
        submit.textContent = "Submit again";
      } catch (error) {
        result.textContent = "Not written: " + error.message;
      } finally {
        submit.disabled = false;
      }
    });
    container.replaceChildren(head, context, form);
  };

  // Notifications: what the checkout's environment tells its human, listed
  // by the runtime CLI with the pending decisions merged in. Read and dismiss
  // go back through the CLI; a decision is settled only on its own page.
  // Set by the bell once it exists, so a page action refreshes the badge at once.
  let refreshBell = async () => {};

  async function notify(id, action) {
    const response = await fetch("/api/notifications/" + encodeURIComponent(id) + "/" + action, {
      method: "POST", credentials: "same-origin",
    });
    if (!response.ok) throw new Error((await response.text()).trim() || "HTTP " + response.status);
  }

  function notificationEntry(entry, md, refresh) {
    const item = el("li", { class: "notification" + (entry.error ? " error" : entry["read-at"] ? "" : " unread") });
    if (entry.error) {
      item.appendChild(el("div", { class: "head" }, [el("span", { class: "kind", text: entry.kind || "file" }),
        el("strong", { text: entry.id })]));
      item.appendChild(el("div", { class: "muted", text: "Malformed: " + entry.error }));
      return item;
    }
    const title = entry.link ? el("a", { href: entry.link, text: entry.title }) : el("strong", { text: entry.title });
    item.appendChild(el("div", { class: "head" }, [el("span", { class: "kind", text: entry.kind }), title]));
    item.appendChild(el("div", { class: "muted", text: entry["posted-by"] + " · " + entry["posted-at"] +
      (entry["read-at"] ? " · read " + entry["read-at"] : "") }));
    if (entry.summary) {
      const summary = el("div", { class: "record" });
      summary.innerHTML = md.render(entry.summary);
      item.appendChild(summary);
    }
    if (entry.kind === "decision") {
      item.appendChild(el("div", { class: "muted", text: "A decision is settled by answering it on its page; its asking agent discards it." }));
      return item;
    }
    const result = el("span", { class: "muted" });
    const buttons = [];
    if (!entry["read-at"]) buttons.push(el("button", { type: "button", text: "Mark read" }));
    buttons.push(el("button", { type: "button", text: "Dismiss" }));
    for (const button of buttons) {
      button.addEventListener("click", async () => {
        const action = button.textContent === "Dismiss" ? "dismiss" : "read";
        for (const other of buttons) other.disabled = true;
        try {
          await notify(entry.id, action);
          await refresh();
          await refreshBell();
        } catch (error) {
          result.textContent = "Not done: " + error.message;
          for (const other of buttons) other.disabled = false;
        }
      });
    }
    item.appendChild(el("div", { class: "toolbar" }, buttons.concat([result])));
    return item;
  }

  pages.notifications = async function (container) {
    const listing = await api("/api/notifications");
    if (listing.notifications.length === 0) {
      container.replaceChildren(el("p", { class: "notice", text: "Nothing is waiting. Agents and tools post with devcapsule project checkout notifications post; decisions appear here while unanswered." }));
      return;
    }
    const md = recordRenderer("");
    const list = el("ul", { class: "notifications" },
      listing.notifications.map((entry) => notificationEntry(entry, md, () => pages.notifications(container))));
    container.replaceChildren(el("p", { class: "muted", text: listing.unread + " unread of " + listing.notifications.length + "." }), list);
  };

  // The bell on every page: the unread count and the newest few, refreshed
  // every half minute. The link opens a dropdown when the script is running.
  function bell() {
    const anchor = document.querySelector("header.console-bar .bell");
    const menu = document.querySelector("header.console-bar .bell-menu");
    if (!anchor || !menu) return;
    const count = anchor.querySelector(".count");
    function showMenu(show) {
      menu.hidden = !show;
      anchor.setAttribute("aria-expanded", String(show));
    }
    showMenu(false);
    async function refresh() {
      try {
        const listing = await api("/api/notifications?unread=1");
        const entries = listing.notifications.filter((entry) => !entry.error);
        count.textContent = String(listing.unread);
        count.hidden = listing.unread === 0;
        anchor.classList.toggle("has-unread", listing.unread > 0);
        anchor.setAttribute("aria-label", "Notifications: " + listing.unread + " unread");
        const items = entries.slice(0, 5).map((entry) => el("a", { href: entry.link || "/notifications" }, [
          el("span", { class: "kind", text: entry.kind }), document.createTextNode(entry.title)]));
        if (items.length === 0) items.push(el("p", { text: "Nothing unread." }));
        items.push(el("a", { class: "more", href: "/notifications", text: "All notifications" }));
        menu.replaceChildren(...items);
      } catch (error) {
        count.hidden = true;
        anchor.classList.toggle("has-unread", false);
        anchor.setAttribute("aria-label", "Notifications unavailable");
        menu.replaceChildren(el("p", { text: "Notifications unavailable: " + error.message }),
          el("a", { class: "more", href: "/notifications", text: "All notifications" }));
      }
    }
    anchor.addEventListener("click", (event) => {
      event.preventDefault();
      showMenu(menu.hidden);
    });
    document.addEventListener("click", (event) => {
      if (!event.target.closest || !event.target.closest(".bell-wrap")) showMenu(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !menu.hidden) {
        showMenu(false);
        anchor.focus();
      }
    });
    refreshBell = refresh;
    refresh();
    setInterval(refresh, 30000);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    const container = document.getElementById("content");
    for (const link of document.querySelectorAll("header nav a")) {
      if (link.getAttribute("href") === window.location.pathname) link.setAttribute("aria-current", "page");
    }
    bell();
    if (page && pages[page] && container) {
      pages[page](container).catch((error) => fail(container, error));
    }
  });
})();
