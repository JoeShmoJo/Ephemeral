# -*- coding: utf-8 -*-
"""
boat_ramp_days.py

Boat ramp days for each Willamette Valley Project pool and for the system, over
the 01 Feb - 15 Dec recreation season, from ten years of daily pool elevation.

THE METRIC
    A ramp counts for a day when the pool is at or above that ramp's minimum
    operable elevation. Ramp days sum over ramps AND days, so five usable ramps
    at Lookout Point for a 30-day month is 150 ramp days. That makes the number
    proportional to how much launching capacity was actually available, which
    is the point - but it also means a project with more ramps scores higher
    without being operated any better, so every figure here reports the
    percent-of-potential alongside the raw count.

    potential(project, year) = ramps * days in season
    ramp_days / potential is what to compare across projects.

WHAT IT PRODUCES
    out/boat_ramp_days_box.png       annual ramp days by project, ten years
    out/boat_ramp_duration.png       pool elevation duration vs ramp thresholds
    out/boat_ramp_days_summary.csv   per-project statistics, plus a system row
    out/boat_ramp_days_by_year.csv   the project x year matrix behind the plots

A NOTE ON THE DURATION PANELS
    Each panel is an elevation duration curve for the season, all ten years
    pooled, with a horizontal line per ramp. Where the curve crosses a ramp
    line is the fraction of the season that ramp was usable, read straight off
    the x axis. That is the plot that shows WHY a project's ramp days are low -
    a pool that sits just under one ramp's sill all summer looks very different
    from one that swings across all of them, and an annual total hides both.

INPUT
    out/wil_elev_daily.csv           written by download_elevations.py
    data/BOAT_RAMP_ELEVATIONS.csv    Project, Ramp_Name, Min_Operable_Elev_ft

    The elevation file must be on the SAME DATUM as the pool record. USGS
    parameter 62614 is feet above NGVD 1929; ramp elevations quoted off a
    project drawing are often NAVD 1988, and the two differ by roughly 3.5 ft
    in this valley - enough to move a ramp day count by weeks. The script
    refuses to run on a mixed-datum table rather than guessing.
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ELEV_DAILY = os.path.join("..", "out", "wil_elev_daily.csv")
RAMPS_CSV = os.path.join("..", "data", "BOAT_RAMP_ELEVATIONS.csv")

BOX_PNG = os.path.join("..", "out", "boat_ramp_days_box.png")
DURATION_PNG = os.path.join("..", "out", "boat_ramp_duration.png")
SUMMARY_CSV = os.path.join("..", "out", "boat_ramp_days_summary.csv")
BY_YEAR_CSV = os.path.join("..", "out", "boat_ramp_days_by_year.csv")

# Recreation season, inclusive, as (month, day).
SEASON_START = (2, 1)
SEASON_END = (12, 15)

# The datum the pool record is on. Every ramp row must declare this same datum.
#
# The 2021 ramp memo does not state a datum anywhere. NGVD29 is inferred from
# its maximum conservation pool figures, which match the USACE NGVD29 values
# for all twelve projects (Detroit 1563.5, Lookout Point 926, Fern Ridge
# 373.5, and so on). That inference is worth confirming before the numbers go
# anywhere official: NAVD88 would shift every ramp about 3.5 ft.
EXPECTED_DATUM = "NGVD29"

# Four ramps carry an advisory elevation in the memo that differs from the
# figure in its left-hand column - an eroded ramp that "should close" higher, a
# marina manager's correction, a sill that needs dredging before it is usable.
# Run with SENSITIVITY = True to count ramp days against the advisory numbers
# instead, which is the pessimistic reading of the same memo.
SENSITIVITY = False
SENSITIVITY_ELEVATIONS = {
    ("LOOKOUT POINT LAKE NEAR LOWELL, OR", "Signal Point"): 825.0,
    ("FERN RIDGE LAKE NEAR ELMIRA, OR", "Fern Ridge Shores"): 370.0,
    ("COTTAGE GROVE LAKE NR COTTAGE GROVE, OR", "Wilson Creek"): 781.0,
}

DPI = 200

# Categorical slots 1-3 from the validated reference palette. Three is the
# all-pairs safe cap, which is why the duration figure is small multiples
# rather than thirteen curves on one axis.
C_SERIES = "#2a78d6"
C_ACCENT = "#eb6834"
C_INK = "#0b0b0b"
C_INK_SOFT = "#52514e"
C_GRID = "#d8d8d4"

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": C_GRID,
    "axes.labelcolor": C_INK_SOFT,
    "xtick.color": C_INK_SOFT,
    "ytick.color": C_INK_SOFT,
    "text.color": C_INK,
})


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def in_season(dates):
    """Boolean mask for 01 Feb - 15 Dec, handled per-year so leap years work."""
    month_day = list(zip(dates.dt.month, dates.dt.day))
    return pd.Series(
        [SEASON_START <= md <= SEASON_END for md in month_day],
        index=dates.index,
    )


def season_length(year):
    start = pd.Timestamp(year=year, month=SEASON_START[0], day=SEASON_START[1])
    end = pd.Timestamp(year=year, month=SEASON_END[0], day=SEASON_END[1])
    return (end - start).days + 1


def season_open_days(year, closed_months):
    """Days in the season that fall outside a ramp's closed months."""
    days = pd.date_range(
        pd.Timestamp(year=year, month=SEASON_START[0], day=SEASON_START[1]),
        pd.Timestamp(year=year, month=SEASON_END[0], day=SEASON_END[1]),
        freq="D",
    )
    return int((~days.month.isin(list(closed_months))).sum())


