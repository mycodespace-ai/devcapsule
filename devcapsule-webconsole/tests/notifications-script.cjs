// Exercise the actual notification page and bell, with the vendored Markdown renderer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const staticRoot = path.join(__dirname, '../devcapsule_webconsole/static');
class Node {
  constructor(tag) {
    this.tag = tag; this.attributes = {}; this.children = []; this.listeners = {}; this.classes = new Set();
    this.classList = {toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name)};
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  focus() { this.focused = true; }
}
function descendants(node) { return node.children.flatMap(child => [child, ...descendants(child)]); }
const content = new Node('main'), anchor = new Node('a'), count = new Node('span'), menu = new Node('div');
menu.hidden = true;
anchor.querySelector = selector => { assert.equal(selector, '.count'); return count; };
const handlers = {};
const document = {
  body: {dataset: {page: 'notifications'}},
  createElement: tag => new Node(tag),
  createTextNode: text => Object.assign(new Node('#text'), {textContent: text}),
  getElementById: id => { assert.equal(id, 'content'); return content; },
  querySelector: selector => selector.endsWith(' .bell') ? anchor : menu,
  querySelectorAll: () => [],
  addEventListener: (name, fn) => { handlers[name] = fn; },
};
const entry = (id, extra = {}) => ({id, kind: 'note', title: '<img src=x onerror=bad()>',
  'posted-by': '<b>agent</b>', 'posted-at': 'now', 'read-at': null, link: '', summary: '', ...extra});
