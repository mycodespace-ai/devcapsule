---
description: Build a DevCapsule base image locally and select it for one checkout when the published base predates a feature you need.
weight: 6
updated: 2026-10-30
---
# Build and select a local base

Every capsule image starts from a base image containing the operating system,
toolchains, contained display, and (from base recipe `11` onward) the web
console. Normally you run the published base pinned in the project's platform
lock. Building a base on your own computer lets one checkout run a newer recipe
before the project lock pins a published update—for example, when a checkout on
an older base prints:

```text
Web console: none on this base (ubuntu-24.04@9; the console needs base recipe 11 or later); the capsule runs without it.
  To build a base that has it:  devcapsule images build --type base --recipe ubuntu-24.04 --source-revision <revision>
  Then select it for this checkout; the steps: https://devcapsule.mycodespace.ai/docs/current/configuration/local-base/
```

The capsule still runs without a local base; follow these steps only when you
want the newer base recipe on your checkout right away.

## Build the base

`images build --type base` builds from the recipe embedded in your launcher and
records the launcher's source revision in image provenance labels. Read the
revision from `devcapsule version` and replace the example revision below.
Supply a local `--tag` name, which `images build --type base` requires even when
you copy the launcher's printed build hint:

```bash
devcapsule version
devcapsule images build --type base --recipe ubuntu-24.04 \
  --tag devcapsule-base-local:recipe-11 \
  --source-revision 0123456789abcdef0123456789abcdef01234567
```

Choose a `--tag` that makes the local image clear to you. The first build
installs OS packages and toolchains and takes several minutes. Add `--network
host` if your Docker BuildKit network cannot resolve DNS names.
`--source-revision` must match the revision already embedded in the launcher;
it does not select different source code.

`--allow-local-source` bypasses the public-revision check for a development
build. It cannot supply missing console source: current base recipes still
need a full GitHub source identity to install the web console. Use a launcher
built from a published commit when that identity is missing.

List the built image in your local Docker store:

```bash
devcapsule images list
```

`images list` reports the recipe (such as `ubuntu-24.04@11`), image ID, and tags.
The build output reports the source revision and source URL. To inspect the
stored revision later:

```bash
docker image inspect devcapsule-base-local:recipe-11
```

Read `devcapsule.source.revision` under `Config.Labels` in the JSON output.

## Select it for a checkout

From the project checkout on your host:

```bash
devcapsule project config authorize base-image devcapsule-base-local:recipe-11
devcapsule project run
```

`authorize base-image` inspects the local image, verifies that it is a
DevCapsule base image for your platform, records its exact image ID in this
checkout's configuration, and notes that your selection overrides the lock's
published base for this checkout. The next `project run` materializes the
checkout's environment image on top of that local base (printing the web
console link when the base is recipe `11` or newer).

Keep these boundaries in mind:

- **Personal to this checkout:** the override stays in your checkout record
  ([Project versus personal](project-versus-personal.md)); the shared lock in
  Git still pins the published base for everyone else.
- **Bound to the exact image ID:** if you rebuild the base under the same tag,
  run `project config authorize base-image <tag>` again to bind the new ID.
- **Qualification, not shared validation:** running on a local base tests your
  checkout on that recipe, and any lock proposal generated from such a checkout
  notes the local-base qualification.
- **Does not waive project requirements:** a local base cannot bypass mandatory
  project guarantees such as a capability minimum; see [Capabilities and
  components](capabilities.md).

`devcapsule project config show` lists the active `base-image` override among
your checkout's answers.

## Back to the published base

```bash
devcapsule project config authorize base-image default
```

`default` returns this checkout to the base pinned in the project lock and
records consent for that exact digest. It does not accept the home-wide
`devcapsule-base` channel.
The local base image stays in your Docker store until you remove it with
`docker rmi`.
