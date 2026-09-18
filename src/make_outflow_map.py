# -*- coding: utf-8 -*-
"""
make_outflow_map.py

One Willamette-basin map showing each Willamette Valley Project dam and the
USGS gauge proposed for its outflow record.

A SIBLING OF make_basin_map.py / make_confluence_map.py
    Same idiom throughout: a settings block at the top, a GeoJSON cache beside
    the script, NLDI for the flowlines, Esri tiles through contextily, haloed
    labels with leader lines, scalebar and north arrow. What is different is
    only the subject - thirteen regulated rivers instead of one, and no
    watershed delineation, which across the whole valley would be a wash of
    outline rather than information.

THE ONE THING TO KNOW ABOUT READING IT
    At basin scale a forebay gauge and its outflow gauge are very nearly the
    same dot - Hills Creek's are 600 ft apart. Both markers are drawn at their
    true positions, but the label belongs to the PAIR and is led out to open
    space. So this map answers "is the right gauge on the right river below
    the right dam", not "is the gauge above or below the dam by 600 feet".
    LABEL_OFFSETS below is hand-tunable for exactly that reason; nudge any
    label that lands on top of another.

INPUT
    data/WIL_OUTFLOW_CANDIDATES.csv, or data/WIL_OUTFLOW_DICT.csv once
    find_outflow_gauges.py has confirmed the picks.

OUTPUT
    out/outflow_gauge_map.png
"""

import os
import json
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import contextily as cx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from shapely.geometry import Point

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
SOURCE_TABLE = os.path.join("..", "data", "WIL_OUTFLOW_CANDIDATES.csv")
OUT_PNG = os.path.join("..", "out", "outflow_gauge_map.png")
CACHE_DIR = "mapdata_outflow"
DPI = 300
FIGSIZE = (11.0, 13.0)

# --- basemap -----------------------------------------------------------------
BASEMAP = "WorldTopoMap"
ZOOM = 10
BASEMAP_ALPHA = 1.0

# --- what the map covers -----------------------------------------------------
EXTENT_PAD = 0.10
# How far to trace each regulated river below its dam, in km. Long enough to
# carry the reach out to the mainstem it joins, so the map reads as a network
# rather than thirteen unconnected dots.
REACH_KM = 70

# --- NLDI / NWIS -------------------------------------------------------------
NLDI_BASES = [
    "https://api.water.usgs.gov/nldi/linked-data",
    "https://labs.waterdata.usgs.gov/api/nldi/linked-data",
]
NWIS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"
HTTP_TIMEOUT = 90

# --- styling -----------------------------------------------------------------
C_NET = "#8fbcdb"
C_MAIN = "#1a4f8a"
C_DAM = "#2c3e50"
C_GAGE = "#c0392b"
C_VERIFY = "#b7791f"
LABEL_HALO = 2.6
LEADER_MIN_POINTS = 22.0

# Label placement, in points from the dam marker. Hand-tuned: the valley puts
# several projects within a few km of each other and the defaults collide.
LABEL_OFFSETS = {
    "Hills Creek": (14, -26),
    "Lookout Point": (-90, -20),
    "Dexter": (26, 10),
    "Fall Creek": (30, -14),
    "Cottage Grove": (-96, -18),
    "Dorena": (26, -20),
    "Cougar": (26, -8),
    "Blue River": (20, 16),
    "Fern Ridge": (-92, 12),
    "Detroit": (26, 14),
    "Big Cliff": (30, -20),
    "Green Peter": (-94, 16),
    "Foster": (26, -22),
}
DEFAULT_OFFSET = (24, 12)

TITLE = "Willamette Valley Project - reservoir outflow gauges"
SUBTITLE = ("Proposed USGS streamflow gauge below each dam, to pair with the "
            "forebay elevation record.\nFlowlines: USGS NHDPlus via NLDI.  "
            "Gauge locations: USGS NWIS.")

SHOW_SCALEBAR = True
SCALEBAR_MI = 10
SCALEBAR_ANCHOR = (0.03, 0.055)
SHOW_NORTH_ARROW = True

WGS84 = "EPSG:4326"
WEBM = "EPSG:3857"

matplotlib.rcParams["font.family"] = "DejaVu Sans"


# ----------------------------------------------------------------------------
# Fetch helpers
# ----------------------------------------------------------------------------
def cache_path(name):
    return os.path.join(CACHE_DIR, name)


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
        print("   NLDI %s" % url)
        text = http_get(url, params)
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            print("      not JSON, trying the next host")
            continue
        if data and data.get("features"):
            return data
        print("      no features, trying the next host")
    return None


