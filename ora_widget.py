# /// script
# dependencies = [
#     "altair==6.2.2",
#     "anywidget==0.11.0",
#     "marimo",
#     "polars==1.43.2",
#     "traitlets==5.16.1",
# ]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def widget_libs():
    import anywidget
    import traitlets

    return


@app.cell
def imports():
    import json
    import random
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl


    return Path, alt, json, mo, pl


@app.cell
def driver():
    import importlib.util as _importlib_util
    from pathlib import Path as _Path

    _driver_path = _Path("battle.py").resolve()
    _driver_spec = _importlib_util.spec_from_file_location("_ora_battle_driver", _driver_path)
    if _driver_spec is None or _driver_spec.loader is None:
        raise ImportError(f"Unable to load battle driver from {_driver_path}")
    battle_driver = _importlib_util.module_from_spec(_driver_spec)
    _driver_spec.loader.exec_module(battle_driver)

    return (battle_driver,)


@app.cell
def unit_data(Path, json):
    _catalog = json.loads(Path("data/units_cnc.json").read_text())["units"]
    _catalog_by_code = {u["code"]: u for u in _catalog}
    _icon_dir = Path("data/icons/cnc").resolve()

    # Combat rosters follow the CNCNZ GDI/NOD unit pages; support units are omitted.
    _nod_codes = [
        "e1", "e3", "e6", "e4", "e5", "rmbo",
        "bggy", "bike", "ltnk", "arty", "ftnk", "stnk", "mlrs", "heli",
    ]
    _gdi_codes = [
        "e1", "e2", "e3", "e6", "rmbo",
        "jeep", "apc", "mtnk", "htnk", "msam", "orca",
    ]

    def _make_units(codes):
        return [
            {
                **_catalog_by_code[code],
                "dps": round(_catalog_by_code[code]["cost"] / 100, 1),
                "icon": _icon_dir / f"{code}.png",
            }
            for code in codes
        ]

    MODS = {
        "cnc": {
            "label": "Tiberian Dawn",
            "attacker": "NOD",
            "defender": "GDI",
            "attacker_units": _make_units(_nod_codes),
            "defender_units": _make_units(_gdi_codes),
            "attacker_defaults": {"bggy": 4, "bike": 4},
            "defender_defaults": {"mtnk": 6, "msam": 2, "e1": 6},
        },
    }
    return (MODS,)


@app.cell
def battle_state(mo):
    get_battle, set_battle = mo.state(None)
    return get_battle, set_battle


@app.cell
def controls(MODS, mo):
    mod_picker = mo.ui.dropdown(
        options={info["label"]: key for key, info in MODS.items()},
        value="Tiberian Dawn",
        label="Game",
    )
    seed_input = mo.ui.number(start=0, stop=9999, step=1, value=1, label="Seed")
    fight_btn = mo.ui.run_button(label="Fight")
    return fight_btn, mod_picker, seed_input


@app.cell
def rosters(MODS, mo, mod_picker):
    _mod_info = MODS[mod_picker.value]
    _attacker_defs = _mod_info["attacker_units"]
    _defender_defs = _mod_info["defender_units"]

    _attacker_inputs = [
        mo.ui.number(
            start=0,
            stop=30,
            step=1,
            value=_mod_info["attacker_defaults"].get(u["code"], 0),
            label=f"{u['name']} ({u['cost']} credits)",
            full_width=False,
        )
        for u in _attacker_defs
    ]
    _defender_inputs = [
        mo.ui.number(
            start=0,
            stop=30,
            step=1,
            value=_mod_info["defender_defaults"].get(u["code"], 0),
            label=f"{u['name']} ({u['cost']} credits)",
            full_width=False,
        )
        for u in _defender_defs
    ]

    attacker_ui = mo.ui.array(_attacker_inputs, label="Attacker roster")
    defender_ui = mo.ui.array(_defender_inputs, label="Defender roster")

    def _unit_rows(units, inputs):
        return mo.vstack(
            [
                mo.hstack(
                    [
                        mo.image(
                            unit["icon"],
                            alt=unit["name"],
                            width=48,
                            rounded=True,
                        ),
                        control,
                    ],
                    align="center",
                    justify="start",
                    gap=0.75,
                )
                for unit, control in zip(units, inputs)
            ],
            align="start",
            gap=0.35,
        )

    attacker_roster = _unit_rows(_attacker_defs, _attacker_inputs)
    defender_roster = _unit_rows(_defender_defs, _defender_inputs)
    return attacker_roster, attacker_ui, defender_roster, defender_ui


