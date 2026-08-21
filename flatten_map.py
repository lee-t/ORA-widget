#!/usr/bin/env python3
"""Generate a flat, obstacle-free map.bin for each arena (MapFormat 12).

Layout: u8 format | u16 width | u16 height | u32 tile offset |
u32 height offset (0 = absent) | u32 resource offset.
Tiles: u16 template + u8 frame per cell. Resources: u8 type + u8 density.
"""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Per-tileset "featureless ground" template:
#   RA/TD desert: template 255 ("Clear"), 16 frames
#   Dune ARRAKIS: template 266 ("Rock"), 17 frames
ARENAS = {
    "maps/arena": (255, 16),
    "maps/arena-cnc": (255, 16),
    "maps/arena-d2k": (266, 17),
}

# Binary map.bin header format (1 = fixed layout, 2 = explicit offsets).
# Note: this is separate from the `MapFormat:` version in map.yaml.
BIN_FORMAT = 2

W = H = 72


def make_map_bin(path: Path, clear: int, frames: int) -> None:
    tile_off = 17
    res_off = tile_off + W * H * 3
    header = struct.pack("<BHHIII", BIN_FORMAT, W, H, tile_off, 0, res_off)

    tiles = bytearray()
    for i in range(W * H):
        idx = (i * 7 + (i // W) * 3) % frames
        tiles += struct.pack("<HB", clear, idx)

    resources = bytes(W * H * 2)
    path.write_bytes(header + bytes(tiles) + resources)
    print(f"wrote {path} ({path.stat().st_size} bytes)")


def main() -> None:
    for rel, (clear, frames) in ARENAS.items():
        arena = ROOT / rel
        if not arena.exists():
            continue
        make_map_bin(arena / "map.bin", clear, frames)


if __name__ == "__main__":
    main()
