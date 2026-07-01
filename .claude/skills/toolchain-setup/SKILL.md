---
name: toolchain-setup
description: Bootstrap the Node/mystmd + Python (griffe/sphinx/sphobjinv) toolchain for this repo. Use when npm/npx/myst/python are missing, when builds or tests fail with "command not found", or when setting up a fresh dev container. Covers the read-only-rootfs and zsh-no-rc gotchas specific to the sandbox this project was built in.
---

# Toolchain setup

This project needs **Node ≥18 + mystmd** and a **Python venv** (griffe, sphinx,
sphobjinv, numpydoc, pytest). In a normal dev box `npm install` + a venv is
enough. In the bare/read-only sandbox this repo was built in, the environment is
unusual — recreate it like this.

## Environment gotchas (sandbox)

- **`/` and `/usr` are read-only.** `apt-get install` fails (can't write
  `/var/lib/apt/lists`). Only `/root` (tmpfs) and the project dir are writable.
- **The shell is zsh started with NO rc files.** `~/.zshenv`/`.bashrc`/`.profile`
  are NOT sourced. PATH is injected by the harness and already includes
  `/root/.local/bin` — so to put a tool on PATH, **symlink it into
  `/root/.local/bin`** (editing rc files does nothing).

## Node + mystmd (npm is often absent)

```bash
# bootstrap npm 10.9.2 (node-18 compatible) into a writable prefix
curl -sSL https://registry.npmjs.org/npm/-/npm-10.9.2.tgz -o /tmp/npm.tgz
mkdir -p /root/.npm-boot && tar xzf /tmp/npm.tgz -C /root/.npm-boot
node /root/.npm-boot/package/bin/npm-cli.js i -g --prefix /root/.npm-global npm@10.9.2
ln -sf /root/.npm-global/bin/{npm,npx} /root/.local/bin/
printf 'prefix=/root/.npm-global\n' > /root/.npmrc

# project deps (mystmd is pinned to 1.10.1 to match the documented findings)
npm install
npm run build          # tsup -> dist/*.mjs   (mystmd only loads .mjs plugins!)
```

`myst` is a project devDep at `./node_modules/.bin/myst`.

## Python (via uv)

```bash
uv python install 3.12
uv venv .venv --python 3.12
VIRTUAL_ENV=.venv uv pip install --python .venv griffe sphinx sphobjinv numpydoc pytest
```

Reference tools by absolute path: `.venv/bin/python`, `.venv/bin/sphinx-build`.

## Network

npm registry, pypi, github, and docs.python.org are all reachable in this
sandbox. Even so, **tests are hermetic** — inventories are vendored and served
over localhost (see the `acceptance-oracle` skill).

## Verify

```bash
./run_all.sh     # build + generate objects.inv + full acceptance suite
```