def load_ramps():
    if not os.path.isfile(RAMPS_CSV):
        sys.exit(
            "Missing %s.\n"
            "Copy BOAT_RAMP_ELEVATIONS_TEMPLATE.csv to that name and fill in "
            "one row per ramp from the project drawings." % RAMPS_CSV
        )

    ramps = pd.read_csv(RAMPS_CSV)
    required = {"Project", "Ramp_Name", "Min_Operable_Elev_ft", "Datum"}
    missing = required - set(ramps.columns)
    if missing:
        sys.exit("%s is missing column(s): %s"
                 % (RAMPS_CSV, ", ".join(sorted(missing))))

    ramps["Min_Operable_Elev_ft"] = pd.to_numeric(
        ramps["Min_Operable_Elev_ft"], errors="coerce"
    )
    blank = ramps["Min_Operable_Elev_ft"].isna()
    if blank.any():
        sys.exit(
            "%d ramp row(s) have no elevation, including %s.\n"
            "Every ramp needs one - a blank would silently count as always "
            "usable." % (int(blank.sum()), ramps.loc[blank, "Project"].iloc[0])
        )

    if SENSITIVITY:
        for (project, ramp_name), elevation in SENSITIVITY_ELEVATIONS.items():
            hit = ((ramps["Project"].str.strip() == project)
                   & (ramps["Ramp_Name"].str.strip() == ramp_name))
            if hit.any():
                ramps.loc[hit, "Min_Operable_Elev_ft"] = elevation
        print("SENSITIVITY on: using the memo's advisory elevations for "
              "%d ramp(s)\n" % len(SENSITIVITY_ELEVATIONS))

    # A ramp closed by policy for part of the season should not be counted
    # against those days in either the numerator or the denominator, so the
    # closed months come out of its potential too.
    if "Closed_Months" not in ramps.columns:
        ramps["Closed_Months"] = ""
    ramps["closed_set"] = ramps["Closed_Months"].apply(
        lambda v: set()
        if pd.isna(v) or not str(v).strip()
        else {int(x) for x in str(v).split(",") if str(x).strip()}
    )

    datums = set(ramps["Datum"].astype(str).str.strip().str.upper())
    unexpected = datums - {EXPECTED_DATUM.upper()}
    if unexpected:
        sys.exit(
            "Ramp elevations are on %s but the pool record is %s.\n"
            "Convert them first - the offset is about 3.5 ft in this valley, "
            "which is weeks of ramp days. Refusing to guess."
            % (", ".join(sorted(unexpected)), EXPECTED_DATUM)
        )

    return ramps


