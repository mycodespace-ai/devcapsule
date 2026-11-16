// The presentation page: a recorded scenario as a deck of slides beside its
// recording. /presentations/<folder> reads <folder>/presentation.json from the
// project (the contract is PRESENTATIONS.md) and shows an overview slide, then
// one slide per step: the script's text, the step's screenshot, and a button
// that plays only that step's part of the one recording. "Play all" runs the
// recording through, changing the slide and the caption as the time passes.
// /presentations alone lists the project's folders that hold a presentation.
//
// The page reads; it writes nothing. Every text is placed with textContent.
(function () {
  "use strict";

  const DATA_FILE = "presentation.json";
  const SCHEMA_VERSION = 1;
  const RAW_ROUTE = "/api/project/raw?path=";
  const LIST_ROUTE = "/api/project/presentations";
  const RATES = [0.5, 0.75, 1];
  const DEFAULT_RATE = 0.5;
  // During "Play all" the recording waits this long on each new step, so its title can be read.
  const HOLD_MILLISECONDS = 1500;
  // A step is over this close to its end: a frame of the recording lasts longer.
  const END_TOLERANCE_SECONDS = 0.02;
  // The recording and its description disagree when their lengths differ by more than this.
  const DURATION_TOLERANCE_SECONDS = 0.5;

  function el(tag, attributes, children) {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes || {})) {
      if (name === "text") node.textContent = value;
      else node.setAttribute(name, value);
    }
    for (const child of children || []) node.appendChild(child);
    return node;
  }

  // The texts of a presentation may mark `code`, **strong** and *emphasis*.
  // Nothing else is interpreted, and every piece becomes a text node.
  const MARK = /(``.+?``|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/;
  function inline(text) {
    return String(text).split(MARK).filter((piece) => piece !== "").map((piece) => {
      if (piece.length > 4 && piece.startsWith("``") && piece.endsWith("``")) return el("code", { text: piece.slice(2, -2).trim() });
      if (piece.length > 2 && piece.startsWith("`") && piece.endsWith("`")) return el("code", { text: piece.slice(1, -1) });
      if (piece.length > 4 && piece.startsWith("**") && piece.endsWith("**")) return el("strong", { text: piece.slice(2, -2) });
      if (piece.length > 2 && piece.startsWith("*") && piece.endsWith("*")) return el("em", { text: piece.slice(1, -1) });
      return document.createTextNode(piece);
    });
  }

  // A file of a presentation's folder, as the raw route serves it.
  function fileUrl(directory, name) {
    return RAW_ROUTE + encodeURIComponent(directory + "/" + name);
  }

  function pageUrl(directory) {
    return "/presentations/" + directory.split("/").map(encodeURIComponent).join("/");
  }

  function stepCount(count) {
    return count === 1 ? "1 step" : count + " steps";
  }

  function clock(seconds) {
    const whole = Math.max(0, Math.round(seconds));
    return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
  }

  // What is wrong with a presentation document, as sentences; empty when it
  // follows the contract. The page shows nothing of a document that does not.
  function problems(doc) {
    const found = [];
    const isText = (value) => typeof value === "string" && value.trim() !== "";
    const isFile = (value) => isText(value) && !value.startsWith("/") && !value.split("/").includes("..");
    const isTime = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
    if (doc === null || typeof doc !== "object" || Array.isArray(doc)) return ["the document is not a JSON object"];
    if (doc.schema_version !== SCHEMA_VERSION) found.push("schema_version is not " + SCHEMA_VERSION);
    if (!isText(doc.title)) found.push("title is missing");
    const overview = doc.overview || {};
    if (!isText(overview.summary)) found.push("overview.summary is missing");
    if (overview.intent !== undefined && !isText(overview.intent)) found.push("overview.intent is not a text");
    if (overview.illustrates !== undefined && !(Array.isArray(overview.illustrates) && overview.illustrates.every(isText))) {
      found.push("overview.illustrates is not a list of texts");
    }
    if (overview.stack !== undefined && !(Array.isArray(overview.stack)
        && overview.stack.every((row) => row && isText(row.name) && isText(row.detail)))) {
      found.push("overview.stack is not a list of name and detail");
    }
    const video = doc.video || {};
    if (!isFile(video.file)) found.push("video.file is not a file name inside the folder");
    if (!isFile(video.poster)) found.push("video.poster is not a file name inside the folder");
    if (!(isTime(video.duration) && video.duration > 0)) found.push("video.duration is not a positive number of seconds");
    if (!Array.isArray(doc.steps) || doc.steps.length === 0) return found.concat(["steps is not a list with at least one step"]);
    let previousEnd = 0;
    doc.steps.forEach((step, index) => {
      const name = "step " + (index + 1);
      if (step === null || typeof step !== "object") { found.push(name + " is not an object"); return; }
      for (const field of ["title", "action", "expected"]) if (!isText(step[field])) found.push(name + ": " + field + " is missing");
      if (!isFile(step.screenshot)) found.push(name + ": screenshot is not a file name inside the folder");
      if (!(isTime(step.start) && isTime(step.end) && step.start < step.end)) {
        found.push(name + ": start and end are not seconds with start before end");
        return;
      }
      if (step.start < previousEnd) found.push(name + " starts before the step before it ends");
      if (isTime(video.duration) && step.end > video.duration) found.push(name + " ends after the recording");
      previousEnd = step.end;
      if (!Array.isArray(step.captions)) { found.push(name + ": captions is not a list"); return; }
      let captionEnd = step.start;
      step.captions.forEach((caption, position) => {
        const label = name + ", caption " + (position + 1);
        if (caption === null || typeof caption !== "object" || !isText(caption.text)
            || !(isTime(caption.start) && isTime(caption.end) && caption.start < caption.end)) {
          found.push(label + " needs a text, and start before end in seconds");
          return;
        }
        if (caption.start < captionEnd || caption.end > step.end) found.push(label + " overlaps its neighbour or leaves its step");
        captionEnd = caption.end;
      });
    });
    return found;
  }

  // The step that is playing at a time of the recording: the last one that
  // has started. Steps are in order and do not overlap (problems checks it).
  function stepIndexAt(steps, time) {
    let index = 0;
    for (let candidate = 0; candidate < steps.length; candidate++) if (steps[candidate].start <= time) index = candidate;
    return index;
  }

  function captionIndexAt(step, time) {
    return step.captions.findIndex((caption) => caption.start <= time && time < caption.end);
  }

  function directoryFromLocation() {
    const tail = window.location.pathname.replace(/^\/presentations\/?/, "").replace(/\/+$/, "");
    return tail ? tail.split("/").map(decodeURIComponent).join("/") : "";
  }

  function crumbs(directory) {
    const trail = el("p", { class: "crumbs" }, [el("a", { href: "/files", text: "project" })]);
    const parts = directory.split("/");
    parts.forEach((part, index) => {
      trail.appendChild(document.createTextNode(" › "));
      trail.appendChild(el("a", { href: "/files/" + parts.slice(0, index + 1).map(encodeURIComponent).join("/"), text: part }));
    });
    return trail;
  }

  // The checked presentation document of a folder below the project root.
  async function read(directory) {
    const path = directory + "/" + DATA_FILE;
    const response = await fetch(fileUrl(directory, DATA_FILE), { credentials: "same-origin" });
    if (response.status === 404) throw new Error("There is no presentation here: " + directory + " has no " + DATA_FILE + ".");
    if (!response.ok) throw new Error(path + ": " + ((await response.text()).trim() || "HTTP " + response.status));
    let doc;
    try { doc = JSON.parse(await response.text()); } catch (error) { throw new Error(path + " is not JSON: " + error.message); }
    const found = problems(doc);
    if (found.length) throw new Error(path + " does not follow the presentation contract:\n" + found.join("\n"));
    return doc;
  }

  // Build the deck for a checked document and wire it. Slide 0 is the
  // overview; slide n is step n. One <video> stays in place for every slide:
  // moving a playing video in the document would stop it.
  function present(container, directory, doc) {
    const steps = doc.steps;
    const duration = doc.video.duration;

    // What the page is doing. `playing` is null at rest, "step" while one step
    // plays to its end, "all" while the recording plays through. `holding` is
    // the timer of the pause on a new step during "all", or null.
    const state = { slide: 0, playing: null, paused: false, finished: false, rate: DEFAULT_RATE, holding: null, frame: null };

    const video = el("video", { preload: "auto", playsinline: "", src: fileUrl(directory, doc.video.file) });
    video.muted = true;
    const still = el("img", { class: "still", alt: "" });
    // The whole resting screen is the button; `pill` is its visible label.
    const pill = el("span", { class: "pill" });
    const overlay = el("button", { type: "button", class: "overlay" }, [pill]);
    const screen = el("div", { class: "screen" }, [video, still, overlay]);
    const caption = el("p", { class: "caption", "aria-live": "polite" });
    const notice = el("p", { class: "notice" });
    notice.hidden = true;
    const primary = el("button", { type: "button", class: "primary" });
    const fill = el("span");
    const progress = el("div", { class: "progress" }, [fill]);
    const time = el("span", { class: "time" });
    const rate = el("select", { "aria-label": "Playback speed" }, RATES.map((value) => {
      const option = el("option", { value: String(value), text: value + "×" });
      option.selected = value === DEFAULT_RATE;
      return option;
    }));
    const layout = el("button", { type: "button", class: "quiet" });
    const transport = el("div", { class: "transport" }, [
      primary, progress, time, el("label", { class: "speed" }, [document.createTextNode("Speed "), rate]), layout,
    ]);
    const stage = el("section", { class: "stage" }, [el("div", { class: "player" }, [screen, caption, transport, notice])]);
    const text = el("section", { class: "slide" });
    const deck = el("div", { class: "deck" }, [text, stage]);

    const previous = el("button", { type: "button", class: "quiet", text: "← Previous" });
    const next = el("button", { type: "button", class: "quiet", text: "Next →" });
    const playAll = el("button", { type: "button", class: "quiet", text: "▶ Play all" });
    const chips = [el("button", { type: "button", class: "chip", text: "Overview" })].concat(
      steps.map((step, index) => el("button", { type: "button", class: "chip", text: String(index + 1), title: step.title })));
    const navigation = el("nav", { class: "deck-nav", "aria-label": "Slides" }, [
      previous, el("span", { class: "chips" }, chips), next, playAll,
    ]);
    // The captions of the slide's step, as the buttons under "Moments".
    let moments = [];

    function scope() {
      return state.slide === 0 ? { start: 0, end: duration } : steps[state.slide - 1];
    }

    function heading(label) {
      return el("h2", { text: label });
    }

    function overviewSlide() {
      const overview = doc.overview;
      const nodes = [
        el("p", { class: "eyebrow", text: "Recorded scenario · " + stepCount(steps.length) + " · " + clock(duration) }),
        el("h1", {}, inline(doc.title)),
        el("p", { class: "summary" }, inline(overview.summary)),
      ];
      if (overview.intent) nodes.push(heading("Why this scenario"), el("p", {}, inline(overview.intent)));
      if (overview.illustrates && overview.illustrates.length) {
        nodes.push(heading("What it shows"), el("ul", {}, overview.illustrates.map((item) => el("li", {}, inline(item)))));
      }
      nodes.push(heading("The steps"), el("ol", { class: "outline" }, steps.map((step, index) => {
        const link = el("button", { type: "button", class: "link" }, inline(step.title));
        link.addEventListener("click", () => show(index + 1));
        return el("li", {}, [link]);
      })));
      if (overview.stack && overview.stack.length) {
        const rows = el("dl", { class: "stack" });
        for (const row of overview.stack) {
          rows.appendChild(el("dt", {}, inline(row.name)));
          rows.appendChild(el("dd", {}, inline(row.detail)));
        }
        nodes.push(el("details", {}, [el("summary", { text: "The stack" }), rows]));
      }
      return nodes;
    }

    function stepSlide(index) {
      const step = steps[index];
      moments = step.captions.map((item) => {
        const moment = el("button", { type: "button", class: "moment" }, [
          el("span", { class: "at", text: clock(item.start - step.start) }),
          el("span", {}, inline(item.text)),
        ]);
        moment.addEventListener("click", () => play("step", item.start));
        return moment;
      });
      return [
        el("p", { class: "eyebrow", text: "Step " + (index + 1) + " of " + steps.length }),
        el("h1", {}, inline(step.title)),
        heading("What the user does"), el("p", {}, inline(step.action)),
        heading("What you should see"), el("p", {}, inline(step.expected)),
        heading("Moments"), el("ol", { class: "moments" }, moments.map((moment) => el("li", {}, [moment]))),
      ];
    }

    function renderSlide() {
      moments = [];
      text.replaceChildren(...(state.slide === 0 ? overviewSlide() : stepSlide(state.slide - 1)));
      chips.forEach((chip, index) => {
        if (index === state.slide) chip.setAttribute("aria-current", "true"); else chip.removeAttribute("aria-current");
      });
      previous.disabled = state.slide === 0;
      next.disabled = state.slide === steps.length;
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", "#" + (state.slide === 0 ? "overview" : state.slide));
      }
    }

    // The caption, the lit moment, the bar and the clock for a time of the
    // recording; null is the slide at rest, before anything has played.
    function paint(now) {
      const range = scope();
      const index = now === null || state.slide === 0 ? -1 : captionIndexAt(range, now);
      if (now === null) {
        caption.replaceChildren(el("span", { class: "hint", text: state.slide === 0
          ? "Play all, or go through the steps one at a time. Captions appear here."
          : "Show this step to watch it happen. Captions appear here." }));
      } else {
        caption.replaceChildren(...(index < 0 ? [] : inline(range.captions[index].text)));
      }
      moments.forEach((moment, position) => {
        if (position === index) moment.setAttribute("aria-current", "true"); else moment.removeAttribute("aria-current");
      });
      const elapsed = now === null ? 0 : Math.min(Math.max(now - range.start, 0), range.end - range.start);
      fill.style.width = (100 * elapsed / (range.end - range.start)) + "%";
      time.textContent = clock(elapsed) + " / " + clock(range.end - range.start);
    }

    function labels() {
      const idle = state.slide === 0 ? "▶ Play all" : state.finished ? "↺ Replay this step" : "▶ Show this step";
      primary.textContent = !state.playing ? idle : state.paused ? "▶ Resume" : "❚❚ Pause";
      pill.textContent = idle;
      playAll.textContent = state.slide === 0 ? "▶ Play all" : "▶ Play all from here";
    }

    function cancelFrame() {
      if (state.frame !== null) cancelAnimationFrame(state.frame);
      state.frame = null;
    }

    function cancelHold() {
      if (state.holding !== null) clearTimeout(state.holding);
      state.holding = null;
    }

    // Follow the recording between its own timeupdate events, which are too
    // far apart to stop a step on its last frame.
    function follow() {
      cancelFrame();
      state.frame = requestAnimationFrame(() => {
        state.frame = null;
        sync();
        if (state.playing && !state.paused && state.holding === null) follow();
      });
    }

    function run() {
      const started = video.play();
      if (started && typeof started.catch === "function") started.catch(() => {});
      follow();
    }

    function halt() {
      cancelHold();
      cancelFrame();
      video.pause();
    }

    // The page's reaction to the recording's time: end the step, or during
    // "all" change the slide and wait on it, then repaint.
    function sync() {
      if (!state.playing) return;
      const now = video.currentTime;
      if (state.playing === "all") {
        const slide = stepIndexAt(steps, now) + 1;
        if (slide !== state.slide) {
          state.slide = slide;
          renderSlide();
          labels();
          cancelFrame();
          video.pause();
          state.holding = setTimeout(() => {
            state.holding = null;
            if (state.playing && !state.paused) run();
          }, HOLD_MILLISECONDS);
        }
      }
      const end = state.playing === "all" ? duration : scope().end;
      paint(now);
      if (now >= end - END_TOLERANCE_SECONDS || video.ended) {
        halt();
        state.playing = null;
        state.finished = true;
        labels();
      }
    }

    function play(mode, from) {
      halt();
      state.playing = mode;
      state.paused = false;
      state.finished = false;
      still.hidden = true;
      overlay.hidden = true;
      video.playbackRate = state.rate;
      video.currentTime = from;
      labels();
      paint(from);
      run();
    }

    // Go to a slide and rest on it: its screenshot, and the button that plays it.
    function show(slide) {
      halt();
      state.slide = Math.min(Math.max(slide, 0), steps.length);
      state.playing = null;
      state.paused = false;
      state.finished = false;
      renderSlide();
      still.setAttribute("src", fileUrl(directory, state.slide === 0 ? doc.video.poster : steps[state.slide - 1].screenshot));
      still.hidden = false;
      overlay.hidden = false;
      labels();
      paint(null);
    }

    function toggle() {
      if (!state.playing) {
        play(state.slide === 0 ? "all" : "step", scope().start);
        return;
      }
      state.paused = !state.paused;
      if (state.paused) halt(); else run();
      labels();
    }

    primary.addEventListener("click", toggle);
    overlay.addEventListener("click", toggle);
    video.addEventListener("click", toggle);
    video.addEventListener("timeupdate", sync);
    // A recording made again without its presentation.json is the likely way
    // for the two to disagree. A recording that does not state its length
    // (the browser reports infinity) cannot be compared.
    function compareLengths() {
      if (!Number.isFinite(video.duration) || Math.abs(video.duration - duration) <= DURATION_TOLERANCE_SECONDS) return;
      notice.textContent = "The recording lasts " + video.duration.toFixed(1) + " s and " + DATA_FILE + " describes "
        + duration.toFixed(1) + " s: the steps and captions may be out of place.";
      notice.hidden = false;
    }
    video.addEventListener("loadedmetadata", () => {
      if (video.videoWidth && video.videoHeight) stage.style.setProperty("--aspect", String(video.videoWidth / video.videoHeight));
      compareLengths();
    });
    video.addEventListener("durationchange", compareLengths);
    video.addEventListener("error", () => {
      notice.textContent = "The recording " + doc.video.file + " could not be loaded from this folder.";
      notice.hidden = false;
    });
    previous.addEventListener("click", () => show(state.slide - 1));
    next.addEventListener("click", () => show(state.slide + 1));
    playAll.addEventListener("click", () => play("all", scope().start));
    chips.forEach((chip, index) => chip.addEventListener("click", () => show(index)));
    rate.addEventListener("change", () => {
      state.rate = Number(rate.value);
      video.playbackRate = state.rate;
    });
    layout.textContent = "Larger video";
    layout.addEventListener("click", () => {
      const wide = deck.getAttribute("class") === "deck";
      deck.setAttribute("class", wide ? "deck wide" : "deck");
      layout.textContent = wide ? "Side by side" : "Larger video";
    });
    // The keys of a deck. A focused field keeps its own keys, and a focused
    // button keeps the space bar, which presses it.
    document.addEventListener("keydown", (event) => {
      const focused = event.target && event.target.tagName;
      if (event.altKey || event.ctrlKey || event.metaKey || ["SELECT", "INPUT", "TEXTAREA"].includes(focused)) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") show(state.slide + 1);
      else if (event.key === "ArrowLeft" || event.key === "PageUp") show(state.slide - 1);
      else if (event.key === "Home") show(0);
      else if (event.key === " " && focused !== "BUTTON") { event.preventDefault(); toggle(); }
    });

    document.title = doc.title.replace(/[`*]/g, "") + " · DevCapsule console";
    container.replaceChildren(crumbs(directory), deck, navigation);
    const named = /^#(\d+)$/.exec(window.location.hash || "");
    show(named ? Number(named[1]) : 0);
  }

  // The project's presentations as cards. Each folder's document is read and
  // checked as its deck would read it, so a card never leads to a refusal.
  async function list(container) {
    const response = await fetch(LIST_ROUTE, { credentials: "same-origin" });
    const body = await response.text();
    if (!response.ok) throw new Error(LIST_ROUTE + ": " + (body.trim() || "HTTP " + response.status));
    const found = JSON.parse(body);
    const cards = await Promise.all(found.folders.map(async (folder) => {
      try {
        const doc = await read(folder);
        return el("a", { class: "show", href: pageUrl(folder) }, [
          el("img", { alt: "", loading: "lazy", src: fileUrl(folder, doc.video.poster) }),
          el("strong", {}, inline(doc.title)),
          el("span", { class: "summary" }, inline(doc.overview.summary)),
          el("span", { class: "meta", text: stepCount(doc.steps.length) + " · " + clock(doc.video.duration) + " · " + folder }),
        ]);
      } catch (error) {
        return el("div", { class: "show refused" }, [
          el("strong", { text: folder }), el("span", { class: "failure", text: String(error.message || error) }),
        ]);
      }
    }));
    const nodes = [
      el("h1", { text: "Presentations" }),
      el("p", { class: "lead", text: "The project's recorded scenarios, as slides beside their recordings." }),
    ];
    if (!found.complete) {
      nodes.push(el("p", { class: "notice", text: "The project is too large to search whole: a presentation may be missing"
        + " from this list. Its folder still opens from Files." }));
    }
    nodes.push(cards.length ? el("div", { class: "shows" }, cards) : el("p", { class: "notice" }, inline(
      "This project has no presentation yet. A folder becomes one when it holds a `" + DATA_FILE + "`, as the evidence"
      + " folder of a recorded end-to-end scenario does.")));
    document.title = "Presentations · DevCapsule console";
    container.replaceChildren(...nodes);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("content");
    if (document.body.dataset.page !== "presentation" || !container) return;
    const directory = directoryFromLocation();
    const shown = directory === "" ? list(container) : read(directory).then((doc) => present(container, directory, doc));
    shown.catch((error) => {
      const failure = el("div", { class: "failure", text: String(error.message || error) });
      container.replaceChildren(...(directory === "" ? [failure] : [crumbs(directory), failure]));
    });
  });
})();
