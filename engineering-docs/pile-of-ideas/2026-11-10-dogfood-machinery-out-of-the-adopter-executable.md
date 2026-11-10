# Keep DevCapsule's own test machinery out of the adopter's executable

From: Claude (Fable 5) with the owner, 2026-11-10, on a first reading of the
code at `v0.3.1-rc2`.

The executable an adopter downloads carries the machinery DevCapsule uses to
validate itself recursively, and shows part of it on the adopter's command
line. None of it can do anything for an adopter: the commands refuse every
project whose manifest is not named `DevCapsule`.

What is there today:

- Five modules, `devcapsule-src/devcapsule/recursive_*.py`, 3,250 lines,
  about 8% of the product's Python.
- `devcapsule project --help` lists `recursive-e2e`, a group of four
  commands: `preflight`, `run`, `launch-successor`, `inspect-successor`.
- `devcapsule project run --help` lists `--no-recursive-e2e`.
- `docs/reference/cli.md` documents both, the group as a contributor tool.
- Ordinary features depend on the test module: `notifications.py` and
  `console_tools.py` import `recursive_dogfood` for the container-name
  variable and the runtime plan path, and `host_daemon.py` for identifying
  and inspecting the current container.

Why it could be worth doing: the README tells the adopter they can know
exactly what the tool can touch. A command line and a launch path that hold
only what serves them are easier to read, to document and to review. Nothing
is broken, and nothing here is urgent.

## 1. Give the shared names a home of their own

Move the container-name variable, the runtime plan path and the container
identification that the three ordinary modules import out of
`recursive_dogfood.py` into the module that owns the capsule's runtime
contract. Small, no behavior change,
and it is the precondition for the other two parts.

## 2. Take the surface off the adopter's command line

Hide the `recursive-e2e` group and the `--no-recursive-e2e` flag from help,
and move their documentation from the user reference to the contributor
documents. Small. The decision it needs: whether a contributor finds the
commands well enough once they are hidden.

## 3. Take the machinery out of the shipped package

Move the five modules to where only a DevCapsule checkout has them: a
separate distribution, or tooling beside the end-to-end tests. Large. The
open question is how a recursive session finds the machinery inside a capsule
that has only the shipped `devcapsule0`.

## Not checked

- Whether anything outside this repository calls the `recursive-e2e`
  commands.
- How much of the five modules the current release gate still exercises; the
  `recursive_dogfood_e2e` nox session exists, and I did not run it.