def compute(elev, ramps):
    """Ramp days per project per year, plus the potential for each."""
    rows = []
    for project, pool in elev.groupby("project"):
        project_ramps = ramps[ramps["Project"].str.strip().str.upper()
                              == project.strip().upper()]
        if project_ramps.empty:
            print("   *** no ramps listed for %s - skipped" % project)
            continue

        pool = pool.sort_values("date")

        for year, season in pool.groupby(pool["date"].dt.year):
            elevations = season["elev_ft"].to_numpy()
            months = season["date"].dt.month.to_numpy()
            open_days_in_season = season_length(int(year))

            ramp_days = 0
            potential = 0
            for _, ramp in project_ramps.iterrows():
                closed = ramp["closed_set"]
                open_mask = (
                    np.ones(len(months), dtype=bool)
                    if not closed
                    else ~np.isin(months, list(closed))
                )
                ramp_days += int(
                    ((elevations >= ramp["Min_Operable_Elev_ft"]) & open_mask).sum()
                )
                potential += (
                    open_days_in_season
                    if not closed
                    else int(season_open_days(int(year), closed))
                )

            rows.append(
                {
                    "project": project,
                    "year": int(year),
                    "ramps": len(project_ramps),
                    "days_observed": len(elevations),
                    "ramp_days": ramp_days,
                    "potential": potential,
                }
            )

    if not rows:
        sys.exit("No project in the elevation file matched the ramp table. "
                 "Check that the Project names agree.")

    by_year = pd.DataFrame(rows)
    by_year["pct_of_potential"] = (
        100.0 * by_year["ramp_days"] / by_year["potential"]
    )
    # A year missing days cannot be compared to a complete one; flag rather
    # than drop, so a short record is visible instead of quietly deflating.
    by_year["complete"] = (
        by_year["days_observed"] >= by_year["year"].map(season_length) - 5
    )
    return by_year


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=C_GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def add_header(figure, title, subtitle, header_inches=0.95):
    """
    Reserve the header in INCHES, not axes fractions.

    A fraction-positioned suptitle collides with its own subtitle as soon as
    the figure is short - which happens here the moment the panel grid has one
    row instead of four. Reserving a fixed physical strip keeps the two lines
    apart at any grid size.
    """
    height = figure.get_size_inches()[1]
    figure.subplots_adjust(top=1.0 - header_inches / height)
    figure.text(0.02, 1.0 - 0.30 / height, title,
                fontsize=15, fontweight="bold", ha="left", va="top",
                color=C_INK)
    figure.text(0.02, 1.0 - 0.62 / height, subtitle,
                fontsize=9, color=C_INK_SOFT, ha="left", va="top")


