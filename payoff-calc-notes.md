# Payoff Calculation Notes

The duel payoff from `matrix.py` should not be used directly for mixed armies.
In a duel, each army contains one unit type, so the result can be attributed to
that matchup. In a mixed battle, targeting, range, positioning, and unit
synergies make that attribution unreliable.

## Retained-value score

The matrix should primarily report the fraction of each unit type's starting
HP-equivalent that remains at the end of the battle:

```text
retention(unit) = sum(surviving unit HP / unit max HP) / units fielded
```

This score is normalized to the range 0 to 1:

- `1.0`: every fielded unit survived at full health
- `0.5`: half of the type's starting HP-equivalent remains
- `0.0`: every fielded unit was destroyed

The same calculation can be expressed in credits:

```text
retention(unit) = surviving credit value / initial credit value
```

Because both values use the same unit cost, the cost cancels. This makes the
score comparable between unit types without allowing an expensive or numerous
type to score higher merely because it represented more of the army budget.

## Army contribution

The previous calculation remains useful as a secondary measure:

```text
contribution(unit) = surviving credit value / credits fielded by the side
```

Equivalently:

```text
contribution(unit) = retention(unit) * initial unit credit share
```

Contribution measures how much of the surviving army value came from a type;
it does not measure that type's survivability. It should therefore be shown in
the tooltip rather than as the matrix's primary score.

## Interpretation

The fielded count should accompany the score. A retention of `1.0` from one
unit provides less evidence than a retention of `0.9` from twenty units.

When combining multiple battles or seeds, aggregate the underlying totals:

```text
retention(unit) = sum(remaining HP fractions) / sum(units fielded)
```

Do not average per-battle scores, because that would give small and large unit
samples equal weight. Even after aggregation, retention describes performance
in the tested army compositions; it is not an intrinsic durability rating.
