# -*- coding: utf-8 -*-
"""
plot_rule_curves.py

Pool elevation against the rule curve, one interactive panel per reservoir, so
the curve behind the boat ramp numbers can be checked rather than trusted.

WHY THIS EXISTS SEPARATELY
    boat_ramp_days.py reduces ten years to one number per project per season.
    That is the answer, but it is unauditable: a project reading 108% and a
    project reading 48% look the same on the page, and neither says whether
    the rule curve was read correctly in the first place. This plots the two
    series that produce those numbers and gets out of the way.

WHAT TO LOOK FOR
    - the rule curve should sit inside the pool's real operating band. A curve
      offset by a few feet everywhere means a datum mismatch; a curve that is
      flat or wildly out of range means the wrong column got mapped.
    - blue fill above the curve is surplus - the pool floating ramps the
      schedule did not call for. That is what puts Fern Ridge over 100%.
    - orange fill below is deficit, and a deep one that lasts months is a
      drawdown worth knowing about rather than a data problem.
    - the dashed horizontal lines are ramp sills. Where the pool crosses one,
      a ramp opens or closes.

PLOTLY, NOT MATPLOTLIB
    The point is to interrogate the series - hover a date, read the two values
    and their difference, zoom into one autumn. The range slider on the bottom
    axis drives every panel at once, because the panels share an x axis.

OUTPUT
    out/boat_ramps/rule_curve_check.html   open it in a browser
"""

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ELEV_DAILY = os.path.join("out", "boat_ramps", "wil_elev_daily.csv")
RAMPS_CSV = os.path.join("data", "boat_ramps", "BOAT_RAMP_ELEVATIONS.csv")
RULE_CURVES_CSV = os.path.join("data", "RuleCurves.csv")
OUT_HTML = os.path.join("out", "boat_ramps", "rule_curve_check.html")

# Season shading. The boat ramp count only looks at 01 Feb - 15 Dec, so the
# months outside it are dimmed rather than hidden: a pool doing something odd
# in January still explains what February looks like.
SEASON_START = (2, 1)
SEASON_END = (12, 15)

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

# Same palette as the matplotlib figures, so the two read as one set. Above and
# below the curve is a polarity, so it gets a diverging pair with the curve
# itself as the neutral middle - not two arbitrary categorical hues.
C_POOL = "#2a78d6"      # observed elevation
C_SURPLUS = "#2a78d6"   # above the curve
C_DEFICIT = "#eb6834"   # below the curve
C_CURVE = "#0b0b0b"     # the rule curve - neutral ink, not a series colour
C_INK_SOFT = "#52514e"
C_GRID = "#e6e6e2"
C_SURFACE = "#fcfcfb"

PANEL_HEIGHT = 300


# ---------------------------------------------------------------------------
def repo_root():
    """Recognise the repository root by its contents, not by a fixed "..\"."""
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
    return path if os.path.isabs(path) else os.path.normpath(
        os.path.join(repo_root(), path))


def load_rule_curves():
    """The generic-year curve, indexed by (month, day)."""
    frame = pd.read_csv(resolve_path(RULE_CURVES_CSV), encoding="utf-8-sig")
    dates = pd.to_datetime(frame[frame.columns[0]], format="%d%b%Y")
    frame = frame.drop(columns=[frame.columns[0]])
    frame.index = pd.MultiIndex.from_arrays([dates.dt.month, dates.dt.day])
    return frame


def curve_for(curves, project, dates):
    """The rule curve aligned to a real calendar, 29 Feb borrowing 28 Feb."""
    column = RULE_CURVE_COLUMNS.get(project)
    if column is None or column not in curves.columns:
        return None
    keys = [(m, 28 if (m == 2 and d == 29) else d)
            for m, d in zip(dates.dt.month, dates.dt.day)]
    return curves[column].reindex(keys).to_numpy()


def in_season(dates):
    return np.array([SEASON_START <= (d.month, d.day) <= SEASON_END
                     for d in dates])


