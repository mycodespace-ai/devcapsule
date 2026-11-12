---
description: Use a provider account for hosted models, or connect a compatible coding agent to a model server on your computer.
weight: 4
updated: 2026-10-30
---
# Hosted and local models

DevCapsule installs coding agents, not a model service or an AI subscription.
Choose a provider through the agent. A model server on your computer is also
an option when the agent supports its protocol and authentication method.

## Hosted models

Select `claude-code-agent`, `codex-agent`, or `antigravity-agent` for your
checkout. Start `claude`, `codex login`, or `antigravity` inside the capsule
and follow its sign-in flow. See [Sign in and defaults](sign-in-and-defaults.md)
for the persistent directories and permission settings.

For API-key authentication, run these commands from a host terminal after
selecting the corresponding agents:

```bash
devcapsule project config bind codex/openai-api-key host-environment:OPENAI_API_KEY
devcapsule project config bind antigravity-cli/gemini-api-key host-environment:GEMINI_API_KEY
```

Export the matching variable before launching the capsule. The binding stores
only its name. The launcher checks for the variable at launch time.
For other provider variables, use `devcapsule project config env set NAME`
and enter the value at the hidden prompt. Use the exact variable name the
agent documents; DevCapsule does not translate provider settings.

Choose a model with the agent's own controls, such as `codex --model MODEL`,
`claude --model MODEL`, or `antigravity --model MODEL`.

## Reach a model server on your computer

Start the model server on your host according to its own instructions.
DevCapsule does not install it or manage its model weights.
The following examples assume an HTTP server on port 8000. Replace that port
with the server's actual port.

A default bridge-network capsule has its own loopback interface. Its
`127.0.0.1` does not reach your host's loopback services. Choose one of these
routes from your host terminal:

- **Share host networking for one launch:**

  ```bash
  devcapsule project run --authorize network host
  ```

  The capsule can then reach a host server at `http://127.0.0.1:8000`.
  This shares the host's network namespace, including access to other host
  services. Save that choice with `devcapsule project config authorize
  network host`, or return to bridge networking with `config deny network`.

- **Keep bridge networking:** configure the server to listen on an address
  reachable from Docker's bridge. A server bound only to host `127.0.0.1`
  will not accept this connection. Add a host address at launch:

  ```bash
  devcapsule project run -- --add-host=host.docker.internal:host-gateway
  ```

  Use `http://host.docker.internal:8000` inside the capsule. Permit the
  connection in your host firewall without exposing the server unnecessarily
  to your local network.

## Configure the agent for that endpoint

Use the agent's documented provider configuration to select the endpoint,
model identifier, and credentials. Check its installed `--help`; supported
providers and flags can differ between agent versions. Codex exposes `--oss`
and `--local-provider` for supported local providers. These flags do not
establish compatibility with every server that describes itself as
OpenAI-compatible.

Keep provider settings in the agent's persistent configuration directory.
For provider-specific environment variables, run `devcapsule project config
env set NAME VALUE` on the host and launch the capsule again. Replace `NAME`
with the variable the agent documents and `VALUE` with its endpoint.

For application previews and port publishing in the other direction, see
[Previews and ports](../everyday-development/previews-and-ports.md).
