# ORA Widget

`ora_widget.py` is a Marimo notebook for small, headless OpenRA battles.
It uses the Tiberian Dawn mod. You choose the armies and seed, then view:

- the winner and survivor count
- army strength over time
- losses by unit type
- a recorded battle

## Requirements

- Linux
- Python 3.14 or newer
- `uv`
- `Xvfb`, `xdotool`, `ffmpeg`, and `systemd-run`
- OpenRA Tiberian Dawn files in `engine/openra-cnc`
- Tiberian Dawn game content installed for OpenRA

Install the system tools on Debian or Ubuntu:

```bash
sudo apt install xvfb xdotool ffmpeg unzip libopenal1 libsdl2-2.0-0
```

The notebook declares its Python packages in the script header. `uv` installs
them when you run the notebook.

## Run

From this directory, run:

```bash
uv run --script ora_widget.py
```

Open the local URL shown by Marimo. Set the seed and unit counts, then select
**Fight**. The default battle uses the bundled `data/units_cnc.json` file.

## Outputs

The battle driver writes:

- `out/stats.json`: battle events and summary data
- `out/battle.webm`: the recorded replay

Each run also updates generated runtime files in `maps/arena-cnc` and
`.run_openra.sh`.

## Run Without The Notebook

Use the sample battle specification:

```bash
uv run battle.py --config battles/demo-cnc.json
```

Skip video recording for a faster run:

```bash
uv run battle.py --config battles/demo-cnc.json --no-record
```

## Unit Data

To rebuild the unit list from the OpenRA rules:

```bash
uv run units.py cnc
```

This writes `data/units_cnc.json`.

## Notes

- The notebook currently exposes Tiberian Dawn only.
- A battle needs at least one unit on each side.
- The seed controls the unit order. OpenRA timing can still affect results.
- See `openra_battle_recipe.md` for the full engine and map setup.
