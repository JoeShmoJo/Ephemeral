# -*- coding: utf-8 -*-
"""
make_outflow_map.py

A verification figure for the outflow gauge picks: one small panel per
Willamette Valley Project dam, each zoomed close enough to read whether the
proposed gauge really sits BELOW the dam and on the right river.

WHY A PANEL GRID AND NOT ONE BASIN MAP
    A single Willamette-wide map puts the forebay and its outflow gauge inside
    the same symbol - several of these pairs are under a kilometre apart, and
    Hills Creek's gauge is 600 ft from the dam. At that scale the figure looks
    tidy and proves nothing. One panel per project, each framed on its own
    pair, is the only version that can actually be checked.

DERIVED FROM make_confluence_map.py
    Same idiom - module-level settings block, GeoJSON cache beside the script,
    NLDI for flowlines, Esri tiles through contextily, haloed labels. What is
    different is the subject: thirteen small multiples instead of one basin,
    and no watershed delineation, which at this zoom would be noise.

INPUT
    data/WIL_OUTFLOW_CANDIDATES.csv, or data/WIL_OUTFLOW_REVIEW.csv once
    find_outflow_gauges.py has been run. Set SOURCE_TABLE below.

OUTPUT
    out/outflow_gauge_check.png

WHAT TO LOOK FOR IN EACH PANEL
    - the red gauge triangle is DOWNSTREAM of the blue dam marker, meaning on
      the far side of the impoundment from the lake
    - the flowline between them has no confluence large enough to add
      unmeasured drainage between the release and the gauge
    - the gauge is not sitting on a tributary that merely joins near the dam
"""

import os
import json
import warnings

import pandas as pd
import geopandas as gpd
import contextily as cx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from shapely.geometry import Point

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SOURCE_TABLE = os.path.join("..", "data", "WIL_OUTFLOW_CANDIDATES.csv")
OUT_PNG = os.path.join("..", "out", "outflow_gauge_check.png")
CACHE_DIR = "mapdata_outflow"

DPI = 200
PANEL_COLS = 4
PANEL_SIZE = (3.6, 3.4)

# How much river to draw below each dam, in km. Short: these panels are about
# the reach between the release and the gauge, nothing further.
REACH_KM = 12
# Padding around the dam/gauge pair, as a fraction of the pair's separation.
# Floored by MIN_SPAN_DEG so a 600 ft separation still gets a readable frame.
EXTENT_PAD = 0.9
MIN_SPAN_DEG = 0.035

BASEMAP = "WorldTopoMap"
BASEMAP_ALPHA = 1.0

NLDI_BASES = [
    "https://api.water.usgs.gov/nldi/linked-data",
    "https://labs.waterdata.usgs.gov/api/nldi/linked-data",
]
NWIS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"
HTTP_TIMEOUT = 90

C_RIVER = "#1a4f8a"
C_DAM = "#2c3e50"
C_GAGE = "#c0392b"
LABEL_HALO = 2.4

TITLE = "Willamette Valley Project - proposed outflow gauges"
SUBTITLE = ("Blue square: dam / forebay elevation gauge.  Red triangle: "
            "proposed outflow gauge.\nFlowlines: USGS NHDPlus via NLDI.  "
            "Gauge locations: USGS NWIS.")

WGS84 = "EPSG:4326"
WEBM = "EPSG:3857"

matplotlib.rcParams["font.family"] = "DejaVu Sans"


# ---------------------------------------------------------------------------
# Fetch helpers  (same shape as make_confluence_map.py)
# ---------------------------------------------------------------------------
def ensure_cache_dir():
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def http_get(url, params=None):
    import requests
    try:
        response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        print("      fetch failed: %s" % exc)
        return None


def nldi_get(path, params=None):
    for base in NLDI_BASES:
        url = "%s/%s" % (base, path.lstrip("/"))
        text = http_get(url, params)
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        if data and data.get("features"):
            return data
    return None


def fetch_reach(site):
    """Downstream-mainstem flowlines below `site`, cached as GeoJSON."""
    name = os.path.join(CACHE_DIR, "reach_%s.geojson" % site)
    if os.path.isfile(name):
        try:
            frame = gpd.read_file(name)
            if len(frame):
                return frame
        except Exception:
            pass

    data = nldi_get(
        "nwissite/USGS-%s/navigation/DM/flowlines" % site,
        {"f": "json", "distance": REACH_KM},
    )
    if not data:
        print("   %s: no flowlines" % site)
        return None

    frame = gpd.GeoDataFrame.from_features(data["features"], crs=WGS84)
    ensure_cache_dir()
    frame.to_file(name, driver="GeoJSON")
    return frame


