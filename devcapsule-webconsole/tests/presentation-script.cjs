// Run the actual presentation page with a small DOM, a clock and a video the
// test drives: the overview, a step shown alone, "Play all", the keys, a
// slide named in the address, the list of presentations, and the refusals.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const scriptSource = fs.readFileSync(path.join(__dirname, '../devcapsule_webconsole/static/presentation.js'), 'utf8');

class Node {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.attributes = {};
    this.children = [];
    this.listeners = {};
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.style = { properties: {}, setProperty(name, value) { this.properties[name] = value; } };
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return key in this.attributes ? this.attributes[key] : null; }
  removeAttribute(key) { delete this.attributes[key]; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  fire(name, event = {}) { for (const callback of this.listeners[name] || []) callback(event); }
}

// A recording the test moves by hand: it never advances on its own.
class Video extends Node {
  constructor() {
    super('video');
    this.currentTime = 0;
    this.playbackRate = 1;
    this.paused = true;
    this.ended = false;
    this.duration = NaN;
  }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
}

function descendants(node) {
  return node.children.flatMap(child => [child, ...descendants(child)]);
}
function textOf(node) {
  return node.textContent + node.children.map(textOf).join('');
}
function byClass(root, name) {
  return descendants(root).filter(node => node.attributes.class === name);
}
function one(root, name) {
  const found = byClass(root, name);
  assert.equal(found.length, 1, `exactly one .${name}`);
  return found[0];
}

const PRESENTATION = {
  schema_version: 1,
  scenario_id: 'sample',
  title: 'A sample with `code`',
  overview: {
    summary: 'What **you** will see, with `psql`.',
    intent: 'Why it exists.',
    illustrates: ['One thing', 'Another *thing*'],
    stack: [{ name: 'Editor', detail: 'An editor' }],
  },
  video: { file: 'scenario-video.webm', poster: 'poster.png', duration: 10 },
  steps: [
    { title: 'Open the editor', action: 'Launch it.', expected: 'It is open.', screenshot: 'step-001.png', start: 0, end: 4,
      captions: [{ start: 0, end: 2, text: 'The editor opens.' }, { start: 2, end: 4, text: 'Trust with `Ctrl+Enter`.' }] },
    { title: 'Run the stack', action: 'Run `./run.sh`.', expected: 'It prints `READY`.', screenshot: 'step-002.png', start: 4, end: 10,
      captions: [{ start: 4, end: 10, text: 'The stack starts.' }] },
  ],
};

function answer(status, body) {
  return { ok: status >= 200 && status < 300, status, text: async () => (typeof body === 'string' ? body : JSON.stringify(body)) };
}

// Load the page at an address and let it render. `frame()` runs the animation
// callbacks waiting now; `elapse()` runs the timers waiting now.
async function open(pathname, hash, responder) {
  const container = new Node('div');
  const fetches = [];
  const hashes = [];
  const frames = new Map();
  const timers = new Map();
  let ticket = 0;
  let ready;
  const documentListeners = {};
  const document = {
    title: '',
    body: { dataset: { page: 'presentation' } },
    createElement: tag => (tag === 'video' ? new Video() : new Node(tag)),
    createTextNode: text => Object.assign(new Node('#text'), { textContent: text }),
    getElementById: id => (id === 'content' ? container : null),
    addEventListener: (name, fn) => { if (name === 'DOMContentLoaded') ready = fn; else documentListeners[name] = fn; },
  };
  const context = {
    document,
    window: { location: { pathname, hash }, history: { replaceState: (state, title, url) => hashes.push(url) } },
    fetch: async (url, options) => { fetches.push({ url, options }); return responder(url); },
    requestAnimationFrame: callback => { frames.set(++ticket, callback); return ticket; },
    cancelAnimationFrame: id => { frames.delete(id); },
    setTimeout: callback => { timers.set(++ticket, callback); return ticket; },
    clearTimeout: id => { timers.delete(id); },
  };
  vm.runInNewContext(scriptSource, context);
  ready();
  for (let turn = 0; turn < 5; turn++) await new Promise(resolve => setImmediate(resolve));
  const drain = queue => () => { const waiting = [...queue.values()]; queue.clear(); waiting.forEach(callback => callback()); };
  return {
    container, document, fetches, hashes,
    frame: drain(frames), elapse: drain(timers), timersWaiting: () => timers.size,
    key: (key, tagName = 'BODY') => {
      const event = { key, target: { tagName }, prevented: false, preventDefault() { this.prevented = true; } };
      documentListeners.keydown(event);
      return event;
    },
    video: () => descendants(container).find(node => node instanceof Video),
  };
}