const link = '/records/README.md?x="onmouseover=bad()';
let listing = {unread: 7, notifications: [
  entry('one', {link, summary: '**Bold** [Guide](docs/guide.md) [Clip](assets/first%20run.webm#t=3)\n\n<script>bad()</script>\n\n[Bad](javascript:bad())'}),
  entry('decision', {kind: 'decision', link: '/decisions/decision'}),
  entry('read', {'read-at': 'before'}),
  {id: '<broken>', kind: '', error: '<script>broken</script>'},
  ...Array.from({length: 5}, (_, i) => entry('extra-' + i, {kind: 'custom-kind'})),
]};
let interval, failList = false, refuse = '', failRefresh = false;
const writes = [], reads = [];
const context = {
  document, window: {location: {pathname: '/notifications'},
    markdownit: require(path.join(staticRoot, 'vendor/markdown-it-15.0.2.umd.min.js'))},
  setInterval: (fn, ms) => { assert.equal(ms, 30000); interval = fn; },
  fetch: async (url, options) => {
    assert.equal(options.credentials, 'same-origin');
    if (!options.method) {
      reads.push(url);
      assert.ok(['/api/notifications', '/api/notifications?unread=1'].includes(url));
      if (failList || failRefresh) return {ok: false, status: 502, json: async () => ({error: 'CLI failed'})};
      return {ok: true, json: async () => url.endsWith('unread=1') ?
        {...listing, notifications: listing.notifications.filter(e => !e['read-at'])} : listing};
    }
    assert.equal(options.method, 'POST');
    writes.push(url);
    return {ok: !refuse, status: 422, text: async () => refuse === 'empty' ? '' : refuse};
  },
};
const flush = () => new Promise(resolve => setImmediate(resolve));
const buttons = item => descendants(item).filter(node => node.tag === 'button');
const entries = () => descendants(content).filter(node => node.tag === 'li');
vm.runInNewContext(fs.readFileSync(path.join(staticRoot, 'console.js'), 'utf8'), context);
(async () => {
  handlers.DOMContentLoaded();
  await flush();
  assert.deepEqual(reads, ['/api/notifications?unread=1', '/api/notifications']);
  assert.equal(count.textContent, '7'); assert.equal(count.hidden, false);
  assert.ok(anchor.classes.has('has-unread'));
  assert.equal(anchor.attributes['aria-label'], 'Notifications: 7 unread');
  assert.equal(anchor.attributes['aria-expanded'], 'false');
  assert.equal(menu.children.length, 6); // five entries and All notifications
  assert.equal(menu.children[0].attributes.href, link);
  assert.equal(menu.children[0].children[1].textContent, listing.notifications[0].title);
  assert.equal(menu.children[2].attributes.href, '/notifications');
  assert.equal(menu.children[5].attributes.href, '/notifications');
  const nodes = descendants(content), items = entries();
  assert.equal(items.length, 9);
  assert.equal(items[0].attributes.class, 'notification unread');
  assert.equal(items[2].attributes.class, 'notification');
  assert.equal(items[3].attributes.class, 'notification error');
  assert.ok(nodes.some(n => n.tag === 'a' && n.textContent === listing.notifications[0].title && n.attributes.href === link));
  assert.ok(nodes.some(n => n.textContent === '<b>agent</b> · now'));
  assert.ok(nodes.some(n => n.textContent === '<b>agent</b> · now · read before'));
  assert.ok(nodes.some(n => n.textContent === 'Malformed: <script>broken</script>'));
  assert.ok(nodes.some(n => n.textContent === 'custom-kind'));
  const html = nodes.find(n => n.innerHTML).innerHTML;
  assert.ok(html.includes('<strong>Bold</strong>'));
  assert.ok(html.includes('href="/records/docs/guide.md"'));
  // A link to a file that is not Markdown leads to its /files address, where a recording plays.
  assert.ok(html.includes('href="/files/assets/first%20run.webm#t=3"'));
  assert.ok(html.includes('&lt;script&gt;bad()&lt;/script&gt;'));
  assert.ok(!html.includes('<script>') && !html.includes('href="javascript:'));
  assert.equal(buttons(items[1]).length, 0); // Decisions can only be answered.
  assert.equal(buttons(items[3]).length, 0); // Malformed files cannot be acted on.
  assert.deepEqual(buttons(items[2]).map(n => n.textContent), ['Dismiss']);
  assert.deepEqual(buttons(items[0]).map(n => n.textContent), ['Mark read', 'Dismiss']);

  const click = () => anchor.listeners.click({preventDefault() {}});
  click(); assert.equal(menu.hidden, false); assert.equal(anchor.attributes['aria-expanded'], 'true');
  handlers.click({target: {closest: () => true}}); assert.equal(menu.hidden, false);
  handlers.keydown({key: 'Escape'});
  assert.equal(menu.hidden, true); assert.equal(anchor.attributes['aria-expanded'], 'false'); assert.ok(anchor.focused);
  click(); handlers.click({target: {}}); assert.equal(menu.hidden, true);
  click(); click(); assert.equal(menu.hidden, true);

  // The real handlers submit only the selected action and refresh the listing.
  const first = buttons(items[0]);
  const reading = first[0].listeners.click();
  assert.ok(first.every(button => button.disabled));
  listing.notifications[0]['read-at'] = 'now';
  await reading;
  assert.equal(writes[0], '/api/notifications/one/read');
  // A page action refreshes the listing and then the bell, without waiting for the timer.
  assert.deepEqual(reads.slice(2), ['/api/notifications', '/api/notifications?unread=1']);
  assert.deepEqual(buttons(entries()[0]).map(n => n.textContent), ['Dismiss']);
  refuse = 'Refused';
  await buttons(entries()[0])[0].listeners.click();
  assert.equal(writes[1], '/api/notifications/one/dismiss');
  assert.equal(buttons(entries()[0])[0].disabled, false);
  assert.ok(descendants(content).some(n => n.textContent === 'Not done: Refused'));
  refuse = 'empty';
  await buttons(entries()[0])[0].listeners.click();
  assert.ok(descendants(content).some(n => n.textContent === 'Not done: HTTP 422'));
  refuse = ''; failRefresh = true;
  await buttons(entries()[0])[0].listeners.click();
  assert.equal(buttons(entries()[0])[0].disabled, false);
  assert.ok(descendants(content).some(n => n.textContent === 'Not done: /api/notifications: CLI failed'));
  failRefresh = false;

  failList = true; await interval();
  assert.equal(count.hidden, true); assert.ok(!anchor.classes.has('has-unread'));
  assert.equal(anchor.attributes['aria-label'], 'Notifications unavailable');
  assert.equal(menu.children[0].textContent, 'Notifications unavailable: /api/notifications?unread=1: CLI failed');
  assert.equal(menu.children[1].attributes.href, '/notifications');
  failList = false; listing = {unread: 0, notifications: []}; await interval();
  assert.equal(count.hidden, true); assert.equal(count.textContent, '0');
  assert.equal(anchor.attributes['aria-label'], 'Notifications: 0 unread');
  assert.equal(menu.children[0].textContent, 'Nothing unread.');
  await buttons(entries()[0])[0].listeners.click();
  assert.ok(content.children[0].textContent.startsWith('Nothing is waiting.'));
  console.log('Notifications script: escaped content, actions, refusals, polling and keyboard controls passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});