def box_figure(by_year, system):
    order = (
        by_year.groupby("project")["ramp_days"].median()
        .sort_values(ascending=False).index.tolist()
    )

    figure, (top, bottom) = plt.subplots(
        2, 1, figsize=(12.5, 9.0), gridspec_kw={"hspace": 0.28}
    )

    def draw(ax, column, title, ylabel, show_labels):
        data = [
            by_year.loc[by_year["project"] == name, column].to_numpy()
            for name in order
        ]
        parts = ax.boxplot(
            data, patch_artist=True, widths=0.5, showfliers=True,
            medianprops=dict(color="white", linewidth=1.8),
            flierprops=dict(marker="o", markersize=4,
                            markerfacecolor=C_ACCENT,
                            markeredgecolor="white", markeredgewidth=0.6),
            whiskerprops=dict(color=C_INK_SOFT, linewidth=1.1),
            capprops=dict(color=C_INK_SOFT, linewidth=1.1),
        )
        for patch in parts["boxes"]:
            patch.set_facecolor(C_SERIES)
            patch.set_alpha(0.88)
            patch.set_edgecolor("white")
            patch.set_linewidth(1.2)

        ax.set_xticks(range(1, len(order) + 1))
        if show_labels:
            ax.set_xticklabels([n.title() for n in order], rotation=35,
                               ha="right", fontsize=8.5)
        else:
            ax.set_xticklabels([])
        ax.set_ylabel(ylabel, fontsize=9.5)
        ax.set_title(title, fontsize=12, fontweight="bold", loc="left",
                     color=C_INK, pad=10)
        style(ax)

    # Both panels are magnitudes, so both keep a zero baseline: a truncated
    # axis would turn a few percent of difference between projects into a
    # dramatic-looking gap.
    draw(top, "ramp_days",
         "Boat ramp days per season, by project",
         "ramp days (ramps x days usable)", show_labels=False)
    top.set_ylim(0, by_year["ramp_days"].max() * 1.08)

    draw(bottom, "pct_of_potential",
         "The same seasons as a share of what the ramps could have delivered",
         "% of potential ramp days", show_labels=True)
    bottom.set_ylim(0, min(100.0, by_year["pct_of_potential"].max() * 1.12))

    years = "%d-%d" % (by_year["year"].min(), by_year["year"].max())
    add_header(
        figure,
        "Willamette Valley Project boat ramp availability, %s" % years,
        "Season 01 Feb - 15 Dec.  Each box is %d seasons.  System total: "
        "%s ramp days per season on the median, %.0f%% of potential."
        % (by_year["year"].nunique(),
           format(int(system["ramp_days"].median()), ","),
           system["pct_of_potential"].median()),
        header_inches=1.30,
    )
    figure.savefig(BOX_PNG, dpi=DPI, bbox_inches="tight",
                   facecolor="#fcfcfb")
    print("wrote %s" % BOX_PNG)


