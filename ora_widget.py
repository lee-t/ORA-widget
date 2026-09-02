# /// script
# dependencies = [
#     "altair==6.2.2",
#     "anywidget==0.11.0",
#     "marimo==0.24.0",
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
    import base64
    import json
    import random
    from html import escape
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl


    return Path, alt, base64, escape, json, mo, pl


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
            "colors": {"Attacker": "#FE1100", "Defender": "#5B7FE7"},
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
    return (mod_picker,)


@app.cell
def rosters(MODS, mo, mod_picker):
    _mod_info = MODS[mod_picker.value]
    _attacker_defs = _mod_info["attacker_units"]
    _defender_defs = _mod_info["defender_units"]
    seed_input = mo.ui.number(start=0, stop=9999, step=1, value=1, label="Seed")
    save_replay = mo.ui.checkbox(label="Save replay copy", value=False)

    _attacker_inputs = [
        mo.ui.number(
            start=0,
            stop=30,
            step=1,
            value=_mod_info["attacker_defaults"].get(u["code"], 0),
            label=f"{u['name']} ({u['cost']:,} credits)",
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
            label=f"{u['name']} ({u['cost']:,} credits)",
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

    attacker_roster = _unit_rows(_attacker_defs, attacker_ui.elements)
    defender_roster = _unit_rows(_defender_defs, defender_ui.elements)

    fight_btn = mo.ui.run_button(label="Fight")
    return (
        attacker_roster,
        attacker_ui,
        defender_roster,
        defender_ui,
        fight_btn,
        save_replay,
        seed_input,
    )


@app.cell
def selection_credits(MODS, attacker_ui, defender_ui, mod_picker):
    _mod_info = MODS[mod_picker.value]
    attacker_credits = sum(
        u["cost"] * int(value or 0)
        for u, value in zip(_mod_info["attacker_units"], attacker_ui.value)
    )
    defender_credits = sum(
        u["cost"] * int(value or 0)
        for u, value in zip(_mod_info["defender_units"], defender_ui.value)
    )
    return attacker_credits, defender_credits


@app.cell
def run_battle(
    MODS,
    battle_driver,
    attacker_ui,
    defender_ui,
    fight_btn,
    get_battle,
    mod_picker,
    save_replay,
    seed_input,
    set_battle,
):
    if fight_btn.value:
        _mod_info = MODS[mod_picker.value]
        _spec = {
            "mod": mod_picker.value,
            "attacker": [
                {"type": unit["code"], "count": int(value or 0)}
                for unit, value in zip(_mod_info["attacker_units"], attacker_ui.value)
            ],
            "defender": [
                {"type": unit["code"], "count": int(value or 0)}
                for unit, value in zip(_mod_info["defender_units"], defender_ui.value)
            ],
            "grid_cols": 4,
            "seed": int(seed_input.value or 0),
            "save_replay": bool(save_replay.value),
        }
        if (
            sum(group["count"] for group in _spec["attacker"]) == 0
            or sum(group["count"] for group in _spec["defender"]) == 0
        ):
            set_battle({"error": "Both armies need at least one unit."})
        else:
            set_battle(
                battle_driver.run_battle(
                    _spec,
                    record=True,
                    save_replay=_spec["save_replay"],
                )
            )

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
        _colors = _info.get("colors", {})
        _atk_color = _colors.get("Attacker", "#FE1100")
        _def_color = _colors.get("Defender", "#5B7FE7")
        if "winner" in battle:
            _surv = battle.get("survivors", {})
            _spawn = battle.get("spawned", {})
            _seed = battle.get("seed", "?")
            _kills = len(battle.get("kills", []))
            _atk_spawned = _spawn.get("Attacker", 0)
            _def_spawned = _spawn.get("Defender", 0)
            _atk_survivors = _surv.get("Attacker", 0)
            _def_survivors = _surv.get("Defender", 0)
            _result_table = (
                "| Side | Survivors | Losses |\n"
                "|:--|--:|--:|\n"
                f'| <span style="color:{_atk_color}"><strong>Attacker - {_atk}</strong></span> | '
                f"{_atk_survivors}/{_atk_spawned} | "
                f"{_atk_spawned - _atk_survivors} |\n"
                f'| <span style="color:{_def_color}"><strong>Defender - {_def}</strong></span> | '
                f"{_def_survivors}/{_def_spawned} | "
                f"{_def_spawned - _def_survivors} |"
            )
            battle_status = mo.callout(
                mo.md(
                    f"**{battle['winner']}** wins in {battle['ticks']} ticks "
                    f"- seed {_seed}, {_kills} kills\n\n"
                    f"{_result_table}"
                ),
                kind="success",
            )
        else:
            battle_status = mo.md(f"Battle result: {battle}")
    return (battle_status,)


@app.cell
def strength_chart(MODS, alt, battle, mo, pl):
    if battle and battle.get("strength"):
        _colors = MODS.get(battle.get("mod"), {}).get("colors", {})
        _plot_df = pl.DataFrame(battle["strength"]).unpivot(
            index=["tick"], on=["Attacker", "Defender"], variable_name="Side", value_name="Strength"
        )
        strength_chart = (
            alt.Chart(_plot_df, title="Army strength over time")
            .mark_line()
            .encode(
                x=alt.X("tick:Q", title="Tick"),
                y=alt.Y("Strength:Q", title="Combined HP%"),
                color=alt.Color(
                    "Side:N",
                    scale=alt.Scale(
                        domain=["Attacker", "Defender"],
                        range=[
                            _colors.get("Attacker", "#FE1100"),
                            _colors.get("Defender", "#5B7FE7"),
                        ],
                    ),
                ),
            )
            .properties(height=280)
        )
    else:
        strength_chart = mo.md("Run a battle to see strength over time.")
    return (strength_chart,)


@app.cell
def kills_chart(MODS, alt, battle, mo, pl):
    if battle and battle.get("kills"):
        _colors = MODS.get(battle.get("mod"), {}).get("colors", {})
        _kill_df = pl.DataFrame(battle["kills"]).group_by("side", "victim").len()
        kills_chart = (
            alt.Chart(_kill_df, title="Losses by unit type")
            .mark_bar()
            .encode(
                x=alt.X("len:Q", title="Units lost"),
                y=alt.Y("victim:N", sort="-x", title="Unit"),
                color=alt.Color(
                    "side:N",
                    title="Side",
                    scale=alt.Scale(
                        domain=["Attacker", "Defender"],
                        range=[
                            _colors.get("Attacker", "#FE1100"),
                            _colors.get("Defender", "#5B7FE7"),
                        ],
                    ),
                ),
                tooltip=["side:N", "victim:N", "len:Q"],
            )
            .properties(height=280)
        )
    else:
        kills_chart = mo.md("Run a battle to see the kill breakdown.")
    return (kills_chart,)


@app.cell
def survivor_matrix(
    MODS,
    Path,
    attacker_credits,
    attacker_ui,
    base64,
    battle,
    defender_credits,
    defender_ui,
    escape,
    mo,
    mod_picker,
):
    if not battle or "error" in battle:
        survivor_matrix = mo.md("Run a battle to see surviving units by type.")
    else:
        _info = MODS.get(battle.get("mod"), MODS[mod_picker.value])
        _attacker_defs = _info["attacker_units"]
        _defender_defs = _info["defender_units"]
        _sides = ("Attacker", "Defender")
        _unit_defs = {
            unit["code"]: unit
            for unit in (*_attacker_defs, *_defender_defs)
        }
        _selected = {}
        _roster = battle.get("roster")
        if _roster is not None:
            for _side in _sides:
                for _group in _roster.get(_side, []):
                    _code = _group.get("type")
                    if (
                        _code in _unit_defs
                        and int(_group.get("count", 0) or 0) > 0
                    ):
                        _selected.setdefault(_code, _unit_defs[_code])
        else:
            for _unit, _value in zip(_attacker_defs, attacker_ui.value):
                if int(_value or 0) > 0:
                    _selected[_unit["code"]] = _unit
            for _unit, _value in zip(_defender_defs, defender_ui.value):
                if int(_value or 0) > 0:
                    _selected.setdefault(_unit["code"], _unit)
        _units = list(_selected.values())

        if not _units:
            survivor_matrix = mo.md("Select at least one unit to see survivors.")
        else:
            _spawned = battle.get("spawned_by_type", {})
            _survived = battle.get("survivors_by_type", {})
            _survivor_hp = battle.get("survivor_hp_by_type", {})
            _credits_used = {
                "Attacker": int(attacker_credits),
                "Defender": int(defender_credits),
            }
            if _roster is not None:
                _credits_used = {
                    side: sum(
                        int(group.get("count", 0) or 0)
                        * _unit_defs[group["type"]]["cost"]
                        for group in _roster.get(side, [])
                        if group.get("type") in _unit_defs
                    )
                    for side in _sides
                }
            _side_labels = {
                "Attacker": _info.get("attacker", "Attacker"),
                "Defender": _info.get("defender", "Defender"),
            }
            _side_colors = _info.get(
                "colors", {"Attacker": "#FE1100", "Defender": "#5B7FE7"}
            )
            _icon_size = 58
            _column_size = _icon_size + 20

            def _icon_data(unit):
                encoded = base64.b64encode(
                    Path(unit["icon"]).read_bytes()
                ).decode("ascii")
                return f"data:image/png;base64,{encoded}"

            def _header(unit):
                _name = escape(str(unit["name"]))
                return (
                    f"<div style='width:{_column_size}px;display:flex;"
                    "flex-direction:column;align-items:center;"
                    "justify-content:flex-end;'>"
                    f"<span style='font:600 10px system-ui;color:#555;"
                    f"text-align:center;line-height:1.15;'>{_name}<br>"
                    f"<span style='font-weight:500;color:#888;'>"
                    f"{unit['cost']:,} cr</span></span>"
                    f"<img src='{_icon_data(unit)}' width='{_icon_size}' "
                    f"height='{_icon_size}' alt='{_name}' title='{unit['code']}' "
                    "style='image-rendering:pixelated;display:block;"
                    "margin:3px auto 0;'>"
                    "</div>"
                )

            def _result_cell(side, unit):
                _code = unit["code"]
                _fielded = int(_spawned.get(side, {}).get(_code, 0))
                _survivors = int(_survived.get(side, {}).get(_code, 0))
                if not _fielded:
                    _title = escape(
                        f"{side} did not field {unit['name']}"
                    )
                    return (
                        f"<div style='width:{_column_size}px;height:58px;display:flex;"
                        "align-items:center;justify-content:center;"
                        "font:600 14px system-ui;border-radius:7px;"
                        "background:#f2f2f2;color:#bbb;'"
                        f" title='{_title}'>-</div>"
                    )

                _hp_fraction = float(
                    _survivor_hp.get(side, {}).get(_code, _survivors)
                )
                _surviving_value = _hp_fraction * unit["cost"]
                _initial_value = _fielded * unit["cost"]
                _retention = _surviving_value / _initial_value
                _budget = _credits_used[side]
                _contribution = (
                    _surviving_value / _budget if _budget > 0 else 0.0
                )
                _ratio = min(max(_retention, 0.0), 1.0)
                _low = (178, 24, 43)
                _high = (33, 102, 172)
                _rgb = tuple(
                    int(low + (high - low) * _ratio)
                    for low, high in zip(_low, _high)
                )
                _style = (
                    f"width:{_column_size}px;height:58px;display:flex;"
                    "align-items:center;justify-content:center;"
                    f"font:600 16px system-ui;border-radius:7px;"
                    f"background:rgb{_rgb};color:#fff;"
                )
                _title = escape(
                    f"{side}: {_survivors} of {_fielded} {unit['name']} "
                    f"survived; {_retention:.1%} HP-equivalent retained; "
                    f"{_surviving_value:,.0f} surviving credits; "
                    f"{_contribution:.1%} of the side's fielded credits"
                )
                return (
                    f"<div style='{_style}'"
                    f" title='{_title}'>{_retention:.2f}</div>"
                )

            _grid_cells = [
                f"<div style='width:{_column_size}px;display:flex;"
                "align-items:flex-end;justify-content:center;"
                "padding-bottom:6px;font:600 11px system-ui;color:#999;'>"
                "survived</div>"
            ]
            _grid_cells.extend(_header(unit) for unit in _units)
            for side in _sides:
                _label_color = _side_colors.get(side, "#555")
                _grid_cells.append(
                    f"<div style='width:{_column_size}px;height:58px;display:flex;"
                    "align-items:center;justify-content:center;"
                    f"font:600 11px system-ui;color:{_label_color};"
                    "text-align:center;'>"
                    f"{escape(str(_side_labels[side]))}<br>"
                    f"<span style='font-weight:500;color:#888;'>"
                    f"{_credits_used[side]:,} cr</span></div>"
                )
                _grid_cells.extend(_result_cell(side, unit) for unit in _units)

            _matrix = (
                "<div style='overflow-x:auto;max-width:100%;'>"
                f"<div style='display:grid;grid-template-columns:repeat("
                f"{len(_units) + 1},{_column_size}px);gap:6px;padding:16px;"
                "width:fit-content;align-items:end;'>"
                + "".join(_grid_cells)
                + "</div></div>"
            )
            survivor_matrix = mo.accordion(
                {
                    f"Payoff matrix - survivors by unit type "
                    f"({len(_units)} selected)": mo.vstack(
                        [
                            mo.md(
                                "Each cell is unit-type retention: "
                                "`sum of surviving HP fractions ÷ units "
                                "fielded`. The tooltip also shows surviving "
                                "bodies, credit value, and army contribution."
                            ),
                            mo.Html(_matrix),
                        ],
                        align="start",
                        gap=0.5,
                    )
                }
            )
    return (survivor_matrix,)


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
    save_replay,
    seed_input,
    strength_chart,
    survivor_matrix,
    attacker_credits,
    defender_credits,
):
    _info = MODS[mod_picker.value]

    mo.vstack(
        [
            mo.md("# Opera Battles - arena widget"),
            mo.hstack(
                [mod_picker, seed_input, save_replay, fight_btn],
                justify="start",
                align="center",
            ),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md(
                                f"### Attacker - {_info['attacker']}\n\n"
                                f"**Credits used:** {attacker_credits:,}"
                            ),
                            attacker_roster,
                        ],
                        align="start",
                        gap=0.75,
                    ),
                    mo.vstack(
                        [
                            mo.md(
                                f"### Defender - {_info['defender']}\n\n"
                                f"**Credits used:** {defender_credits:,}"
                            ),
                            defender_roster,
                        ],
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
            survivor_matrix,
            mo.hstack([strength_chart, kills_chart], align="start", wrap=True),
        ],
        align="stretch",
        gap=1,
    )
    return


if __name__ == "__main__":
    app.run()
