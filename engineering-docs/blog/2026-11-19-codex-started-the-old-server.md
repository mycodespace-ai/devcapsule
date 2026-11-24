---
description: "An updated Codex started an old server from a saved home directory. Three terminal launches explained a missing model and why a container-side fix is a bad bargain."
draft: true
---

# We upgraded Codex. It started the old server.

Costin could pick GPT-6.2 Astra on one laptop. On the other he had the same account, the same sign-in, and a freshly updated Codex. Where was Astra?

There’s a small indignity in asking a coding agent to help you find the coding agent you wanted to talk to. The one he had was quite willing to help. It found the old server, gave him the command to update it, and pronounced the mystery solved. A little later Costin found Astra in the model picker and said hello. Then he asked the question we should have answered before declaring victory.

> And what did install the daemon in ~/.codex then ?

**TL;DR** Codex put it there the first time the old version ran. When the new version found it, it started the old one again.

We’d had a good clue. In the very same request for the list of models, the terminal introduced itself as version `0.170.0` and the server went looking for the catalog for `0.163.0`. It even noticed its copy was stale and refreshed it. Costin now had a perfectly fresh list for the wrong version. Meanwhile `codex --version` said `0.170.0`, quite truthfully. You can see why he was thinking about his account.

We knew where both executables lived. The new one came with the Docker image. The old one was in `~/.codex`, along with Costin’s settings, sign-in and conversations. DevCapsule keeps that directory when it replaces an image, for much the same reason it keeps your IDE shortcuts and the plugins you went to the trouble of installing. But knowing where we found a file didn’t tell us who put it there. Costin had to ask again before we actually tried the old release.

We gave the new Codex an empty home directory and opened a terminal. By the time it asked us to sign in, it had installed its own server. We gave the old Codex an empty home of its own. Same thing. Two clean installs, both behaving just as you’d hope.

For the third run we stopped the old Codex and its server. We kept its home directory and launched the **new** Codex there. Up came the sign-in screen. Behind it, a brand-new process was running the old `0.163.0` executable. There was no forgotten process hanging around in a terminal somewhere. We’d stopped it. The new Codex had gone back to disk and started it again.

We never inspected the other laptop. We didn’t need it to explain the missing model on this one. We could make the new CLI start the old server without entering a single credential. In Costin’s actual capsule, `codex app-server daemon update --from-cli` brought the server up to date, and it offered Astra. We briefly thought it had reverted after a restart. That was our second wrong turn. The update had stuck. This time Astra really was in the menu, just easy to miss.

## Now suppose we “fix” it

It’s tempting. We have a command that worked. Why shouldn’t DevCapsule run it whenever the two versions differ? Well, suppose you have another Codex session halfway through a job. We’ve just volunteered to update its server. And who told us the two version numbers must always match? Nobody. We observed what two releases did on a Thursday. That’s a thin basis for deciding when to replace software on somebody else’s machine.

We could give every rebuilt image an empty `~/.codex`. Our first two runs tell us exactly how well that works, right up to the moment you ask where your conversations went. Keeping everything *except* the daemon directory is a nicer idea until you consider who now has to know which bits of Codex’s private filing system are safe to throw away. We’d get to find out again on the next upgrade, and once more when somebody rolls back.

I’d give the three-run example to the Codex team and tell people which command helped us with these versions. That still leaves somebody doing a manual repair. I think that’s a lousy experience. Codex picked the server. It’s the one program in a position to know whether that choice is sound, and to tell the person at the keyboard when changing it would interrupt their work.

There is one change I’d gladly make on our side. When we test an upgraded capsule, give it a home somebody has actually used. Open the tool, find yesterday’s conversation, then try the feature we upgraded for. If we’d tried that the first time around, we might have found the missing model before Costin did.

## About this entry

The dialogue excerpt is Costin’s, quoted as typed. We tested the Linux x86-64 releases on November 19, 2026, using temporary homes for the three launches. DevCapsule’s side of the story is in the [Codex component’s package and persistence declarations](https://github.com/mycodespace-ai/devcapsule/blob/b3410ca24e9ae94670a86807ec55aa2a63e5d842/devcapsule-src/devcapsule/components/codex.py) and the [persistent-home specification](https://github.com/mycodespace-ai/devcapsule/blob/b3410ca24e9ae94670a86807ec55aa2a63e5d842/engineering-docs/specifications/product/state-and-persistence.md).
