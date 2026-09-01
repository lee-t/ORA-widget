# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "altair<5.5",
#     "httpx==0.28.1",
#     "marimo",
#     "mohtml==0.1.11",
#     "numpy==2.5.1",
#     "polars",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    import io

    import altair as alt
    import httpx
    import marimo as mo
    import numpy as np
    import polars as pl
    from mohtml import div, img, span

    return alt, div, httpx, img, io, mo, np, pl, span


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Data — game, budget, units

    Pick the **game** (which roster and matchups to use) and the **budget**.
    Army size sets the scale: combat is non-linear, so both armies fielding more
    units changes the matchups — `M` is loaded from duels at exactly that budget.
    Use the expandable panel to drop units from the roster. Everything downstream
    rebuilds on any change.
    """)
    return


@app.cell
def _(mo):
    game_dd = mo.ui.dropdown(
        options={
            "Dune 2000 (d2k)": "d2k",
            "Command & Conquer (cnc)": "cnc",
            "Red Alert (ra)": "ra",
        },
        value="Dune 2000 (d2k)",
        label="game",
    )
    budget_dd = mo.ui.dropdown(
        options={f"{b:,} credits": b for b in (2000, 10000, 20000, 50000, 100000)},
        value="100,000 credits",
        label="simulation budget (matrix scale)",
    )
    mo.hstack([game_dd, budget_dd], justify="start", gap=2)
    return budget_dd, game_dd


@app.cell
def _(budget_dd, game_dd, httpx, io, pl):
    def load_csv(sql: str) -> pl.DataFrame:
        resp = httpx.get(
            "https://datasette.exe.xyz/cnc_units.csv",
            params={"sql": sql, "_size": "max"},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return pl.read_csv(io.StringIO(resp.text))

    def load_json(sql: str) -> list[dict]:
        resp = httpx.get(
            "https://datasette.exe.xyz/cnc_units.json",
            params={"sql": sql, "_shape": "array", "_size": "max"},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.json()

    mod = game_dd.value
    budget = budget_dd.value

    # Full roster = the units that actually appear in this game's duels.
    all_units = [
        r["code"]
        for r in load_json(
            f"select distinct attacker as code from duels where mod='{mod}' "
            "order by attacker"
        )
    ]

    duels_df = load_csv(
        "select attacker, defender, atk_hp_left, atk_hp_max, atk_cost_max, "
        "def_hp_left, def_hp_max, def_cost_max "
        f"from duels where mod='{mod}' and budget={budget}"
    )

    # Unit metadata keyed by lowercased code (cnc duels are UPPERCASE, the units
    # table is lowercase — match case-insensitively so all games resolve).
    meta = {
        r["code"].lower(): {
            "name": r["name"],
            "cost": float(r["cost"]),
            "icon": f"data:image/png;base64,{r['icon']['encoded']}",
        }
        for r in load_json(f"select code, name, cost, icon from units where mod='{mod}'")
    }
    return all_units, budget, duels_df, meta


@app.cell
def _(all_units, mo):
    unit_select = mo.ui.multiselect(
        options=all_units, value=all_units, label="units in play"
    )
    mo.accordion({"⚙️ Units — deselect to exclude from the matrix": unit_select})
    return (unit_select,)


@app.cell
def _(all_units, meta, mo, np, unit_select):
    chosen = set(unit_select.value)
    units = [u for u in all_units if u in chosen]
    mo.stop(len(units) < 2, mo.md("**Select at least two units.**"))

    cost = np.array([meta[u.lower()]["cost"] for u in units], dtype=float)
    icons = {u: meta[u.lower()]["icon"] for u in units}
    names = {u: meta[u.lower()]["name"] for u in units}
    return cost, icons, names, units


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Payoff matrix `M`

    We score a duel by **how much of each army's cost survives**, since credits
    are the common currency across units (raw HP isn't comparable — units have
    wildly different HP pools). HP is just how we *normalise* survival: a unit at
    40% HP counts as 40% of its credit value. So each side's surviving value is
    `hp_left / hp_max × credits_fielded`, and the margin from row unit *i* is

    `(value_i − value_j) / budget`.

    (This also penalises units that can't spend the whole budget — some hit a
    unit cap, so they field fewer credits than the budget allows.) Each duel
    contributes to both `M[i,j]` and `M[j,i]`, mixing attacker and defender roles
    → a role-neutral, ~anti-symmetric zero-sum matrix.

    Combat is non-linear in army size, so `M` is **scale-dependent** — it is
    built from duels fought at our target budget. Blue = row unit wins the
    matchup, red = it loses.
    """)
    return


