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
ELEV_DAILY = os.path.join("out", "boat_ramps", "wil_elev_daily.csv")
RAMPS_CSV = os.path.join("data", "boat_ramps", "BOAT_RAMP_ELEVATIONS.csv")
RULE_CURVES_CSV = os.path.join("data", "RuleCurves.csv")

BOX_PNG = os.path.join("out", "boat_ramps", "boat_ramp_days_box.png")
DURATION_PNG = os.path.join("out", "boat_ramps", "boat_ramp_duration.png")
SYSTEM_PNG = os.path.join("out", "boat_ramps", "boat_ramp_system.png")
SUMMARY_CSV = os.path.join("out", "boat_ramps", "boat_ramp_days_summary.csv")
BY_YEAR_CSV = os.path.join("out", "boat_ramps", "boat_ramp_days_by_year.csv")

# Pools with no rule curve and no ramps worth counting. Dexter and Big Cliff
# are re-regulating pools held in a narrow band; Dexter's two ramps sit below
# its minimum pool, so it scored a meaningless 100%.
EXCLUDE_PROJECTS = {
    "DEXTER LAKE AT DEXTER, OR",
    "BIG CLIFF LAKE NEAR NIAGARA, OR",
}

# RuleCurves.csv names projects by their short name; the elevation record uses
# the full gauge name. This maps one to the other.
RULE_CURVE_COLUMNS = {
    "GREEN PETER LAKE NEAR FOSTER, OR": "GREEN PETER",
    "FOSTER LAKE AT FOSTER, OR": "FOSTER",
    "DETROIT LAKE NEAR DETROIT, OR": "DETROIT",
    "LOOKOUT POINT LAKE NEAR LOWELL, OR": "LOOKOUT POINT",
    "HILLS CREEK LAKE NEAR OAKRIDGE, OR": "HILLS CREEK",
    "FALL CREEK LAKE NEAR LOWELL, OR": "FALL CREEK",
    "COUGAR LAKE NEAR RAINBOW, OR": "COUGAR",
    "BLUE RIVER LAKE NEAR BLUE RIVER, OR": "BLUE RIVER",
    "FERN RIDGE LAKE NEAR ELMIRA, OR": "FERN RIDGE",
    "DORENA LAKE NEAR COTTAGE GROVE, OR": "DORENA",
    "COTTAGE GROVE LAKE NR COTTAGE GROVE, OR": "COTTAGE GROVE",
}

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


def repo_root():
    """Recognise the repository root by its contents, not by a fixed ".."."""
    here = os.path.dirname(os.path.abspath(__file__))
    while True:
        if all(os.path.isdir(os.path.join(here, d)) for d in ("data", "src")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            raise SystemExit("Cannot find the repository root above %s"
                             % os.path.dirname(os.path.abspath(__file__)))
        here = parent


def resolve_path(path):
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(repo_root(), path))


def load_rule_curves():
    """
    The generic-year rule curve for each pool, indexed by (month, day).

    The file carries one year of dates stamped 1900, so the year is dropped and
    each value is looked up by calendar day. 29 February is not in it; a leap
    day borrows 28 February, which is what the curve is doing at that point in
    the refill anyway.
    """
    frame = pd.read_csv(resolve_path(RULE_CURVES_CSV), encoding="utf-8-sig")
    dates = pd.to_datetime(frame[frame.columns[0]], format="%d%b%Y")
    frame = frame.drop(columns=[frame.columns[0]])
    frame.index = pd.MultiIndex.from_arrays(
        [dates.dt.month, dates.dt.day], names=["month", "day"]
    )
    return frame


def rule_curve_for(curves, project, months, days):
    """The rule curve elevation for each day of one pool's season."""
    column = RULE_CURVE_COLUMNS.get(project)
    if column is None or column not in curves.columns:
        return None
    series = curves[column]
    keys = [(m, 28 if (m == 2 and d == 29) else d) for m, d in zip(months, days)]
    return series.reindex(keys).to_numpy()


def season_open_days(year, closed_months):
    """Days in the season that fall outside a ramp's closed months."""
    days = pd.date_range(
        pd.Timestamp(year=year, month=SEASON_START[0], day=SEASON_START[1]),
        pd.Timestamp(year=year, month=SEASON_END[0], day=SEASON_END[1]),
        freq="D",
    )
    return int((~days.month.isin(list(closed_months))).sum())


def load_ramps():
    if not os.path.isfile(resolve_path(RAMPS_CSV)):
        sys.exit(
            "Missing %s.\n"
            "Copy BOAT_RAMP_ELEVATIONS_TEMPLATE.csv to that name and fill in "
            "one row per ramp from the project drawings." % RAMPS_CSV
        )

    ramps = pd.read_csv(resolve_path(RAMPS_CSV))
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


