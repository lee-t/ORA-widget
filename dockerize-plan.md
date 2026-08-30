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
   - Base: `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` (uv + Python 3.14 preinstalled, matches `.python-version`). If that exact tag doesn't exist at build time, fall back to `ghcr.io/astral-sh/uv:bookworm-slim` + `RUN uv python install 3.14`.
   - `apt-get install`: `xvfb xdotool ffmpeg unzip curl ca-certificates procps libopenal1 libsdl2-2.0-0 libgl1 libgl1-mesa-dri` (same list as README's manual apt install, plus `procps` for `pgrep` used in `battle.py:start_xvfb()`, plus mesa/GL libs for llvmpipe software rendering under Xvfb, plus `curl`/`ca-certificates` for runtime downloads).
   - `RUN uv pip install --system marimo` so the `marimo` CLI is available to launch `ora_widget.py` (its own deps — anywidget, altair, polars, traitlets — are installed on demand via `--sandbox`, reusing the inline PEP 723 header already in ora_widget.py).
   - `WORKDIR /app`, `COPY . /app` (respecting `.dockerignore`).
   - `COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh` + `chmod +x`.
   - `EXPOSE 2718`.
   - `ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]`.

2. `docker/entrypoint.sh` — idempotent setup + launch, run as root at container start:
   - Step A — engine: if `engine/openra-cnc/usr/bin/openra-cnc-utility` is missing, download+extract per openra_battle_recipe.md Step 1 (cnc only): `curl -sLO .../OpenRA-Tiberian-Dawn-x86_64.AppImage`, `chmod +x`, `./*.AppImage --appimage-extract` (no FUSE needed — this flag is exactly the container-friendly extraction path), `mv squashfs-root engine/openra-cnc`. Release tag pinned via `ARG`/`ENV OPENRA_RELEASE=release-20250330` (matches recipe).
   - Step B — content: if `$HOME/.config/openra/Content/cnc` is missing/empty, download+unzip per recipe Step 2 (cnc only): `curl -sL "$(curl -s https://www.openra.net/packages/cnc-mirrors.txt | head -1)" -o /tmp/cnc.zip`, `unzip /tmp/cnc.zip -d "$HOME/.config/openra/Content/cnc/"`.
   - Step C — exec the notebook server: `exec marimo edit --sandbox --headless --host 0.0.0.0 --port "${PORT:-2718}" ora_widget.py`.
   - Fail loudly (`set -euo pipefail`) with a clear message if a download fails, rather than silently starting with a broken engine.

3. `docker-compose.yml` — repo root, single service `ora-widget`:
   - `build: .`
   - `ports: ["127.0.0.1:2718:2718"]`
   - `volumes:`
     - `./engine:/app/engine` (bind mount — persists the extracted engine across container recreation, visible on host, reuses the existing `engine/` convention already in the repo).
     - `openra-config:/root/.config/openra` (named volume — persists downloaded Content + `lua.log` across restarts; kept out of the repo tree since it's large freeware asset data, not source).
     - `./out:/app/out` (bind mount — battle outputs land on the host, matching current README behavior).
     - `./battles:/app/battles` (bind mount — user can add/edit battle spec JSON without rebuilding).
   - `environment: [PORT=2718]` (optional override).
   - top-level `volumes: { openra-config: {} }`.

4. `.dockerignore` — exclude `.git`, `engine/`, `out/`, `__pycache__/`, `*.pyc`, `.run_openra.sh`, `.venv/`. (`engine/` excluded from build context since it's populated at runtime, not baked in; avoids copying a large/partial local extraction into the image.)

## Modified files
- README.md — add a "Quick Start (Docker/Podman)" section above the current "Requirements" section:
  - `docker compose up --build` (or `podman compose up --build` / `podman-compose up --build` — the compose file uses plain syntax, no Docker-specific extensions).
  - Note first run downloads ~250MB engine + ~300MB freeware content (cached afterward in `./engine` and the `openra-config` volume).
  - Open `http://localhost:2718` using the token URL printed in the container logs.
  - Keep the existing manual/bare-metal steps under a "Manual Setup (no container)" heading, pointing to openra_battle_recipe.md for full internals — do not delete or rewrite the recipe doc, it remains the reference for how the engine/map/Lua pieces fit together.

## Explicitly out of scope
- Red Alert / Dune 2000 engines or content (not implemented elsewhere in this repo).
- GPU acceleration / hardware rendering (recipe already establishes llvmpipe software rendering is sufficient and even preferred for headless throughput).
- Changes to `battle.py`'s launch fallback logic — it already handles the no-systemd-in-container case (see the "Molab containers" comment in `launch_game()`), so no code changes needed there.
- Rebuilding `data/units_cnc.json` in the container (already committed, unrelated to installation simplification).

## Verification
1. `docker compose build` succeeds on a clean checkout.
2. `docker compose up`: entrypoint logs show engine download+extract and content download+unzip on first run; container prints a marimo edit URL with token.
3. From host: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2718` returns 200 (or a redirect to the tokened URL).
4. Smoke-test the actual sim end-to-end without the UI: `docker compose exec ora-widget uv run battle.py --config battles/demo-cnc.json --no-record`, confirm `out/stats.json` appears on the host with a non-"Unknown" `winner` field.
5. `docker compose down && docker compose up`: confirm engine/content are **not** re-downloaded (entrypoint's existence checks short-circuit), so second startup is fast.
6. If podman is available: `podman compose up --build` (or `podman-compose up --build`) as a compatibility check — no Docker-specific compose syntax should be used.

## Further considerations
1. Pin OpenRA release tag as a build ARG (`release-20250330`, same as recipe) vs. always fetching "latest" — recommend pinning for reproducibility, matching the recipe's existing convention. Bumping requires editing `docker/entrypoint.sh`.
