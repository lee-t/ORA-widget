# Plan: Dockerize ORA-widget install

## Decisions from alignment
- Fetch OpenRA engine + Tiberian Dawn content at first container **startup** (not baked into image), cached in a bind-mounted `./engine` dir and a named volume for `~/.config/openra`.
- Scope: **cnc (Tiberian Dawn) only** — matches what's actually implemented (maps/arena-cnc, battles/demo-cnc.json, ora_widget.py hardcodes cnc).
- docker-compose publishes the marimo port bound to `127.0.0.1` only (not `0.0.0.0`) — host-side safety. Inside the container marimo still binds `0.0.0.0` so Docker's port-forwarding can reach it.
- Container runs as **root** (simplest; matches current script's assumptions, avoids permission edge cases with the engine dir / OpenRA config).
- Leave marimo's default token auth **enabled** (don't pass `--no-token`) as a cheap extra safety layer; entrypoint prints the URL marimo prints (includes token).
- Base image must be **glibc-based** (Debian/Ubuntu) — OpenRA's self-contained .NET build won't run on musl/Alpine.

## New files
1. `Dockerfile` — repo root.
   - Base: the amd64 manifest for `ghcr.io/astral-sh/uv:python3.14-bookworm-slim`, pinned by digest in `Dockerfile`; the build installs the exact `.python-version` (3.14.6) with uv. The build rejects non-amd64 images because the pinned OpenRA artifact is x86_64.
   - `apt-get install`: `xvfb xdotool x11-utils ffmpeg unzip curl ca-certificates procps libopenal1 libsdl2-2.0-0 libgl1 libgl1-mesa-dri` (same list as README's manual apt install, plus `procps` for `pgrep` used in `battle.py:start_xvfb()`, `x11-utils` for `xdpyinfo`, plus mesa/GL libs for llvmpipe software rendering under Xvfb, plus `curl`/`ca-certificates` for runtime downloads).
   - `requirements.lock` contains the hash-locked Marimo environment for Python 3.14 on Linux amd64. `RUN uv pip install --system --require-hashes -r requirements.lock` installs it at build time, so startup does not resolve dependencies or require PyPI access. The inline PEP 723 header pins Marimo to the same version for bare-metal runs.
   - `WORKDIR /app`, `COPY . /app` (respecting `.dockerignore`).
   - `COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh` + `chmod +x`.
   - `EXPOSE 2718`.
   - `ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]`.

2. `docker/entrypoint.sh` — idempotent setup + launch, run as root at container start:
   - Step A — engine: if the versioned cache marker and expected files are not present, download the pinned `OpenRA-Tiberian-Dawn-x86_64.AppImage`, verify its SHA-256, and extract it into a temporary directory with `--appimage-extract` (no FUSE needed). Replace `engine/openra-cnc` only after extraction succeeds, then write the marker. The release, URL, and SHA-256 are defined together in the image environment.
   - Step B — content: if the versioned cache marker and `conquer.mix` are not present, download the pinned CNC archive URL, verify its SHA-256, unzip into a temporary directory, validate the expected file, and atomically replace `$HOME/.config/openra/Content/cnc` before writing the marker. This avoids accepting an interrupted download or extraction.
   - Step C — exec the notebook server: `exec marimo edit --headless --host 0.0.0.0 --port "$PORT" ora_widget.py`. Dependencies are already installed in the image; do not use `--sandbox` at runtime.
   - Fail loudly (`set -euo pipefail`) with a clear message if a download or checksum fails, rather than silently starting with a broken engine.

3. `docker-compose.yml` — repo root, single service `ora-widget`:
   - `platform: linux/amd64` (the OpenRA AppImage is x86_64; native amd64 is preferred, while Docker/Podman can use emulation where configured).
   - `build: .`
   - `ports: ["127.0.0.1:${HOST_PORT:-2718}:2718"]` (the container port remains fixed at 2718).
   - `volumes:`
     - `./engine:/app/engine:Z` (bind mount — persists the extracted engine across container recreation, visible on host; the cache is versioned by a release/checksum marker and `:Z` keeps rootless Podman SELinux labeling compatible).
     - `openra-config:/root/.config/openra` (named volume — persists downloaded Content + `lua.log` across restarts; kept out of the repo tree since it's large freeware asset data, not source).
     - `./out:/app/out:Z` (bind mount — battle outputs land on the host, matching current README behavior).
     - `./battles:/app/battles:ro,Z` (bind mount — user can add/edit battle spec JSON without rebuilding, while the container cannot modify specs).
   - `environment: [PORT=2718]` (the host-side override is `HOST_PORT`).
   - top-level `volumes: { openra-config: {} }`.

4. `.dockerignore` — exclude `.git`, `engine/`, `out/`, `__pycache__/`, `*.pyc`, `.run_openra.sh`, `.venv/`. (`engine/` excluded from build context since it's populated at runtime, not baked in; avoids copying a large/partial local extraction into the image.) `.gitignore` also excludes runtime caches and generated outputs; the previously tracked engine/output artifacts are removed from source tracking.
5. `docker/uv.lock` — hash-locks the uv upgrade needed to install the exact Python 3.14.6 runtime.
6. `requirements.lock` — generated with `uv pip compile` for Python 3.14/Linux amd64 with hashes, and used during the image build.

## Modified files
- README.md — add a "Quick Start (Docker/Podman)" section above the manual setup section:
   - `docker compose up --build` (or install a provider with `uv tool install podman-compose` and use `podman compose up --build` / `podman-compose up --build` — the compose file uses standard Compose syntax).
   - Note first run downloads the pinned engine and freeware content archives (cached afterward in `./engine` and the `openra-config` volume).
  - Open `http://localhost:2718` using the token URL printed in the container logs.
  - Keep the existing manual/bare-metal steps under a "Manual Setup (no container)" heading, pointing to openra_battle_recipe.md for full internals — do not delete or rewrite the recipe doc, it remains the reference for how the engine/map/Lua pieces fit together.

## Explicitly out of scope
- Red Alert / Dune 2000 engines or content (not implemented elsewhere in this repo).
- GPU acceleration / hardware rendering (recipe already establishes llvmpipe software rendering is sufficient and even preferred for headless throughput).
- Broader battle-driver changes — the no-systemd fallback is hardened only enough for the container case; simulation behavior remains unchanged.
- Rebuilding `data/units_cnc.json` in the container (already committed, unrelated to installation simplification).

## Verification
1. `docker compose build` succeeds on a clean checkout.
2. `docker compose up`: entrypoint logs show engine download+extract and content download+unzip on first run; container prints a marimo edit URL with token.
3. From host: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2718` returns 200 (or a redirect to the tokened URL).
4. Smoke-test the actual sim end-to-end without the UI: `docker compose exec ora-widget python battle.py --config battles/demo-cnc.json --no-record`, confirm `out/stats.json` appears on the host with a non-"Unknown" `winner` field.
5. `docker compose down && docker compose up`: confirm engine/content are **not** re-downloaded (entrypoint's existence checks short-circuit), so second startup is fast.
6. If podman is available: `podman compose up --build` (or `podman-compose up --build`) as a compatibility check — no Docker-specific compose syntax should be used.

## Further considerations
1. Pin OpenRA release tag as a build ARG (`release-20250330`, same as recipe) vs. always fetching "latest" — recommend pinning for reproducibility, matching the recipe's existing convention. Bumping requires editing `docker/entrypoint.sh`.