def compute(elev, ramps, curves):
    """
    Ramp days per project per year, against a rule-curve potential.

    The denominator is the question this answers. Counting every season day as
    a day the ramp could have been open charges a project for the months its
    own rule curve puts the pool below the sill - Detroit's Ramp D at 1556 ft
    is not meant to be in the water in February, and scoring it as a miss says
    more about the drawdown schedule than about how the pool was run.

    So potential counts only the days the rule curve is at or above the ramp,
    and the ratio reads as: of the days this ramp was SUPPOSED to be usable,
    how many was it? That can exceed 100% when the pool is held above the rule
    curve, which is real and is left uncapped.
    """
    rows = []
    for project, pool in elev.groupby("project"):
        if project in EXCLUDE_PROJECTS:
            continue

        project_ramps = ramps[ramps["Project"].str.strip().str.upper()
                              == project.strip().upper()]
        if project_ramps.empty:
            print("   *** no ramps listed for %s - skipped" % project)
            continue

        pool = pool.sort_values("date")

        for year, season in pool.groupby(pool["date"].dt.year):
            elevations = season["elev_ft"].to_numpy()
            months = season["date"].dt.month.to_numpy()
            days = season["date"].dt.day.to_numpy()

            target = rule_curve_for(curves, project, months, days)
            if target is None:
                print("   *** no rule curve for %s - skipped" % project)
                break

            ramp_days = 0
            potential = 0
            surplus = 0
            deficit = 0
            for _, ramp in project_ramps.iterrows():
                closed = ramp["closed_set"]
                open_mask = (
                    np.ones(len(months), dtype=bool)
                    if not closed
                    else ~np.isin(months, list(closed))
                )
                sill = ramp["Min_Operable_Elev_ft"]
                actual_ok = (elevations >= sill) & open_mask
                curve_ok = (target >= sill) & open_mask
                ramp_days += int(actual_ok.sum())
                # The rule curve says when it SHOULD have been usable.
                potential += int(curve_ok.sum())
                # Where the two disagree is the whole story behind a number
                # above or below 100%: surplus is a day the pool floated a ramp
                # the curve had no intention of floating, deficit the reverse.
                surplus += int((actual_ok & ~curve_ok).sum())
                deficit += int((curve_ok & ~actual_ok).sum())

            rows.append(
                {
                    "project": project,
                    "year": int(year),
                    "ramps": len(project_ramps),
                    "days_observed": len(elevations),
                    "ramp_days": ramp_days,
                    "potential": potential,
                    "surplus_days": surplus,
                    "deficit_days": deficit,
                }
            )

    if not rows:
        sys.exit("No project in the elevation file matched the ramp table. "
                 "Check that the Project names agree.")

    by_year = pd.DataFrame(rows)
    # A pool whose rule curve never reaches its lowest ramp has no potential at
    # all; reporting 0/0 as 0% would read as a failure rather than as a ramp
    # the schedule never intends to float.
    by_year["pct_of_potential"] = np.where(
        by_year["potential"] > 0,
        100.0 * by_year["ramp_days"] / by_year["potential"].replace(0, np.nan),
        np.nan,
    )
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
         "The same seasons against what the rule curve says they should have been",
         "% of rule-curve potential", show_labels=True)
    # Uncapped: a pool held above its rule curve genuinely delivers more ramp
    # days than the schedule calls for, and clipping that at 100 would hide it.
    top_pct = float(np.nanmax(by_year["pct_of_potential"]))
    bottom.set_ylim(0, max(105.0, top_pct * 1.08))
    bottom.axhline(100, color=C_INK_SOFT, linewidth=1.0,
                   linestyle=(0, (4, 3)), zorder=2)
    bottom.annotate("what the rule curve calls for",
                    xy=(len(order) + 0.5, 100), xytext=(-3, 4),
                    textcoords="offset points", ha="right", fontsize=7.5,
                    color=C_INK_SOFT,
                    path_effects=[pe.withStroke(linewidth=2.4,
                                                foreground="#fcfcfb")])

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
    os.makedirs(os.path.dirname(resolve_path(BOX_PNG)), exist_ok=True)
    figure.savefig(resolve_path(BOX_PNG), dpi=DPI, bbox_inches="tight",
                   facecolor="#fcfcfb")
    print("wrote %s" % BOX_PNG)



