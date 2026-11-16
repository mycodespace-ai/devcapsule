// Run the actual files page with a small DOM adapter across listing, empty, recording, file-redirect and failure states.
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

// A tree route answer: a listing, or the refusal text with its status.
function listingOf(directory, entries) {
  const body = JSON.stringify({ path: directory, entries });
  return { ok: true, status: 200, text: async () => body, json: async () => JSON.parse(body) };
}

function refusal(status, message) {
  return { ok: false, status, text: async () => message, json: async () => { throw new Error('not JSON'); } };
}

const NOT_A_DIRECTORY = name => refusal(404, `'${name}' is not a directory in the project\n`);

function runFilesPage(pathname, responder, hash) {
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
        ...(hash === undefined ? {} : { hash }),
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
        { name: 'guide.md', kind: 'file', size: 1536, modified: '2026-11-08T10:01:00Z', type: 'text/markdown; charset=utf-8' },
        { name: '<clip>.webm', kind: 'file', size: 2097152, modified: '2026-11-08T10:02:00Z', type: 'video/webm' },
        { name: 'archive.tar', kind: 'file', size: 1610612736, modified: '2026-11-08T10:03:00Z', type: 'application/octet-stream' },
        { name: 'tiny.bin', kind: 'file', size: 42, modified: '2026-11-08T10:04:00Z' },
        { name: 'escape.md', kind: 'link', size: null, modified: '2026-11-08T10:05:00Z', type: null },
        { name: 'pipe', kind: 'other', size: null, modified: '2026-11-08T10:06:00Z', type: null },
        { name: 'voice.ogg', kind: 'file', size: 2048, modified: '2026-11-08T10:07:00Z', type: 'audio/ogg' },
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
  assert.equal(rows.length, 8);

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

  // Video row with angle brackets kept as literal textContent: view -> its /files address, where the page plays it
  const videoLinks = rows[2].children[0].children.filter(node => node.tag === 'a');
  assert.deepEqual(videoLinks.map(node => [node.textContent, node.attributes.href]), [
    ['<clip>.webm', '/files/docs/sub%20dir/%3Cclip%3E.webm'],
    ['download', '/api/project/raw?path=docs%2Fsub%20dir%2F%3Cclip%3E.webm&download=1'],
  ]);
  assert.equal(rows[2].children[1].textContent, '2.0 MiB');

  // A file that is neither Markdown nor a recording, and a file the listing gives no type for: view -> raw
  const viewLink = row => row.children[0].children.filter(node => node.tag === 'a')[0].attributes.href;
  assert.equal(viewLink(rows[3]), '/api/project/raw?path=docs%2Fsub%20dir%2Farchive.tar');
  assert.equal(viewLink(rows[4]), '/api/project/raw?path=docs%2Fsub%20dir%2Ftiny.bin');

  // Audio row: view -> its /files address
  assert.equal(viewLink(rows[7]), '/files/docs/sub%20dir/voice.ogg');
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

  // 3. /files/<video> plays the file in the page: the type comes from the parent's listing, and no location is replaced.
  const video = await runFilesPage('/files/docs/sub%20dir/first%20run.webm', async url => (
    url === '/api/project/tree?path=docs%2Fsub%20dir%2Ffirst%20run.webm' ? NOT_A_DIRECTORY('docs/sub dir/first run.webm')
      : url === '/api/project/tree?path=docs%2Fsub%20dir' ? listingOf('docs/sub dir', [
        { name: 'first run.webm', kind: 'directory', size: null, modified: '2026-11-08T10:00:00Z', type: null },
        { name: 'first run.webm', kind: 'file', size: 2097152, modified: '2026-11-08T10:02:00Z', type: 'video/webm' },
      ])
        : refusal(500, 'unexpected ' + url)
  ));
  assert.deepEqual(video.fetches.map(call => [call.url, call.options.credentials]), [
    ['/api/project/tree?path=docs%2Fsub%20dir%2Ffirst%20run.webm', 'same-origin'],
    ['/api/project/tree?path=docs%2Fsub%20dir', 'same-origin'],
  ]);
  assert.deepEqual(video.replacedLocations, []);
  assert.equal(video.titleNode.textContent, 'docs/sub dir/first run.webm');
  assert.equal(video.container.children.length, 3);
  const [videoCrumbs, player, videoDownload] = video.container.children;
  assert.deepEqual(videoCrumbs.children.filter(node => node.tag !== '#text').map(node => [node.tag, node.textContent, node.attributes.href]), [
    ['a', 'project', '/files'],
    ['a', 'docs', '/files/docs'],
    ['a', 'sub dir', '/files/docs/sub%20dir'],
    ['span', 'first run.webm', undefined],
  ]);
  assert.equal(player.tag, 'video');
  assert.deepEqual(player.attributes, {
    class: 'recording', controls: '', preload: 'metadata', src: '/api/project/raw?path=docs%2Fsub%20dir%2Ffirst%20run.webm',
  });
  assert.deepEqual(videoDownload.children.map(node => [node.textContent, node.attributes.href]), [
    ['download', '/api/project/raw?path=docs%2Fsub%20dir%2Ffirst%20run.webm&download=1'],
  ]);

  // 3a. An audio file at the project root plays in an audio element; its parent's listing is the root's.
  const audio = await runFilesPage('/files/voice.ogg', async url => (
    url === '/api/project/tree?path=voice.ogg' ? NOT_A_DIRECTORY('voice.ogg')
      : url === '/api/project/tree' ? listingOf('', [{ name: 'voice.ogg', kind: 'file', size: 2048, modified: '2026-11-08T10:07:00Z', type: 'audio/ogg' }])
        : refusal(500, 'unexpected ' + url)
  ));
  assert.deepEqual(audio.replacedLocations, []);
  assert.equal(audio.container.children[1].tag, 'audio');
  assert.equal(audio.container.children[1].attributes.src, '/api/project/raw?path=voice.ogg');
  assert.deepEqual(audio.container.children[0].children.filter(node => node.tag !== '#text').map(node => [node.tag, node.textContent]), [
    ['a', 'project'], ['span', 'voice.ogg'],
  ]);

  // 3b. Any other file leaves for where it is viewed, with the address's fragment: raw, or Records for Markdown.
  const inDocs = entries => async url => (url === '/api/project/tree?path=docs' ? listingOf('docs', entries) : NOT_A_DIRECTORY('the file'));
  const text = await runFilesPage('/files/docs/notes.txt', inDocs([
    { name: 'notes.txt', kind: 'file', size: 12, modified: '2026-11-08T10:00:00Z', type: 'text/plain; charset=utf-8' },
  ]), '#L3');
  assert.deepEqual(text.replacedLocations, ['/api/project/raw?path=docs%2Fnotes.txt#L3']);
  assert.equal(text.container.children.length, 0);
  const markdown = await runFilesPage('/files/docs/guide.md', inDocs([
    { name: 'guide.md', kind: 'file', size: 12, modified: '2026-11-08T10:00:00Z', type: 'text/markdown; charset=utf-8' },
  ]));
  assert.deepEqual(markdown.replacedLocations, ['/records/docs/guide.md']);

  // 3c. A name the parent's listing does not hold as a regular file, and a parent that cannot be listed, go to the
  // raw route, which answers for them; a video name alone plays nothing.
  const linked = await runFilesPage('/files/docs/demo.webm', inDocs([
    { name: 'demo.webm', kind: 'link', size: null, modified: '2026-11-08T10:00:00Z', type: null },
  ]));
  assert.deepEqual(linked.replacedLocations, ['/api/project/raw?path=docs%2Fdemo.webm']);
  const unlisted = await runFilesPage('/files/docs/demo.webm', async url => (
    url === '/api/project/tree?path=docs' ? refusal(403, 'cannot read') : NOT_A_DIRECTORY('docs/demo.webm')
  ));
  assert.deepEqual(unlisted.replacedLocations, ['/api/project/raw?path=docs%2Fdemo.webm']);

  // 4. Missing or refused paths render through fail()
  const failed = await runFilesPage('/files/missing', async () => refusal(404, "no directory at 'missing' in the project\n"));
  assert.equal(failed.fetches.length, 1);
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

  console.log('Files script: breadcrumbs, table links, sizes, empty notice, recordings played in the page, file redirect, failure and presentation offer passed.');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
