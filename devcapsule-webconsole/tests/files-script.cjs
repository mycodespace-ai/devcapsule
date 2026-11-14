// Run the actual files page with a small DOM adapter across listing, empty, file-redirect and failure states.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const staticRoot = path.join(__dirname, '../devcapsule_webconsole/static');
const scriptSource = fs.readFileSync(path.join(staticRoot, 'console.js'), 'utf8');

class Node {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.listeners = {};
    this.textContent = '';
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

function descendants(node) {
  return node.children.flatMap(child => [child, ...descendants(child)]);
}

function runFilesPage(pathname, responder) {
  const container = new Node('div');
  const titleNode = new Node('h1');
  const fetches = [];
  const replacedLocations = [];
  let ready;
  const document = {
    title: '',
    body: { dataset: { page: 'files' } },
    createElement: tag => new Node(tag),
    createTextNode: text => Object.assign(new Node('#text'), { textContent: text }),
    getElementById: id => (id === 'content' ? container : id === 'files-title' ? titleNode : null),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: (name, fn) => { assert.equal(name, 'DOMContentLoaded'); ready = fn; },
  };
  const context = {
    document,
    window: {
      location: {
        pathname,
        replace: url => replacedLocations.push(url),
      },
    },
    fetch: async (url, options) => {
      fetches.push({ url, options });
      return responder(url, options);
    },
  };
  vm.runInNewContext(scriptSource, context);
  ready();
  return new Promise(resolve => setImmediate(() => resolve({
    container,
    titleNode,
    document,
    fetches,
    replacedLocations,
  })));
}

(async () => {
  // 1. Nested directory with directory, markdown, binary/XSS-named file, sizes, link and FIFO.
  const nested = await runFilesPage('/files/docs/sub%20dir', async () => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify({
      path: 'docs/sub dir',
      entries: [
        { name: 'assets', kind: 'directory', size: null, modified: '2026-11-08T10:00:00Z' },
        { name: 'guide.md', kind: 'file', size: 1536, modified: '2026-11-08T10:01:00Z' },
        { name: '<clip>.webm', kind: 'file', size: 2097152, modified: '2026-11-08T10:02:00Z' },
        { name: 'archive.tar', kind: 'file', size: 1610612736, modified: '2026-11-08T10:03:00Z' },
        { name: 'tiny.bin', kind: 'file', size: 42, modified: '2026-11-08T10:04:00Z' },
        { name: 'escape.md', kind: 'link', size: null, modified: '2026-11-08T10:05:00Z' },
        { name: 'pipe', kind: 'other', size: null, modified: '2026-11-08T10:06:00Z' },
      ],
    }),
  }));
  assert.equal(nested.fetches.length, 1);
  assert.equal(nested.fetches[0].url, '/api/project/tree?path=docs%2Fsub%20dir');
  assert.equal(nested.fetches[0].options.credentials, 'same-origin');
  assert.equal(nested.titleNode.textContent, 'docs/sub dir');
  assert.equal(nested.document.title, 'docs/sub dir · DevCapsule console');

  const crumbs = nested.container.children[0];
  const crumbLinks = crumbs.children.filter(node => node.tag === 'a').map(node => [node.textContent, node.attributes.href]);
  assert.deepEqual(crumbLinks, [
    ['project', '/files'],
    ['docs', '/files/docs'],
    ['sub dir', '/files/docs/sub%20dir'],
  ]);

  const dataTable = nested.container.children[1];
  const headers = descendants(dataTable.children[0]).filter(node => node.tag === 'th').map(node => node.textContent);
  assert.deepEqual(headers, ['Name', 'Size', 'Modified']);

  const rows = dataTable.children[1].children;
  assert.equal(rows.length, 7);

  // Directory row
  assert.equal(rows[0].children[0].children[0].attributes.href, '/files/docs/sub%20dir/assets');
  assert.equal(rows[0].children[0].children[0].textContent, 'assets/');
  assert.equal(rows[0].children[1].textContent, '—');

