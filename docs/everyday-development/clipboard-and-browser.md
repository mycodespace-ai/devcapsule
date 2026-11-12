---
description: How text moves between your computer and the capsule's desktop, how keys and fullscreen behave in the browser tab, and how links open.
weight: 5
updated: 2026-10-30
---
# Clipboard, keys and browser

The capsule's desktop runs inside a browser tab on `127.0.0.1` so your host
display session stays outside the container. That isolation changes three
everyday habits: copying text across the boundary, entering fullscreen, and
opening external links.

## Clipboard

The capsule cannot read your computer's clipboard automatically; text crosses
only when you move it:

1. Open the control bar along the left edge of the desktop tab and select the
   **Clipboard** icon.
2. **From capsule to host:** copy text inside the IDE (`Ctrl+C`), then copy it
   out of the sidebar's clipboard box into your host clipboard.
3. **From host to capsule:** paste text into the sidebar's clipboard box, then
   paste inside the IDE (`Ctrl+V` or `Ctrl+Shift+V` in terminals).

Keeping clipboard transfer explicit prevents background processes inside the
capsule from reading secrets you copied on your host.

## Keys, Escape and fullscreen

In a normal browser tab, every shortcut the browser itself does not reserve
reaches the IDE—including `Escape`.

- **Use your browser's fullscreen (`F11`), not the sidebar's fullscreen
  button.** Browsers exit HTML5 element fullscreen whenever you press `Escape`,
  which intercepts `Escape` before Vim modes, dialogs, or code completion see
  it. Instead, press `Ctrl+L` to focus the address bar, press `F11` (or
  **View → Enter Full Screen** on macOS), and click back into the desktop.
- Browser-reserved shortcuts such as `Ctrl+W`, `Ctrl+T`, and `Alt+Tab` stay with
  your browser and OS. If you close the tab with `Ctrl+W` by mistake, the
  capsule keeps running—reopen the desktop URL printed in your launcher
  terminal ([Stop and come back](../getting-started/stop-and-come-back.md)).

## Managing windows on the capsule desktop

The capsule runs a single virtual desktop with a taskbar along the bottom
showing a button for every open window and a clock. The IDE starts maximized
and resizes automatically when you resize the browser window. If a modal dialog
or secondary window opens behind the main editor, click its button on the
bottom panel—or right-click empty desktop background—to bring it forward.

## Opening links on your host browser

The default base image has no standalone web browser. The optional
`browser-automation` component supplies Chromium for Playwright. When an IDE
or CLI agent prints or opens an `http://` or
`https://` link (such as OAuth sign-in or API documentation), you have two
choices:

- **Copy the URL out** through the left sidebar's clipboard box and open it in
  your host browser, or
- **Grant the URL-only browser broker** from a host terminal for this checkout
  or a single run:

  ```bash
  devcapsule project config authorize host-browser true
  # or for one session without saving:
  devcapsule project run --authorize host-browser true
  ```

With `host-browser` enabled, `http://` and `https://` URLs opened through
`BROWSER` / `xdg-open` inside the capsule ask the launcher on your host to open
them in your default browser, without exposing your browser profile or display
session to the container. A printed URL still needs you to open it.
`host-browser` does not publish application or OAuth callback ports; see
[Previews and ports](previews-and-ports.md).

Run `devcapsule project config deny host-browser` on the host to withdraw
access for the next launch. Stop the current capsule to end its existing
access ([Granting and withdrawing
access](../containment/granting-and-withdrawing.md)).
