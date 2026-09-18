# Ephemeral

Willamette Valley Project analysis scripts, plus the Git and pull-request
reference sheets.

## Layout

Each workflow owns a folder under `src/`, `data/` and `out/`. Inputs shared by
more than one workflow stay at the root of `data/`.

| Path | Holds |
|---|---|
| `src/boat_ramps/` | Pool elevation download and the boat ramp day analysis |
| `src/gauges/` | Outflow gauge resolution and the basin map |
| `src/DP_DL_28Aug2026.py` | Damages Prevented download (USGS + CWMS, writes DSS) |
| `data/` | `WIL_ELEV_DICT.csv` and `RuleCurves.csv` - shared by several workflows |
| `data/<workflow>/` | Inputs used by one workflow only |
| `out/<workflow>/` | Generated figures and tables |
| `cache/` | USGS and NLDI responses, reused between runs. Not in git |
| `ref/` | Reference material, including the Cowlitz map script the basin map derives from |

## Boat ramp days

```powershell
cd src\boat_ramps ; python download_elevations.py ; if ($?) { python boat_ramp_days.py }
```

`download_elevations.py` pulls ten years of daily pool elevation for the
thirteen projects. Every response is cached under `cache/usgs/`, so a rerun
costs nothing against the USGS request budget and a run interrupted by the rate
limit resumes where it stopped.

`boat_ramp_days.py` counts a ramp for each day the pool is at or above that
ramp's minimum operable elevation, so five usable ramps for a 30-day month is
150 ramp days. It reports that against **rule-curve potential** - the days the
rule curve says the pool should have been above the sill - rather than against
every day in the season, so a project is not charged for the months its own
drawdown schedule puts the pool below a ramp.

Dexter and Big Cliff are excluded: they are re-regulating pools with no rule
curve, and Dexter's ramps sit below its minimum pool.

Three figures come out of it: per-project boxes, per-project elevation duration
against each ramp sill, and `boat_ramp_system.png` - the system on one tile,
with headline numbers, the spread across seasons, and how many of the 35 ramps
were floating on a given day against how many the rule curve called for.

A project can read above 100%. That is not an error: the rule curve is a
schedule, and a pool held above it floats ramps the schedule never promised.
`surplus_days` and `deficit_days` in the summary say which way it went - Fern
Ridge's curve drops to 353 ft in November while its lowest ramp is at 364, so
a slow autumn drawdown shows up as surplus.

## Outflow gauges

```powershell
cd src\gauges ; python find_outflow_gauges.py ; if ($?) { python make_outflow_map.py }
```

## Requirements

`pandas`, `dataretrieval` (1.2.0 or newer), and for the map `geopandas`,
`contextily`, `matplotlib`, `shapely`.

The USGS key goes in `data/usgs_api_key.txt`, which is gitignored. On
dataretrieval 1.2.0 it only raises the request rate limit; downloads work
without one.
