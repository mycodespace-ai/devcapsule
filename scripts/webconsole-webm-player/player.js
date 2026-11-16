// The player page: builds, for the recording named by `?src=`, the document
// the console's raw route cannot be: a <video> with the raw address as source.

import { EXPECTED, consoleRecording } from './pattern.js';

const LOG_PREFIX = '[DevCapsule WebM player]';
const stage = document.getElementById('stage');
const source = new URLSearchParams(location.search).get('src');
const recording = consoleRecording(source);

if (recording) {
  showPlayer(recording);
} else {
  const message = `pattern not matched: ${source ?? 'no address'} is not ${EXPECTED}`;
  console.warn(`${LOG_PREFIX} ${message}`);
  stage.append(element('p', { className: 'alert', textContent: message }));
}

function showPlayer({ origin, path, raw }) {
  document.title = path.split('/').pop();
  const video = element('video', { controls: true, autoplay: true, src: raw });
  const failure = element('p', { className: 'alert', hidden: true });
  video.addEventListener('error', () => {
    failure.textContent =
      `The console at ${origin} did not serve this recording. ` +
      'Check that the capsule is running and that this browser has opened its console link once, then reload.';
    failure.hidden = false;
    console.warn(`${LOG_PREFIX} cannot load ${raw}`, video.error);
  });
  const folder = path.split('/').slice(0, -1).map(encodeURIComponent).join('/');
  stage.append(
    element('h1', { textContent: path }),
    video,
    failure,
    element('nav', {}, [
      element('a', { href: `${raw}&download=1`, textContent: 'Download' }),
      element('a', { href: `${origin}/files/${folder}`, textContent: 'Folder in the console' }),
    ]),
  );
}

function element(name, properties, children = []) {
  const node = Object.assign(document.createElement(name), properties);
  node.append(...children);
  return node;
}
