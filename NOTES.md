### ver0.0.3
- Added `matrix.py`, a standalone Marimo payoff-matrix prototype with game, budget, and unit selection backed by Datasette duel data.
- Added role-neutral, budget-normalized matchup scoring based on surviving army value, with icon-based matrix rendering and color-coded results.
- Added `payoff-calc-notes.md` documenting retained HP-equivalent scoring, army-credit contribution, aggregation guidance, and interpretation limits.
- Enhanced `battle.py` statistics with the battle roster, per-side/per-unit-type spawn and survivor counts, surviving HP fractions, and replay metadata.
- Added uniquely named replay copies under `out/replays/`, atomic recording output replacement, ffmpeg diagnostics, and recording timeout handling.
- Made map installation avoid copying host metadata that can cause SELinux permission problems under rootless Podman.
- Updated `ora_widget.py` with colored side summaries, survivor retention matrices with unit icons and tooltips, and a save-replay control.
- Added a final frame sample for timed-out battles and fixed strength-chart aggregation so early attacker HP is retained.

### ver0.0.2
- Added Dockerfile using a digest-pinned amd64 uv image.
- Installs exact Python 3.14.6.
- Added hash-locked Python dependencies in requirements.lock.
- Added hash-locked uv bootstrap dependency in docker/uv.lock.
- Added docker/entrypoint.sh with:
- SHA-256 verification for OpenRA and CNC content.
- Versioned cache markers.
- Temporary extraction directories and validated replacement.
- Explicit amd64 and port validation.
- No runtime dependency resolution.
- Added docker-compose.yml with:
- linux/amd64 platform declaration.
- localhost-only port binding.
- SELinux-compatible :Z bind mounts for Podman.
- Read-only battle specifications.
- Healthcheck.
- Added .dockerignore.
- Updated .gitignore to exclude runtime engine, output, and generated files.
- Removed previously tracked engine/output artifacts and generated config.lua.
- Hardened battle.py so the documented no-systemd fallback works when systemctl and systemd-run are absent.
- Updated README.md and dockerize-plan.md.

### ver0.0.1
- init