@app.cell
def _(budget, duels_df, np, units):
    idx = {u: k for k, u in enumerate(units)}
    n = len(units)
    _sums = np.zeros((n, n))
    _counts = np.zeros((n, n))

    for row in duels_df.iter_rows(named=True):
        if row["attacker"] not in idx or row["defender"] not in idx:
            continue  # a deselected unit
        a, d = idx[row["attacker"]], idx[row["defender"]]
        # Surviving army *value* in credits (hp fraction × credits fielded),
        # as a fraction of budget. This also penalises units that cannot spend
        # the whole budget (cost_max < budget due to unit caps).
        va = row["atk_hp_left"] / row["atk_hp_max"] * row["atk_cost_max"] / budget
        vd = row["def_hp_left"] / row["def_hp_max"] * row["def_cost_max"] / budget
        margin = va - vd
        _sums[a, d] += margin
        _counts[a, d] += 1
        _sums[d, a] += -margin
        _counts[d, a] += 1

    M = np.divide(_sums, _counts, out=np.zeros_like(_sums), where=_counts > 0)
    return (M,)


@app.cell
def _(M, div, icons, img, mo, names, span, units):
    ICON = 58
    COL = ICON + 20

    def payoff_style(v):
        # v in [-1, 1]: blue = row unit wins, red = row unit loses.
        base = (33, 102, 172) if v >= 0 else (178, 24, 43)
        t = min(abs(v), 1.0)
        rgb = tuple(int(255 + (b - 255) * t) for b in base)
        fg = "#fff" if t > 0.55 else "#1a1a1a"
        return f"background:rgb{rgb};color:{fg};"

    def header(code):
        # Unit name label sitting just above its (pixel-art) icon.
        return div(
            span(
                names[code],
                style="font:600 10px system-ui;color:#555;text-align:center;"
                "line-height:1.15;",
            ),
            img(
                src=icons[code],
                width=str(ICON),
                height=str(ICON),
                title=code,
                style="image-rendering:pixelated;display:block;margin:3px auto 0;",
            ),
            style=f"width:{COL}px;display:flex;flex-direction:column;"
            "align-items:center;justify-content:flex-end;",
        )

    _cell = (
        f"width:{COL}px;height:{COL}px;display:flex;align-items:center;"
        "justify-content:center;font:600 14px system-ui;border-radius:7px;"
    )

    _kids = [div(span("i \\ j", style="font:600 11px system-ui;color:#999;"),
                 style=f"width:{COL}px;display:flex;align-items:flex-end;"
                 "justify-content:center;padding-bottom:6px;")]
    _kids += [header(u) for u in units]
    for i, ui in enumerate(units):
        _kids.append(header(ui))
        for j, uj in enumerate(units):
            v = float(M[i, j])
            if i == j:
                _kids.append(div("–", style=_cell + "background:#f2f2f2;color:#ccc;"))
            else:
                _kids.append(
                    div(
                        f"{v:+.2f}",
                        style=_cell + payoff_style(v),
                        title=f"{ui} vs {uj}: {v:+.2f}",
                    )
                )

    matrix = div(
        *_kids,
        style=(
            f"display:grid;grid-template-columns:repeat({len(units) + 1},{COL}px);"
            "gap:6px;padding:16px;width:fit-content;align-items:end;"
        ),
    )
    # Wrap in a horizontally scrollable container for wide rosters.
    scroller = div(matrix, style="overflow-x:auto;max-width:100%;")
    mo.accordion({f"🔲 Payoff matrix M ({len(units)}×{len(units)})": scroller})
    return