def read_cached_geojson(name):
    path = cache_path(name)
    if not os.path.isfile(path):
        return None
    try:
        frame = gpd.read_file(path)
        return frame if len(frame) else None
    except Exception as exc:
        print("   cache %s unreadable (%s), refetching" % (name, exc))
        return None


def fetch_reach(site, label):
    """Downstream-mainstem flowlines below `site`."""
    name = "reach_%s.geojson" % site
    cached = read_cached_geojson(name)
    if cached is not None:
        print("   %-18s cached (%d features)" % (label, len(cached)))
        return cached

    data = nldi_get(
        "nwissite/USGS-%s/navigation/DM/flowlines" % site,
        {"f": "json", "distance": REACH_KM},
    )
    if not data:
        print("   %-18s UNAVAILABLE" % label)
        return None

    frame = gpd.GeoDataFrame.from_features(data["features"], crs=WGS84)
    ensure_cache_dir()
    frame.to_file(cache_path(name), driver="GeoJSON")
    print("   %-18s fetched (%d features)" % (label, len(frame)))
    return frame


def fetch_sites(numbers):
    """
    Coordinates for every site. Nothing is approximated: a site NWIS does not
    return is dropped and named, because a marker at a guessed position would
    answer the question this map exists to answer, wrongly.
    """
    path = cache_path("sites.csv")
    wanted = sorted(set(str(n) for n in numbers))

    if os.path.isfile(path):
        table = pd.read_csv(path, dtype={"site_no": str})
        if set(wanted) <= set(table["site_no"]):
            print("   %-18s cached" % "gage coordinates")
            return table

    print("   NWIS %s" % NWIS_SITE_URL)
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
        print("   *** NWIS returned nothing for %s - those are left off the map"
              % ", ".join(missing))

    if len(table):
        ensure_cache_dir()
        table.to_csv(path, index=False)
    print("   %-18s %d site(s)" % ("gage coordinates", len(table)))
    return table


# ----------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------
def halo(size, weight="normal", color="black"):
    return dict(
        fontsize=size,
        fontweight=weight,
        color=color,
        path_effects=[pe.withStroke(linewidth=LABEL_HALO, foreground="white")],
    )


def annotate_leader(ax, xy, text, offset, color, size=9):
    far = (offset[0] ** 2 + offset[1] ** 2) ** 0.5 >= LEADER_MIN_POINTS
    ax.annotate(
        text,
        xy=xy,
        xytext=offset,
        textcoords="offset points",
        ha="left" if offset[0] >= 0 else "right",
        va="bottom" if offset[1] >= 0 else "top",
        zorder=11,
        arrowprops=(
            dict(arrowstyle="-", color=color, lw=0.9, shrinkA=0, shrinkB=6,
                 alpha=0.85)
            if far else None
        ),
        **halo(size, "bold", color)
    )


def add_scalebar(ax, length_mi=SCALEBAR_MI):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    # Web Mercator metres are only true at the equator; correct by the
    # latitude at the middle of the frame.
    lat = np.degrees(
        2 * np.arctan(np.exp((y0 + y1) / 2 / 6378137.0)) - np.pi / 2
    )
    metres = length_mi * 1609.34 / np.cos(np.radians(lat))

    x_start = x0 + SCALEBAR_ANCHOR[0] * (x1 - x0)
    y_start = y0 + SCALEBAR_ANCHOR[1] * (y1 - y0)

    ax.plot([x_start, x_start + metres], [y_start, y_start],
            color="#22313f", lw=3, solid_capstyle="butt", zorder=12)
    ax.annotate("%d mi" % length_mi,
                xy=(x_start + metres / 2, y_start), xytext=(0, 5),
                textcoords="offset points", ha="center", zorder=12,
                **halo(8.5, "bold", "#22313f"))


