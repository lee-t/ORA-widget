#!/usr/bin/env python3
"""Extract buildable unit codes, names, and costs from OpenRA mod rules.

Parses the tab-indented MiniYAML dialect (including `Inherits:` templates),
walks the combat rule files, and writes data/units_<mod>.json entries:
{code, name, cost, category}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_miniyaml(text: str) -> dict:
    """Return {key: {"value": str, "children": {}}} for a MiniYAML document."""
    root: dict = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip("\t"))
        key, _, value = stripped.partition(":")
        key = key.strip()
        if key.startswith("-"):  # deletion syntax, irrelevant here
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        node = {"value": value.strip(), "children": {}}
        parent[key] = node
        stack.append((indent, node["children"]))
    return root


def dig(children: dict, *path: str) -> str | None:
    node = children.get(path[0])
    for key in path[1:]:
        if node is None:
            return None
        node = node["children"].get(key)
    return node["value"] if node else None


class Rules:
    def __init__(self, rules_dir: Path, files: list[str]):
        self.docs = {}
        self.templates = {}
        for fname in files:
            doc = parse_miniyaml((rules_dir / fname).read_text())
            self.docs[fname] = doc
            for key, node in doc.items():
                if key.startswith("^"):
                    self.templates[key] = node

    def _resolved_children(self, key: str, node: dict, seen: set) -> dict:
        merged: dict = {}
        inherits = dig(node["children"], "Inherits") or ""
        for parent_name in [p.strip() for p in inherits.split(",") if p.strip()]:
            if parent_name in seen:
                continue
            seen.add(parent_name)
            parent = self.templates.get(parent_name)
            if parent is None:
                continue
            merged.update(
                self._resolved_children(parent_name, parent, seen))
        merged.update(node["children"])
        return merged

    def actors(self) -> dict:
        out = {}
        for doc in self.docs.values():
            for key, node in doc.items():
                if not key.startswith("^"):
                    out[key] = self._resolved_children(key, node, {key})
        return out


CATEGORY_FILES = {
    "vehicle": ["vehicles.yaml"],
    "infantry": ["infantry.yaml"],
    "ship": ["ships.yaml"],
    "aircraft": ["aircraft.yaml"],
}

# Buildable but not combat units.
EXCLUDED_CODES = {"harv", "mcv", "truck", "tran"}


def load_language(mod: str) -> dict:
    """Parse Fluent .ftl files into {"<id>.<attr>": text} lookups."""
    import re

    fluent_dir = ROOT / "engine" / f"openra-{mod}" / "usr/lib/openra" / "mods" / mod / "fluent"
    strings: dict[str, str] = {}
    for ftl in sorted(fluent_dir.glob("*.ftl")):
        current_id = None
        for line in ftl.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line[0].isspace():
                m = re.match(r"^([\w-]+)\s*=\s*(.*)$", line)
                if m:
                    current_id = m.group(1)
                    if m.group(2):
                        strings[current_id] = m.group(2)
                continue
            if current_id:
                a = re.match(r"^\.([\w-]+)\s*=\s*(.*)$", stripped)
                if a and a.group(2):
                    strings[f"{current_id}.{a.group(1)}"] = a.group(2)
    return strings


def extract(mod: str) -> list[dict]:
    rules_dir = ROOT / "engine" / f"openra-{mod}" / "usr/lib/openra" / "mods" / mod / "rules"
    strings = load_language(mod)
    units = []
    seen_codes = set()
    for category, files in CATEGORY_FILES.items():
        rules = Rules(rules_dir, files)
        for code, children in sorted(rules.actors().items()):
            if code in seen_codes or code.lower() in EXCLUDED_CODES:
                continue
            name_key = dig(children, "Tooltip", "Name")
            cost = dig(children, "Valued", "Cost")
            buildable = dig(children, "Buildable", "Queue")
            if not (name_key and cost and buildable):
                continue
            name = strings.get(name_key) or name_key
            seen_codes.add(code)
            units.append({
                "code": code.lower(),
                "name": name,
                "cost": int(cost),
                "category": category,
                "queue": buildable,
            })
    units.sort(key=lambda u: (u["category"], u["cost"]))
    return units


def main() -> None:
    mod = sys.argv[1] if len(sys.argv) > 1 else "cnc"
    units = extract(mod)
    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"units_{mod}.json"
    out.write_text(json.dumps({"mod": mod, "units": units}, indent=2))
    print(f"{len(units)} units -> {out}")
    for u in units:
        print(f"  {u['code']:<12} {u['cost']:>5}  {u['category']:<8} {u['name']}")


if __name__ == "__main__":
    main()