# ---------------------------------------------------------------------------
def build(elev, ramps, curves):
    projects = [p for p in sorted(elev["project"].unique())
                if p in RULE_CURVE_COLUMNS]
    if not projects:
        sys.exit("No project in the elevation file has a rule curve column.")

    figure = make_subplots(
        rows=len(projects), cols=1, shared_xaxes=True,
        vertical_spacing=0.012,
        subplot_titles=[p.title() for p in projects],
    )

    # One continuous daily calendar, so a missing day stays missing. Without
    # this the line is drawn straight across a gap and the band fills under it:
    # Lookout Point's 2023 outage rendered as a smooth nine-month drawdown that
    # never happened, which is exactly the kind of thing this plot exists to
    # catch rather than invent.
    span = pd.date_range(elev["date"].min(), elev["date"].max(), freq="D")

    for row, project in enumerate(projects, start=1):
        pool = (elev[elev["project"] == project]
                .sort_values("date")
                .set_index("date")
                .reindex(span))
        dates = pd.Series(span)
        actual = pool["elev_ft"].to_numpy().round(2)
        target = curve_for(curves, project, dates).round(2)
        missing = int(np.isnan(actual).sum())
        if missing:
            print("   %-42s %d day(s) with no observation - shown as breaks"
                  % (project, missing))

        first = row == 1

        # The rule curve is defined whether or not anyone measured the pool, so
        # it is drawn unbroken - during an outage it is the only thing on the
        # panel, which is the honest picture.
        figure.add_trace(
            go.Scattergl(x=dates, y=target, mode="lines", name="Rule curve",
                         line=dict(color=C_CURVE, width=1.4, dash="dot"),
                         legendgroup="curve", showlegend=first,
                         hovertemplate="rule curve %{y:.2f} ft<extra></extra>"),
            row=row, col=1)

        # Observations get drawn one contiguous run at a time. connectgaps is
        # not enough on its own: it breaks the LINE at a NaN but the fill
        # polygon still closes across the gap, which drew Lookout Point's
        # 282-day outage as a nine-month triangle. Splitting the series is the
        # only thing that stops the band spanning missing data.
        valid = ~np.isnan(actual)
        edges = np.flatnonzero(np.diff(valid.astype(int)))
        bounds = np.concatenate(([0], edges + 1, [len(valid)]))
        shown = first

        for lo, hi in zip(bounds[:-1], bounds[1:]):
            if not valid[lo] or hi - lo < 2:
                continue
            x = dates.iloc[lo:hi]
            a = actual[lo:hi]
            t = target[lo:hi]

            figure.add_trace(
                go.Scatter(x=x, y=t, mode="lines", line=dict(width=0),
                           showlegend=False, hoverinfo="skip"),
                row=row, col=1)
            figure.add_trace(
                go.Scatter(x=x, y=np.maximum(a, t), mode="lines",
                           line=dict(width=0), fill="tonexty",
                           fillcolor="rgba(42,120,214,0.25)",
                           name="Above the curve", legendgroup="surplus",
                           showlegend=shown, hoverinfo="skip"),
                row=row, col=1)
            figure.add_trace(
                go.Scatter(x=x, y=t, mode="lines", line=dict(width=0),
                           showlegend=False, hoverinfo="skip"),
                row=row, col=1)
            figure.add_trace(
                go.Scatter(x=x, y=np.minimum(a, t), mode="lines",
                           line=dict(width=0), fill="tonexty",
                           fillcolor="rgba(235,104,52,0.25)",
                           name="Below the curve", legendgroup="deficit",
                           showlegend=shown, hoverinfo="skip"),
                row=row, col=1)
            figure.add_trace(
                go.Scattergl(x=x, y=a, mode="lines", name="Pool elevation",
                             line=dict(color=C_POOL, width=1.6),
                             legendgroup="pool", showlegend=shown,
                             customdata=(a - t).round(2),
                             hovertemplate="%{x|%d %b %Y}<br>pool %{y:.2f} ft"
                                           "<br>%{customdata:+.2f} ft vs curve"
                                           "<extra></extra>"),
                row=row, col=1)
            shown = False

        sills = ramps[ramps["Project"].str.strip().str.upper()
                      == project.strip().upper()]
        # Ramps sharing an elevation share one line and one label - Cougar's
        # Slide Creek and Echo Park are both at 1635 and printed on top of
        # each other otherwise.
        grouped = (sills.groupby("Min_Operable_Elev_ft")["Ramp_Name"]
                   .apply(lambda names: " / ".join(sorted(names)))
                   .sort_index(ascending=False))
        # Four label slots, cycled by height order, so neighbours separate
        # horizontally even when they are a foot apart.
        slots = ["top left", "top right", "bottom left", "bottom right"]
        for index, (sill, names) in enumerate(grouped.items()):
            figure.add_hline(
                y=sill, row=row, col=1,
                line=dict(color=C_INK_SOFT, width=0.8, dash="dash"),
                annotation_text="%s  %.0f" % (names, sill),
                annotation_position=slots[index % len(slots)],
                annotation_font=dict(size=9, color=C_INK_SOFT),
            )

        season = in_season(dates)
        figure.update_yaxes(
            title_text="ft", row=row, col=1, gridcolor=C_GRID,
            title_font=dict(size=10), tickfont=dict(size=9),
            # Frame on the season, since that is what the ramp count uses, but
            # leave headroom so an out-of-season excursion is still visible.
            range=[min(np.nanmin(actual[season]),
                       np.nanmin(target[season])) - 3,
                   max(np.nanmax(actual[season]),
                       np.nanmax(target[season])) + 3],
        )
        figure.update_xaxes(gridcolor=C_GRID, row=row, col=1,
                            tickfont=dict(size=9))

    figure.update_xaxes(rangeslider=dict(visible=True, thickness=0.02),
                        row=len(projects), col=1)

    figure.update_layout(
        height=PANEL_HEIGHT * len(projects) + 150,
        title=dict(
            text="<b>Pool elevation against the rule curve</b><br>"
                 "<span style='font-size:13px;color:%s'>"
                 "Blue above the dotted curve is surplus - ramp days the "
                 "schedule did not call for. Orange below is deficit. "
                 "Dashed horizontals are ramp sills."
                 "</span>" % C_INK_SOFT,
            x=0.012, xanchor="left", font=dict(size=20),
        ),
        hovermode="x unified",
        plot_bgcolor=C_SURFACE, paper_bgcolor=C_SURFACE,
        font=dict(family="DejaVu Sans, Segoe UI, sans-serif", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.006,
                    xanchor="right", x=1, font=dict(size=11)),
        margin=dict(l=70, r=40, t=140, b=60),
    )
    for note in figure.layout.annotations:
        if note.text in [p.title() for p in projects]:
            note.update(x=0.0, xanchor="left", font=dict(size=13))

    return figure


def main():
    elev_path = resolve_path(ELEV_DAILY)
    if not os.path.isfile(elev_path):
        sys.exit("Missing %s - run download_elevations.py first." % elev_path)

    elev = pd.read_csv(elev_path, parse_dates=["date"])
    ramps = pd.read_csv(resolve_path(RAMPS_CSV))
    curves = load_rule_curves()

    figure = build(elev, ramps, curves)

    out = resolve_path(OUT_HTML)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # The plotly bundle comes from the CDN so the file stays a few MB rather
    # than carrying 3 MB of library with it. It needs a network connection the
    # first time a browser opens it; swap to include_plotlyjs=True for a file
    # that works offline.
    figure.write_html(out, include_plotlyjs="cdn")
    print("wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    print("%d reservoirs plotted" % sum(
        1 for p in elev["project"].unique() if p in RULE_CURVE_COLUMNS))


if __name__ == "__main__":
    main()
