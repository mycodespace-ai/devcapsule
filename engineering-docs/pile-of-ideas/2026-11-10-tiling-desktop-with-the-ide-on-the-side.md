# A tiling desktop: agents in a tabbed terminal, the IDE on the side

From: Costin Cozianu, 2026-11-10, written up with Claude.

Today a capsule's desktop is one big IDE. PyCharm is a memory and CPU hog by
default. Working on the DevCapsule codebase I have to put it in Power Save
mode: it indexes the whole codebase to give perfect navigation (go to
definition, go to declaration, find usages) and refactoring. I now use those
infrequently, and they rarely justify the memory and CPU the IDE spends on
them all the time.

Meanwhile the IDE is where everything else happens. I run the agent tools
(Antigravity, Codex, Claude) in the IDE's terminal, where I can watch the
agent work and browse the code beside it.

The idea: the desktop a capsule gives you by default should be laid out for
that way of working, above all in the contained X server behind noVNC.

- A tiling window manager arranges the windows, so nothing is lost behind
  something else.
- The agents and everything else run in a multi-tab terminal. That also saves
  the CPU and memory of the IDE's Java terminal.
- The IDE lives happily in a window on the side, only when it is needed.
- A bar at the bottom of the desktop has a notification area.

## 1. Research first: is the window manager we ship good enough?

Maybe it only needs configuring. Find out before choosing another one.

## 2. A multi-tab terminal as the default home of the agents

The terminal, not the IDE, is what opens first and what the agents run in.

## 3. The IDE on the side, only when needed

The IDE becomes one window among others, started when I want navigation,
refactoring or a debugger, and closed again without ending the session.

## 4. A bottom bar with a notification area

## What ships today

Added by Claude from the code at `release-0.3.1`, as input to part 1.

- The contained display runs Xvnc, Openbox and a tint2 panel, served through
  noVNC (`devcapsule-src/devcapsule/container_runtime/display.py`).
- Openbox is a stacking window manager. DevCapsule's configuration,
  `container_runtime/openbox-rc.xml`, gives it one desktop and starts the IDE
  maximized. It can place windows by rule and by key binding; it does not
  tile on its own.
- The bottom bar already exists: `container_runtime/tint2rc` puts tint2 at
  the bottom with a button per window and a clock (`panel_items = TC`). It
  has no notification area, and this capsule has no notification daemon and
  no `notify-send`.
- This capsule has no terminal emulator outside the IDE: no `xterm`, no
  `tmux`. Part 2 therefore needs a package in the base image.
- A constraint the research has to settle: tiling window managers are driven
  from the keyboard, and the Openbox configuration records an owner finding
  of 2026-09-14 that Alt+Tab never reaches the browser page under noVNC.
  Which key combinations do reach the capsule decides what is usable.