def duration_figure(elev, ramps):
    projects = sorted(elev["project"].unique())
    ncols = 4 if len(projects) > 6 else max(1, min(3, len(projects)))
    nrows = (len(projects) + ncols - 1) // ncols

    panel_w, panel_h = 4.0, 3.3
    header_in = 0.95
    figure, axes = plt.subplots(
        nrows, ncols,
        figsize=(panel_w * ncols, panel_h * nrows + header_in),
    )
    axes = np.atleast_1d(axes).ravel()

    for index, project in enumerate(projects):
        ax = axes[index]
        pool = elev.loc[elev["project"] == project, "elev_ft"].dropna()
        if pool.empty:
            ax.set_axis_off()
            continue

        # Duration curve: elevation equalled or exceeded x percent of the season.
        values = np.sort(pool.to_numpy())[::-1]
        exceedance = np.arange(1, len(values) + 1) / len(values) * 100.0
        ax.plot(exceedance, values, color=C_SERIES, linewidth=2.0, zorder=4)

        project_ramps = ramps[ramps["Project"].str.strip().str.upper()
                              == project.strip().upper()]
        for _, ramp in project_ramps.iterrows():
            sill = ramp["Min_Operable_Elev_ft"]
            ax.axhline(sill, color=C_INK_SOFT, linewidth=1.0,
                       linestyle=(0, (4, 3)), zorder=3)
            share = 100.0 * (pool >= sill).mean()
            # Haloed, because the duration curve runs straight through where
            # these labels sit and plain text on top of it is unreadable.
            ax.annotate(
                "%s  %.0f%%" % (str(ramp["Ramp_Name"])[:18], share),
                xy=(99, sill), xytext=(-2, 2), textcoords="offset points",
                ha="right", va="bottom", fontsize=7, color=C_INK_SOFT,
                zorder=6,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="#fcfcfb")],
            )

        ax.set_title(project.title(), fontsize=10, fontweight="bold",
                     loc="left", color=C_INK)
        ax.set_xlim(0, 100)
        ax.set_xlabel("% of season equalled or exceeded", fontsize=8)
        ax.set_ylabel("pool elevation (ft)", fontsize=8)
        ax.tick_params(labelsize=8)
        style(ax)

    spares = axes[len(projects):]
    for spare in spares:
        spare.set_axis_off()

    handles = [
        Line2D([], [], color=C_SERIES, lw=2, label="Pool elevation duration"),
        Line2D([], [], color=C_INK_SOFT, lw=1, linestyle=(0, (4, 3)),
               label="Ramp minimum operable elevation"),
    ]
    if len(spares):
        # Park the key in the first empty cell of the grid rather than letting
        # it float off the side of the figure.
        spares[0].legend(handles=handles, loc="center", frameon=False,
                         fontsize=9)
    else:
        figure.legend(handles=handles, loc="lower center", ncol=2,
                      frameon=False, fontsize=9,
                      bbox_to_anchor=(0.5, -0.01))

    figure.tight_layout(rect=[0, 0, 1, 1.0 - header_in / figure.get_size_inches()[1]])
    add_header(
        figure,
        "Pool elevation duration against ramp sills, 01 Feb - 15 Dec",
        "Dashed line: a ramp's minimum operable elevation, labelled with the "
        "share of the season the pool stayed at or above it.",
        header_inches=header_in,
    )
    figure.savefig(DURATION_PNG, dpi=DPI, bbox_inches="tight",
                   facecolor="#fcfcfb")
    print("wrote %s" % DURATION_PNG)


# ---------------------------------------------------------------------------
def main():
    if not os.path.isfile(ELEV_DAILY):
        sys.exit("Missing %s - run download_elevations.py first." % ELEV_DAILY)

    elev = pd.read_csv(ELEV_DAILY, parse_dates=["date"])
    ramps = load_ramps()

    elev = elev[in_season(elev["date"]).to_numpy()].copy()
    print("%d in-season daily elevations across %d pools\n"
          % (len(elev), elev["project"].nunique()))

    by_year = compute(elev, ramps)

    system = (
        by_year.groupby("year")
        .agg(ramps=("ramps", "sum"), ramp_days=("ramp_days", "sum"),
             potential=("potential", "sum"))
        .reset_index()
    )
    system["pct_of_potential"] = (
        100.0 * system["ramp_days"] / system["potential"]
    )
    system["project"] = "SYSTEM TOTAL"

    by_year.to_csv(BY_YEAR_CSV, index=False)
    print("wrote %s" % BY_YEAR_CSV)

    def stats(frame, label):
        return {
            "project": label,
            "ramps": int(frame["ramps"].iloc[0]),
            "seasons": int(frame["year"].nunique()),
            "mean_ramp_days": round(frame["ramp_days"].mean(), 1),
            "median_ramp_days": round(frame["ramp_days"].median(), 1),
            "min_ramp_days": int(frame["ramp_days"].min()),
            "max_ramp_days": int(frame["ramp_days"].max()),
            "median_pct_of_potential": round(frame["pct_of_potential"].median(), 1),
            "incomplete_seasons": int((~frame["complete"]).sum())
            if "complete" in frame else 0,
        }

    summary = pd.DataFrame(
        [stats(frame, name) for name, frame in by_year.groupby("project")]
        + [stats(system, "SYSTEM TOTAL")]
    ).sort_values("median_ramp_days", ascending=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    print("wrote %s\n" % SUMMARY_CSV)
    print(summary.to_string(index=False))

    box_figure(by_year, system)
    duration_figure(elev, ramps)


if __name__ == "__main__":
    main()