def system_figure(by_year, system, elev, ramps, curves):
    """
    The system as one page: headline numbers, the spread across seasons, and
    how many of the 35 ramps were actually floating on a given day.

    The per-project figures cannot carry this. A system total is an order of
    magnitude larger than any one project, so putting it on the same axis
    either flattens the projects or needs a second scale - and the duration
    curve that matters here counts RAMPS ACROSS THE SYSTEM, which is a
    different quantity from any one pool's elevation.
    """
    figure = plt.figure(figsize=(13.0, 6.4))
    grid = figure.add_gridspec(
        2, 3, height_ratios=[0.22, 1.0], hspace=0.18, wspace=0.26
    )

    # --- headline tiles ----------------------------------------------------
    median_days = int(system["ramp_days"].median())
    median_pct = float(system["pct_of_potential"].median())
    best = system.loc[system["ramp_days"].idxmax()]
    worst = system.loc[system["ramp_days"].idxmin()]

    tiles = [
        ("%s" % format(median_days, ","), "ramp days in a median season",
         "%d ramps across %d projects" % (int(system["ramps"].iloc[0]),
                                          by_year["project"].nunique())),
        ("%.0f%%" % median_pct, "of what the rule curve calls for",
         "100% would be exactly on schedule"),
        ("%s / %s" % (format(int(worst["ramp_days"]), ","),
                      format(int(best["ramp_days"]), ",")),
         "worst and best season",
         "%d and %d" % (int(worst["year"]), int(best["year"]))),
    ]
    for column, (value, label, note) in enumerate(tiles):
        ax = figure.add_subplot(grid[0, column])
        ax.set_axis_off()
        ax.text(0, 0.80, value, fontsize=26, fontweight="bold",
                color=C_SERIES, ha="left", va="center")
        ax.text(0, 0.40, label, fontsize=10.5, color=C_INK, ha="left",
                va="center")
        ax.text(0, 0.16, note, fontsize=8.5, color=C_INK_SOFT, ha="left",
                va="center")

    # --- spread across seasons --------------------------------------------
    ax = figure.add_subplot(grid[1, 0])
    parts = ax.boxplot(
        [system["ramp_days"].to_numpy()], patch_artist=True, widths=0.45,
        medianprops=dict(color="white", linewidth=1.8),
        flierprops=dict(marker="o", markersize=4, markerfacecolor=C_ACCENT,
                        markeredgecolor="white", markeredgewidth=0.6),
        whiskerprops=dict(color=C_INK_SOFT, linewidth=1.1),
        capprops=dict(color=C_INK_SOFT, linewidth=1.1),
    )
    for patch in parts["boxes"]:
        patch.set_facecolor(C_SERIES)
        patch.set_alpha(0.88)
        patch.set_edgecolor("white")
        patch.set_linewidth(1.2)
    # Each season as a dot beside the box: ten points is few enough that the
    # box alone hides more than it summarises.
    jitter = np.random.default_rng(0).normal(1.42, 0.035, len(system))
    ax.plot(jitter, system["ramp_days"], "o", markersize=4.5,
            color=C_INK_SOFT, alpha=0.65, markeredgecolor="white",
            markeredgewidth=0.5)
    ax.set_xlim(0.55, 1.75)
    ax.set_xticks([])
    ax.set_ylim(0, system["ramp_days"].max() * 1.1)
    ax.set_ylabel("system ramp days per season", fontsize=9.5)
    ax.set_title("Spread across %d seasons" % len(system), fontsize=11,
                 fontweight="bold", loc="left", color=C_INK, pad=8)
    style(ax)

    # --- how many ramps were floating, day by day --------------------------
    ax = figure.add_subplot(grid[1, 1:])
    actual, expected = system_ramp_counts(elev, ramps, curves)

    for series, colour, label in (
        (actual, C_SERIES, "Ramps actually usable"),
        (expected, C_ACCENT, "Ramps the rule curve calls for"),
    ):
        values = np.sort(series)[::-1]
        exceedance = np.arange(1, len(values) + 1) / len(values) * 100.0
        ax.plot(exceedance, values, color=colour, linewidth=2.0, zorder=4,
                label=label)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(ramps) + 1)
    ax.set_xlabel("% of season equalled or exceeded", fontsize=9)
    ax.set_ylabel("ramps usable system-wide", fontsize=9.5)
    ax.set_title("Ramps floating on a given day, all seasons pooled",
                 fontsize=11, fontweight="bold", loc="left", color=C_INK,
                 pad=8)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    style(ax)

    # Where the blue curve sits above the orange one, the system floated more
    # ramps than the schedule called for - which is what a number over 100%
    # means, said as a picture.
    gap = float(np.mean(actual) - np.mean(expected))
    wording = (
        "%.1f more ramps than the curve calls for" % gap if gap >= 0.05
        else "%.1f fewer ramps than the curve calls for" % abs(gap)
        if gap <= -0.05
        else "the same number of ramps the curve calls for"
    )
    ax.annotate(
        "On an average day the system floated %s." % wording,
        xy=(0.5, 0.045), xycoords="axes fraction", ha="center", fontsize=8.5,
        color=C_INK_SOFT,
    )

    years = "%d-%d" % (by_year["year"].min(), by_year["year"].max())
    add_header(
        figure,
        "Willamette Valley Project boat ramps - system summary, %s" % years,
        "Season 01 Feb - 15 Dec.  Dexter and Big Cliff excluded: "
        "re-regulating pools with no rule curve.",
        header_inches=1.05,
    )
    figure.savefig(resolve_path(SYSTEM_PNG), dpi=DPI, bbox_inches="tight",
                   facecolor="#fcfcfb")
    print("wrote %s" % SYSTEM_PNG)