const FOLDER = '/presentations/e2e/evidence/todo%20run';
const sample = url => (url.endsWith('presentation.json') ? answer(200, PRESENTATION) : answer(404, 'unexpected'));

(async () => {
  // 1. The overview: the document is read from the folder's presentation.json through the raw route,
  //    and the first slide says what the scenario is, why, what it shows and its steps.
  const overview = await open(FOLDER, '', sample);
  assert.deepEqual(overview.fetches.map(call => call.url), ['/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fpresentation.json']);
  assert.equal(overview.fetches[0].options.credentials, 'same-origin');
  assert.equal(overview.document.title, 'A sample with code · DevCapsule console');
  assert.equal(textOf(one(overview.container, 'eyebrow')), 'Recorded scenario · 2 steps · 0:10');
  const slide = one(overview.container, 'slide');
  assert.equal(textOf(descendants(slide).find(node => node.tagName === 'H1')), 'A sample with code');
  assert.equal(textOf(one(overview.container, 'summary')), 'What you will see, with psql.');
  assert.ok(!textOf(slide).includes('`') && !textOf(slide).includes('*'), 'the marks are interpreted, not shown');
  assert.deepEqual(descendants(slide).filter(node => node.tagName === 'CODE').map(textOf), ['code', 'psql']);
  assert.deepEqual(descendants(slide).filter(node => node.tagName === 'H2').map(textOf), ['Why this scenario', 'What it shows', 'The steps']);
  assert.deepEqual(byClass(overview.container, 'link').map(textOf), ['Open the editor', 'Run the stack']);
  assert.equal(one(overview.container, 'still').attributes.src, '/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fposter.png');
  assert.equal(overview.video().attributes.src, '/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fscenario-video.webm');
  assert.equal(textOf(one(overview.container, 'primary')), '▶ Play all');
  assert.equal(overview.video().paused, true);
  const crumbs = one(overview.container, 'crumbs').children.filter(node => node.tagName === 'A');
  assert.deepEqual(crumbs.map(node => node.attributes.href), ['/files', '/files/e2e', '/files/e2e/evidence', '/files/e2e/evidence/todo%20run']);

  // 2. Next goes to the first step, at rest: its script, its screenshot, its address.
  const nextButton = descendants(overview.container).find(node => textOf(node) === 'Next →');
  nextButton.fire('click');
  assert.equal(textOf(one(overview.container, 'eyebrow')), 'Step 1 of 2');
  assert.deepEqual(descendants(one(overview.container, 'slide')).filter(node => node.tagName === 'P').map(textOf),
    ['Step 1 of 2', 'Launch it.', 'It is open.']);
  assert.equal(one(overview.container, 'still').attributes.src, '/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fstep-001.png');
  assert.equal(one(overview.container, 'still').hidden, false);
  assert.equal(overview.hashes.at(-1), '#1');
  assert.equal(textOf(one(overview.container, 'primary')), '▶ Show this step');

  // 3. Show this step plays that step only: from its start, at the slow default, to its end.
  const video = overview.video();
  video.currentTime = 9;
  one(overview.container, 'primary').fire('click');
  assert.deepEqual([video.currentTime, video.playbackRate, video.paused], [0, 0.5, false]);
  assert.equal(one(overview.container, 'still').hidden, true);
  assert.equal(textOf(one(overview.container, 'primary')), '❚❚ Pause');
  video.currentTime = 2.5;
  overview.frame();
  assert.equal(textOf(one(overview.container, 'caption')), 'Trust with Ctrl+Enter.');
  assert.deepEqual(byClass(overview.container, 'moment').map(node => 'aria-current' in node.attributes), [false, true]);
  assert.equal(textOf(one(overview.container, 'time')), '0:03 / 0:04');
  // Pause and resume leave the recording where it was.
  one(overview.container, 'primary').fire('click');
  assert.deepEqual([video.paused, textOf(one(overview.container, 'primary'))], [true, '▶ Resume']);
  one(overview.container, 'primary').fire('click');
  assert.deepEqual([video.paused, video.currentTime], [false, 2.5]);
  video.currentTime = 4;
  overview.frame();
  assert.equal(video.paused, true, 'the step stops at its end');
  assert.equal(textOf(one(overview.container, 'eyebrow')), 'Step 1 of 2', 'and the slide stays');
  assert.equal(textOf(one(overview.container, 'primary')), '↺ Replay this step');
  // A moment plays the step from that caption.
  byClass(overview.container, 'moment')[1].fire('click');
  assert.deepEqual([video.currentTime, video.paused], [2, false]);

  // 4. Play all runs the recording through: the slide follows the time, waits on each new step, and stops at the end.
  const all = await open(FOLDER, '', sample);
  const recording = all.video();
  descendants(all.container).find(node => textOf(node) === '▶ Play all' && node.attributes.class === 'quiet').fire('click');
  assert.deepEqual([recording.currentTime, recording.paused], [0, false]);
  all.frame();
  assert.equal(textOf(one(all.container, 'eyebrow')), 'Step 1 of 2');
  assert.deepEqual([recording.paused, all.timersWaiting()], [true, 1], 'waits on the new step');
  all.elapse();
  assert.equal(recording.paused, false);
  recording.currentTime = 5;
  all.frame();
  assert.equal(textOf(one(all.container, 'eyebrow')), 'Step 2 of 2');
  assert.equal(textOf(one(all.container, 'caption')), 'The stack starts.');
  assert.equal(all.hashes.at(-1), '#2');
  assert.equal(recording.paused, true);
  all.elapse();
  recording.currentTime = 10;
  all.frame();
  assert.deepEqual([recording.paused, all.timersWaiting()], [true, 0]);
  assert.equal(textOf(one(all.container, 'primary')), '↺ Replay this step');
  // Leaving a slide stops what was playing.
  one(all.container, 'primary').fire('click');
  assert.equal(recording.paused, false);
  byClass(all.container, 'chip')[0].fire('click');
  assert.deepEqual([recording.paused, textOf(one(all.container, 'eyebrow'))], [true, 'Recorded scenario · 2 steps · 0:10']);

  // 5. The keys of a deck, and the fields that keep their own.
  const keyed = await open(FOLDER, '', sample);
  keyed.key('ArrowRight');
  keyed.key('ArrowRight');
  keyed.key('ArrowRight');
  assert.equal(textOf(one(keyed.container, 'eyebrow')), 'Step 2 of 2', 'the last slide is the end');
  keyed.key('ArrowLeft');
  assert.equal(textOf(one(keyed.container, 'eyebrow')), 'Step 1 of 2');
  assert.equal(keyed.key(' ').prevented, true);
  assert.equal(keyed.video().paused, false);
  keyed.key('ArrowRight', 'SELECT');
  assert.equal(textOf(one(keyed.container, 'eyebrow')), 'Step 1 of 2', 'a focused field keeps the arrows');
  keyed.key(' ', 'BUTTON');
  assert.equal(keyed.video().paused, false, 'a focused button keeps the space bar');
  keyed.key('Home');
  assert.equal(textOf(one(keyed.container, 'primary')), '▶ Play all');

  // 6. The address names the slide.
  const second = await open(FOLDER, '#2', sample);
  assert.equal(textOf(one(second.container, 'eyebrow')), 'Step 2 of 2');

  // 7. /presentations alone lists the project's presentations: a card for each folder the search
  //    found, saying what its document says, and the refusal in place of a card whose document is broken.
  const listed = await open('/presentations', '', url => {
    if (url === '/api/project/presentations') return answer(200, { folders: ['e2e/evidence/todo run', 'e2e/broken'], complete: true });
    if (url === '/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fpresentation.json') return answer(200, PRESENTATION);
    return answer(200, { schema_version: 1 });
  });
  assert.equal(listed.document.title, 'Presentations · DevCapsule console');
  const cards = byClass(listed.container, 'show');
  assert.equal(cards.length, 1);
  assert.equal(cards[0].attributes.href, '/presentations/e2e/evidence/todo%20run');
  assert.equal(cards[0].children[0].attributes.src, '/api/project/raw?path=e2e%2Fevidence%2Ftodo%20run%2Fposter.png');
  assert.deepEqual(cards[0].children.slice(1).map(textOf),
    ['A sample with code', 'What you will see, with psql.', '2 steps · 0:10 · e2e/evidence/todo run']);
  const refusedCard = one(listed.container, 'show refused');
  assert.equal(textOf(refusedCard.children[0]), 'e2e/broken');
  assert.ok(textOf(refusedCard).includes('e2e/broken/presentation.json does not follow the presentation contract'));
  assert.equal(byClass(listed.container, 'notice').length, 0);
  // A project without one says how a folder becomes one; a search cut short says a presentation may be missing.
  const none = await open('/presentations/', '', () => answer(200, { folders: [], complete: false }));
  assert.equal(byClass(none.container, 'show').length, 0);
  const notices = byClass(none.container, 'notice').map(textOf);
  assert.equal(notices.length, 2);
  assert.ok(notices[0].startsWith('The project is too large to search whole'));
  assert.ok(notices[1].startsWith('This project has no presentation yet.'));
  const unlisted = await open('/presentations', '', () => answer(403, 'cannot read the project\n'));
  assert.equal(textOf(one(unlisted.container, 'failure')), '/api/project/presentations: cannot read the project');

  // 8. A folder without presentation.json says so and builds no player.
  const absent = await open('/presentations/docs', '', () => answer(404, "no file at 'docs/presentation.json' in the project\n"));
  const refusal = one(absent.container, 'failure');
  assert.equal(textOf(refusal), 'There is no presentation here: docs has no presentation.json.');
  assert.equal(absent.video(), undefined);

  // 9. A document that breaks the contract is refused whole, with every breach named.
  const broken = JSON.parse(JSON.stringify(PRESENTATION));
  delete broken.title;
  broken.video.file = '../outside.webm';
  broken.steps[1].start = 3;
  broken.steps[0].captions[1].end = 5;
  const refused = await open(FOLDER, '', () => answer(200, broken));
  assert.equal(textOf(one(refused.container, 'failure')), [
    'e2e/evidence/todo run/presentation.json does not follow the presentation contract:',
    'title is missing',
    'video.file is not a file name inside the folder',
    'step 1, caption 2 overlaps its neighbour or leaves its step',
    'step 2 starts before the step before it ends',
  ].join('\n'));
  assert.equal(refused.video(), undefined);
  const garbled = await open(FOLDER, '', () => answer(200, 'not json'));
  assert.ok(textOf(one(garbled.container, 'failure')).startsWith('e2e/evidence/todo run/presentation.json is not JSON'));

  console.log('Presentation script: overview, one step, play all, keys, addressed slide, list, absence and refusals passed.');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