  // Markdown file row: view -> /records/..., download -> raw&download=1
  const mdLinks = rows[1].children[0].children.filter(node => node.tag === 'a');
  assert.deepEqual(mdLinks.map(node => [node.textContent, node.attributes.href]), [
    ['guide.md', '/records/docs/sub%20dir/guide.md'],
    ['download', '/api/project/raw?path=docs%2Fsub%20dir%2Fguide.md&download=1'],
  ]);
  assert.equal(rows[1].children[1].textContent, '1.5 KiB');

  // Non-markdown file row with angle brackets kept as literal textContent
  const videoLinks = rows[2].children[0].children.filter(node => node.tag === 'a');
  assert.deepEqual(videoLinks.map(node => [node.textContent, node.attributes.href]), [
    ['<clip>.webm', '/api/project/raw?path=docs%2Fsub%20dir%2F%3Cclip%3E.webm'],
    ['download', '/api/project/raw?path=docs%2Fsub%20dir%2F%3Cclip%3E.webm&download=1'],
  ]);
  assert.equal(rows[2].children[1].textContent, '2.0 MiB');
  assert.equal(rows[3].children[1].textContent, '1.5 GiB');
  assert.equal(rows[4].children[1].textContent, '42 B');

  // Link entry: links to raw URL without download link
  const symlinkLinks = rows[5].children[0].children.filter(node => node.tag === 'a');
  assert.deepEqual(symlinkLinks.map(node => [node.textContent, node.attributes.href]), [
    ['escape.md', '/api/project/raw?path=docs%2Fsub%20dir%2Fescape.md'],
  ]);
  assert.equal(rows[5].children[1].textContent, '—');

  // Other entry (FIFO): shown without a link
  assert.equal(rows[6].children[0].children.filter(node => node.tag === 'a').length, 0);
  assert.equal(rows[6].children[0].children[0].textContent, 'pipe');
  assert.equal(rows[6].children[1].textContent, '—');

  // 2. Empty root directory
  const empty = await runFilesPage('/files', async () => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify({ path: '', entries: [] }),
  }));
  assert.equal(empty.fetches[0].url, '/api/project/tree');
  assert.equal(empty.titleNode.textContent, 'Files');
  assert.equal(empty.document.title, 'Files · DevCapsule console');
  assert.ok(descendants(empty.container).some(node => node.attributes?.class === 'notice' && node.textContent === 'This directory is empty.'));

  // 3. Direct /files/<file> URLs redirect to the file's view URL
  const videoRedirect = await runFilesPage('/files/docs/demo.webm', async () => ({
    ok: false,
    status: 404,
    text: async () => "'docs/demo.webm' is not a directory in the project\n",
  }));
  assert.deepEqual(videoRedirect.replacedLocations, ['/api/project/raw?path=docs%2Fdemo.webm']);

  // 4. Missing or refused paths render through fail()
  const failed = await runFilesPage('/files/missing', async () => ({
    ok: false,
    status: 404,
    text: async () => "no directory at 'missing' in the project\n",
  }));
  const failure = failed.container.children[0];
  assert.equal(failure.attributes.class, 'failure');
  assert.ok(failure.textContent.includes("no directory at 'missing' in the project"));

  // 5. A folder that holds a presentation.json offers its presentation above the listing; another folder does not.
  const recorded = await runFilesPage('/files/e2e/evidence/todo%20run', async () => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify({
      path: 'e2e/evidence/todo run',
      entries: [
        { name: 'presentation.json', kind: 'file', size: 4096, modified: '2026-11-14T10:00:00Z' },
        { name: 'scenario-video.webm', kind: 'file', size: 3145728, modified: '2026-11-14T10:00:00Z' },
      ],
    }),
  }));
  const offer = recorded.container.children[1];
  assert.equal(offer.attributes.class, 'notice');
  assert.deepEqual(offer.children.filter(node => node.tag === 'a').map(node => [node.textContent, node.attributes.href]), [
    ['Open its presentation', '/presentations/e2e/evidence/todo%20run'],
  ]);
  assert.equal(recorded.container.children[2].attributes.class, 'data');
  assert.equal(descendants(nested.container).some(node => node.textContent === 'Open its presentation'), false);

  console.log('Files script: breadcrumbs, table links, sizes, empty notice, file redirect, failure and presentation offer passed.');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