@app.cell
def run_battle(
    MODS,
    attacker_ui,
    battle_driver,
    defender_ui,
    fight_btn,
    get_battle,
    mod_picker,
    seed_input,
    set_battle,
):
    _mod_info = MODS[mod_picker.value]
    _attacker_defs = _mod_info["attacker_units"]
    _defender_defs = _mod_info["defender_units"]
    _attacker_counts = [
        (u["code"], int(v or 0))
        for u, v in zip(_attacker_defs, attacker_ui.value)
    ]
    _defender_counts = [
        (u["code"], int(v or 0))
        for u, v in zip(_defender_defs, defender_ui.value)
    ]

    if fight_btn.value:
        if sum(v for _, v in _attacker_counts) == 0 or sum(v for _, v in _defender_counts) == 0:
            set_battle({"error": "Both armies need at least one unit."})
        else:
            _spec = {
                "mod": mod_picker.value,
                "attacker": [{"type": t, "count": n} for t, n in _attacker_counts],
                "defender": [{"type": t, "count": n} for t, n in _defender_counts],
                "grid_cols": 4,
                "seed": int(seed_input.value),
            }
            set_battle(battle_driver.run_battle(_spec, record=True))

    battle = get_battle()
    return (battle,)


@app.cell
def status(MODS, battle, mo):
    if battle is None:
        battle_status = mo.md("Configure the rosters and press **Fight** to run a battle.")
    elif "error" in battle:
        battle_status = mo.callout(mo.md(battle["error"]), kind="warn")
    else:
        _info = MODS.get(battle.get("mod"), {})
        _atk = _info.get("attacker", "Attacker")
        _def = _info.get("defender", "Defender")
        if "winner" in battle:
            _surv = battle.get("survivors", {})
            _spawn = battle.get("spawned", {})
            _seed = battle.get("seed", "?")
            _kills = len(battle.get("kills", []))
            battle_status = mo.callout(
                mo.md(
                    f"**{battle['winner']}** wins in {battle['ticks']} ticks "
                    f"({_atk} {_surv.get('Attacker', '?')}/{_spawn.get('Attacker', '?')} alive vs "
                    f"{_def} {_surv.get('Defender', '?')}/{_spawn.get('Defender', '?')} alive) "
                    f"- seed {_seed}, {_kills} kills"
                ),
                kind="success",
            )
        else:
            battle_status = mo.md(f"Battle result: {battle}")
    return (battle_status,)


@app.cell
def strength_chart(alt, battle, mo, pl):
    if battle and battle.get("strength"):
        _plot_df = pl.DataFrame(battle["strength"]).unpivot(
            index=["tick"], on=["Attacker", "Defender"], variable_name="Side", value_name="Strength"
        )
        strength_chart = (
            alt.Chart(_plot_df, title="Army strength over time")
            .mark_line()
            .encode(
                x=alt.X("tick:Q", title="Tick"),
                y=alt.Y("Strength:Q", title="Combined HP%"),
                color="Side:N",
            )
            .properties(height=280)
        )
    else:
        strength_chart = mo.md("Run a battle to see strength over time.")
    return (strength_chart,)


@app.cell
def kills_chart(alt, battle, mo, pl):
    if battle and battle.get("kills"):
        _kill_df = pl.DataFrame(battle["kills"]).group_by("side", "victim").len()
        kills_chart = (
            alt.Chart(_kill_df, title="Losses by unit type")
            .mark_bar()
            .encode(
                x=alt.X("len:Q", title="Units lost"),
                y=alt.Y("victim:N", sort="-x", title="Unit"),
                color=alt.Color("side:N", title="Side"),
                tooltip=["side:N", "victim:N", "len:Q"],
            )
            .properties(height=280)
        )
    else:
        kills_chart = mo.md("Run a battle to see the kill breakdown.")
    return (kills_chart,)


@app.cell
def video(battle, mo):
    if battle and battle.get("video"):
        battle_video = mo.video(src=battle["video"], width=640)
    else:
        battle_video = mo.md("Fight a battle to record a replay.")
    return (battle_video,)


@app.cell
def layout(
    MODS,
    attacker_roster,
    battle_status,
    battle_video,
    defender_roster,
    fight_btn,
    kills_chart,
    mo,
    mod_picker,
    seed_input,
    strength_chart,
):
    _info = MODS[mod_picker.value]

    mo.vstack(
        [
            mo.md("# Opera Battles - arena widget"),
            mo.hstack([mod_picker, seed_input, fight_btn], justify="start", align="center"),
            mo.hstack(
                [
                    mo.vstack(
                        [mo.md(f"### Attacker - {_info['attacker']}"), attacker_roster],
                        align="start",
                        gap=0.75,
                    ),
                    mo.vstack(
                        [mo.md(f"### Defender - {_info['defender']}"), defender_roster],
                        align="start",
                        gap=0.75,
                    ),
                ],
                align="start",
                widths="equal",
                wrap=True,
                gap=1.5,
            ),
            battle_status,
            battle_video,
            mo.hstack([strength_chart, kills_chart], align="start", wrap=True),
        ],
        align="stretch",
        gap=1,
    )
    return


if __name__ == "__main__":
    app.run()