def add_north_arrow(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + 0.965 * (x1 - x0)
    y = y0 + 0.055 * (y1 - y0)
    span = 0.045 * (y1 - y0)
    ax.annotate("", xy=(x, y + span), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>", color="#22313f", lw=1.6),
                zorder=12)
    ax.annotate("N", xy=(x, y + span), xytext=(0, 4),
                textcoords="offset points", ha="center", zorder=12,
                **halo(10, "bold", "#22313f"))


def main():
    table = pd.read_csv(
        SOURCE_TABLE, dtype={"Forebay_Site": str, "Outflow_Site": str}
    )
    print("mapping %d dam/gauge pairs\n" % len(table))

    coords = fetch_sites(
        list(table["Forebay_Site"]) + list(table["Outflow_Site"])
    )
    if coords.empty:
        raise SystemExit(
            "No site coordinates came back from NWIS. Check the network, then "
            "delete %s and rerun." % cache_path("sites.csv")
        )
    coords = coords.set_index("site_no")

    print("\nflowlines")
    reaches = []
    for _, row in table.iterrows():
        reach = fetch_reach(str(row["Forebay_Site"]), row["Reservoir"])
        if reach is not None and len(reach):
            reaches.append(reach.to_crs(WEBM))

    def frame_for(column):
        rows = [
            (row["Reservoir"], str(row[column]), row.get("Confidence", ""))
            for _, row in table.iterrows()
            if str(row[column]) in coords.index
        ]
        return gpd.GeoDataFrame(
            {
                "label": [r[0] for r in rows],
                "site": [r[1] for r in rows],
                "confidence": [r[2] for r in rows],
            },
            geometry=[
                Point(coords.loc[r[1], "lon"], coords.loc[r[1], "lat"])
                for r in rows
            ],
            crs=WGS84,
        ).to_crs(WEBM)

    dams = frame_for("Forebay_Site")
    gages = frame_for("Outflow_Site")

    figure, ax = plt.subplots(figsize=FIGSIZE)

    # --- flowlines, drawn under everything ---------------------------------
    for reach in reaches:
        reach.plot(ax=ax, color=C_NET, linewidth=1.0, zorder=2, alpha=0.9)
    for reach in reaches:
        reach.plot(ax=ax, color=C_MAIN, linewidth=1.8, zorder=3, alpha=0.35)

    # --- extent, set from the markers before the basemap is requested ------
    everything = pd.concat([dams.geometry, gages.geometry])
    minx, miny, maxx, maxy = everything.total_bounds
    padx = (maxx - minx) * EXTENT_PAD
    pady = (maxy - miny) * EXTENT_PAD
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)

    # --- markers -----------------------------------------------------------
    dams.plot(ax=ax, marker="s", markersize=52, color=C_DAM,
              edgecolor="white", linewidth=0.9, zorder=6)
    gages.plot(ax=ax, marker="^", markersize=78, color=C_GAGE,
               edgecolor="white", linewidth=0.9, zorder=7)

    # --- one label per PAIR, led out to open space -------------------------
    for (_, dam), (_, gage) in zip(dams.iterrows(), gages.iterrows()):
        verify = str(dam["confidence"]).strip().lower() != "high"
        text = "%s\n%s  >  %s%s" % (
            dam["label"], dam["site"], gage["site"], "  [verify]" if verify else ""
        )
        annotate_leader(
            ax,
            (dam.geometry.x, dam.geometry.y),
            text,
            LABEL_OFFSETS.get(dam["label"], DEFAULT_OFFSET),
            C_VERIFY if verify else "#12507a",
            size=8.5,
        )

    # --- basemap -----------------------------------------------------------
    try:
        if not hasattr(cx.providers.Esri, BASEMAP):
            raise SystemExit(
                "BASEMAP is '%s', which this xyzservices does not have.\n"
                "Available Esri basemaps: %s"
                % (BASEMAP, ", ".join(sorted(cx.providers.Esri.keys())))
            )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cx.add_basemap(ax, source=getattr(cx.providers.Esri, BASEMAP),
                           zoom=ZOOM, alpha=BASEMAP_ALPHA, attribution_size=6)
    except SystemExit:
        raise
    except Exception as exc:
        print("\n   *** BASEMAP NOT DRAWN: %s" % exc)
        print("   The vectors are still correct; only the backdrop is missing.")

    if SHOW_SCALEBAR:
        add_scalebar(ax)
    if SHOW_NORTH_ARROW:
        add_north_arrow(ax)

    ax.legend(
        handles=[
            Line2D([], [], marker="s", linestyle="none", color=C_DAM,
                   markeredgecolor="white", markersize=8,
                   label="Dam / forebay elevation gauge"),
            Line2D([], [], marker="^", linestyle="none", color=C_GAGE,
                   markeredgecolor="white", markersize=9,
                   label="Proposed outflow gauge"),
            Line2D([], [], color=C_MAIN, lw=2,
                   label="Regulated reach below each dam"),
        ],
        loc="upper right", frameon=True, framealpha=0.92, fontsize=9,
    )

    ax.set_title(TITLE, fontsize=15, fontweight="bold", pad=14)
    ax.annotate(SUBTITLE, xy=(0.5, 1.005), xycoords="axes fraction",
                ha="center", va="bottom", fontsize=8.5, color="#40566b")
    ax.set_xticks([])
    ax.set_yticks([])

    out_dir = os.path.dirname(OUT_PNG)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    figure.savefig(OUT_PNG, dpi=DPI, bbox_inches="tight")
    print("\nwrote %s" % OUT_PNG)


if __name__ == "__main__":
    main()