def fetch_sites(numbers):
    """Coordinates for every site, cached as CSV. Nothing is approximated."""
    path = os.path.join(CACHE_DIR, "sites.csv")
    wanted = sorted(set(str(n) for n in numbers))

    if os.path.isfile(path):
        table = pd.read_csv(path, dtype={"site_no": str})
        if set(wanted) <= set(table["site_no"]):
            print("   gage coordinates cached")
            return table

    text = http_get(
        NWIS_SITE_URL,
        {"format": "rdb", "sites": ",".join(wanted), "siteOutput": "expanded"},
    )

    rows = []
    if text:
        lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
        if len(lines) >= 3:
            header = lines[0].split("\t")
            for line in lines[2:]:
                parts = line.split("\t")
                if len(parts) != len(header):
                    continue
                rec = dict(zip(header, parts))
                try:
                    rows.append(
                        {
                            "site_no": rec["site_no"].strip(),
                            "station_nm": rec.get("station_nm", "").strip(),
                            "lat": float(rec["dec_lat_va"]),
                            "lon": float(rec["dec_long_va"]),
                        }
                    )
                except (KeyError, ValueError):
                    continue

    table = pd.DataFrame(rows)
    missing = [n for n in wanted if n not in set(table.get("site_no", []))]
    if missing:
        # Deliberately not falling back to hand-typed coordinates. A panel
        # drawn from a guessed position would answer the one question this
        # figure exists to answer, wrongly.
        print("   *** NWIS returned nothing for %s - those panels are skipped"
              % ", ".join(missing))

    if len(table):
        ensure_cache_dir()
        table.to_csv(path, index=False)
    return table


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
def halo(size, weight, color):
    return {
        "fontsize": size,
        "fontweight": weight,
        "color": color,
        "path_effects": [pe.withStroke(linewidth=LABEL_HALO, foreground="white")],
    }


def panel_extent(dam, gage):
    """Web-Mercator bounds framing the pair, floored so close pairs stay legible."""
    span = max(
        abs(dam.x - gage.x),
        abs(dam.y - gage.y),
        MIN_SPAN_DEG * 111000.0,
    )
    pad = span * EXTENT_PAD
    cx_, cy_ = (dam.x + gage.x) / 2.0, (dam.y + gage.y) / 2.0
    half = span / 2.0 + pad
    return cx_ - half, cx_ + half, cy_ - half, cy_ + half


def draw_panel(ax, row, coords):
    label = row["Reservoir"]
    forebay, outflow = str(row["Forebay_Site"]), str(row["Outflow_Site"])

    if forebay not in coords.index or outflow not in coords.index:
        ax.text(0.5, 0.5, "%s\nno coordinates" % label,
                ha="center", va="center", transform=ax.transAxes, fontsize=8)
        ax.set_axis_off()
        return

    points = gpd.GeoDataFrame(
        {"kind": ["dam", "gage"]},
        geometry=[
            Point(coords.loc[forebay, "lon"], coords.loc[forebay, "lat"]),
            Point(coords.loc[outflow, "lon"], coords.loc[outflow, "lat"]),
        ],
        crs=WGS84,
    ).to_crs(WEBM)

    dam_pt, gage_pt = points.geometry.iloc[0], points.geometry.iloc[1]

    reach = fetch_reach(forebay)
    if reach is not None and len(reach):
        reach.to_crs(WEBM).plot(ax=ax, color=C_RIVER, linewidth=1.6, zorder=3)

    ax.plot([dam_pt.x], [dam_pt.y], marker="s", markersize=7,
            color=C_DAM, markeredgecolor="white", markeredgewidth=0.8, zorder=5)
    ax.plot([gage_pt.x], [gage_pt.y], marker="^", markersize=9,
            color=C_GAGE, markeredgecolor="white", markeredgewidth=0.8, zorder=5)

    ax.annotate(outflow, xy=(gage_pt.x, gage_pt.y), xytext=(6, -12),
                textcoords="offset points", zorder=6, **halo(8, "bold", C_GAGE))
    ax.annotate(forebay, xy=(dam_pt.x, dam_pt.y), xytext=(6, 6),
                textcoords="offset points", zorder=6, **halo(7.5, "normal", C_DAM))

    x0, x1, y0, y1 = panel_extent(dam_pt, gage_pt)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cx.add_basemap(ax, source=getattr(cx.providers.Esri, BASEMAP),
                           alpha=BASEMAP_ALPHA, attribution=False)
    except Exception as exc:
        print("   %s: basemap not drawn (%s)" % (label, exc))

    flag = "" if str(row.get("Confidence", "")).lower() == "high" else "  [VERIFY]"
    ax.set_title("%s%s" % (label, flag), fontsize=9.5, fontweight="bold",
                 color="#b03a2e" if flag else "#12507a")
    ax.set_xticks([])
    ax.set_yticks([])


def main():
    table = pd.read_csv(
        SOURCE_TABLE, dtype={"Forebay_Site": str, "Outflow_Site": str}
    )
    print("resolving %d dam/gauge pairs" % len(table))

    coords = fetch_sites(
        list(table["Forebay_Site"]) + list(table["Outflow_Site"])
    )
    if coords.empty:
        raise SystemExit(
            "No site coordinates came back from NWIS. Check the network, then "
            "delete %s and rerun." % os.path.join(CACHE_DIR, "sites.csv")
        )
    coords = coords.set_index("site_no")

    rows = len(table)
    ncols = PANEL_COLS
    nrows = (rows + ncols - 1) // ncols

    figure, axes = plt.subplots(
        nrows, ncols,
        figsize=(PANEL_SIZE[0] * ncols, PANEL_SIZE[1] * nrows),
    )
    axes = axes.ravel()

    for index, (_, row) in enumerate(table.iterrows()):
        print("   panel %d/%d  %s" % (index + 1, rows, row["Reservoir"]))
        draw_panel(axes[index], row, coords)

    for spare in axes[rows:]:
        spare.set_axis_off()

    figure.suptitle(TITLE, fontsize=15, fontweight="bold", y=0.995)
    figure.text(0.5, 0.965, SUBTITLE, ha="center", fontsize=8.5, color="#40566b")
    figure.tight_layout(rect=[0, 0, 1, 0.95])

    out_dir = os.path.dirname(OUT_PNG)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    figure.savefig(OUT_PNG, dpi=DPI, bbox_inches="tight")
    print("\nwrote %s" % OUT_PNG)


if __name__ == "__main__":
    main()
