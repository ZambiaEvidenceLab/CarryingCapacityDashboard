"""Per-Sector map colour identity (ADR-0017 lever 2; colour rules in `.scratch/cca-v2/spec.md`).

Each Sector gets its own light-to-dark single-hue sequential ramp for the
choropleth — dark = high capacity, pale = more underserved — so switching
Sectors re-hues the map and gives each Sector a stable visual identity across
views. `SECTOR_HUE_ANCHOR` is each ramp's identity colour (its middle stop);
the five anchors were checked with the dataviz skill's CVD-separation method
(OKLab, Machado-Oliveira-Fernandes simulation) in the fixed Sector order
below — the order `cca.dashboard.app._ordered_sectors()` derives from
`CCA_indicator_list.csv` — and clear both gates on that adjacent pairlist:
worst adjacent CVD deltaE 21.6 (protan, >= 8 target) and worst adjacent
normal-vision deltaE 29.0 (>= 15 floor). If a Sector is ever added or
reordered, re-check the new adjacent pairs before reusing these hexes.
"""

from __future__ import annotations

import colorsys

SECTOR_HUE_ANCHOR: dict[str, str] = {
    "Health": "#e34948",
    "Education": "#2a78d6",
    "Agriculture": "#008300",
    "Infrastructure": "#4a3aa7",
    "Environment": "#eda100",
}


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def _build_ramp(anchor_hex: str) -> list[list]:
    """A 3-stop light -> anchor -> dark sequential colourscale, one hue, from `anchor_hex`."""
    hue, lightness, saturation = colorsys.rgb_to_hls(*_hex_to_rgb(anchor_hex))
    light_rgb = colorsys.hls_to_rgb(hue, 0.93, saturation * 0.7)
    dark_rgb = colorsys.hls_to_rgb(hue, min(lightness * 0.55, 0.30), min(saturation * 1.05, 1.0))
    return [[0.0, _rgb_to_hex(light_rgb)], [0.5, anchor_hex], [1.0, _rgb_to_hex(dark_rgb)]]


SECTOR_RAMP: dict[str, list[list]] = {sector: _build_ramp(anchor) for sector, anchor in SECTOR_HUE_ANCHOR.items()}