def system_ramp_counts(elev, ramps, curves):
    """
    Per calendar day: ramps usable system-wide, actual and per the rule curve.

    Counted across every pool and season at once, so a day appears once per
    season rather than being averaged into a single generic year - the spread
    between wet and dry years is the point.
    """
    actual_by_day = {}
    expected_by_day = {}

    for project, pool in elev.groupby("project"):
        project_ramps = ramps[ramps["Project"].str.strip().str.upper()
                              == project.strip().upper()]
        if project_ramps.empty:
            continue

        pool = pool.sort_values("date")
        months = pool["date"].dt.month.to_numpy()
        days = pool["date"].dt.day.to_numpy()
        target = rule_curve_for(curves, project, months, days)
        if target is None:
            continue

        elevations = pool["elev_ft"].to_numpy()
        keys = pool["date"].to_numpy()

        for _, ramp in project_ramps.iterrows():
            closed = ramp["closed_set"]
            open_mask = (
                np.ones(len(months), dtype=bool)
                if not closed
                else ~np.isin(months, list(closed))
            )
            sill = ramp["Min_Operable_Elev_ft"]
            for key, ok, want in zip(keys,
                                     (elevations >= sill) & open_mask,
                                     (target >= sill) & open_mask):
                actual_by_day[key] = actual_by_day.get(key, 0) + int(ok)
                expected_by_day[key] = expected_by_day.get(key, 0) + int(want)

    shared = sorted(set(actual_by_day) & set(expected_by_day))
    return (
        np.array([actual_by_day[k] for k in shared]),
        np.array([expected_by_day[k] for k in shared]),
    )


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
    figure.savefig(resolve_path(DURATION_PNG), dpi=DPI, bbox_inches="tight",
                   facecolor="#fcfcfb")
    print("wrote %s" % DURATION_PNG)


# ---------------------------------------------------------------------------
def main():
    if not os.path.isfile(resolve_path(ELEV_DAILY)):
        sys.exit("Missing %s - run download_elevations.py first."
                 % resolve_path(ELEV_DAILY))

    elev = pd.read_csv(resolve_path(ELEV_DAILY), parse_dates=["date"])
    ramps = load_ramps()
    curves = load_rule_curves()

    elev = elev[in_season(elev["date"]).to_numpy()].copy()
    elev = elev[~elev["project"].isin(EXCLUDE_PROJECTS)].copy()
    print("%d in-season daily elevations across %d pools "
          "(%d excluded: no rule curve)\n"
          % (len(elev), elev["project"].nunique(), len(EXCLUDE_PROJECTS)))

    by_year = compute(elev, ramps, curves)

    system = (
        by_year.groupby("year")
        .agg(ramps=("ramps", "sum"), ramp_days=("ramp_days", "sum"),
             potential=("potential", "sum"),
             surplus_days=("surplus_days", "sum"),
             deficit_days=("deficit_days", "sum"))
        .reset_index()
    )
    system["pct_of_potential"] = (
        100.0 * system["ramp_days"] / system["potential"]
    )
    system["project"] = "SYSTEM TOTAL"

    os.makedirs(os.path.dirname(resolve_path(BY_YEAR_CSV)), exist_ok=True)
    by_year.to_csv(resolve_path(BY_YEAR_CSV), index=False)
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
            "mean_surplus_days": round(frame["surplus_days"].mean(), 1),
            "mean_deficit_days": round(frame["deficit_days"].mean(), 1),
            "incomplete_seasons": int((~frame["complete"]).sum())
            if "complete" in frame else 0,
        }

    summary = pd.DataFrame(
        [stats(frame, name) for name, frame in by_year.groupby("project")]
        + [stats(system, "SYSTEM TOTAL")]
    ).sort_values("median_ramp_days", ascending=False)
    summary.to_csv(resolve_path(SUMMARY_CSV), index=False)
    print("wrote %s\n" % SUMMARY_CSV)
    print(summary.to_string(index=False))

    box_figure(by_year, system)
    duration_figure(elev, ramps)
    system_figure(by_year, system, elev, ramps, curves)


if __name__ == "__main__":
    main()
