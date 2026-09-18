# -*- coding: utf-8 -*-
"""
find_outflow_gauges.py

Resolve the closest downstream USGS streamflow gauge below each Willamette
Valley Project dam in WIL_ELEV_DICT.csv, and write a download dictionary for
the outflow records in the same schema the DP download script already reads.

WHY THIS EXISTS
    The reservoir elevation dictionary keys each project by its forebay gauge.
    The outflow record has to come from a separate station below the dam, and
    picking the wrong one is easy: several projects have a near-identically
    named gauge just ABOVE the lake (14162000 Blue River NR Blue River vs
    14162200 Blue River AT Blue River; 14159200 above Cougar vs 14159500
    below it). This resolves them from the river network rather than by name.

HOW IT DECIDES
    For each forebay site, NLDI is navigated DOWNSTREAM MAIN (DM) and every
    NWIS site it returns is scored: the closest one that actually publishes
    discharge (parameter 00060) for the requested window wins. The candidate
    in WIL_OUTFLOW_CANDIDATES.csv is then compared against that answer, and
    any disagreement is printed loudly rather than silently resolved.

    A dam whose release is re-regulated a short distance downstream (Detroit
    -> Big Cliff, Lookout Point -> Dexter) has no gauge of its own in between.
    Those are listed in SHARED_TAILWATER and are expected to resolve to the
    re-regulating project's gauge; that is a real limitation of using USGS for
    outflow, not a bug. Daily volumes are right, sub-daily shape is not.

OUTPUT
    data/WIL_OUTFLOW_REVIEW.csv   every downstream candidate considered, with
                                  distance, drainage area and period of record
    data/WIL_OUTFLOW_DICT.csv     ResSimPath / Download_Key / Source, ready to
                                  concatenate with WIL_ELEV_DICT.csv

NOTE ON APIS
    Site metadata and the period-of-record catalog come from the legacy
    waterservices.usgs.gov site service, which USGS is decommissioning in
    Q1 2027. It is used here because the modernized replacement requires an
    API key and this script is meant to run without one. The DOWNLOAD script
    already uses the modern api.waterdata.usgs.gov path; only this one-time
    resolution step is on the legacy service.
"""

import os
import json
import time

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ELEV_DICT_PATH = os.path.join("data", "WIL_ELEV_DICT.csv")
CANDIDATES_PATH = os.path.join("data", "gauges", "WIL_OUTFLOW_CANDIDATES.csv")
REVIEW_OUT = os.path.join("out", "gauges", "WIL_OUTFLOW_REVIEW.csv")
DICT_OUT = os.path.join("data", "gauges", "WIL_OUTFLOW_DICT.csv")
CACHE_DIR = os.path.join("cache", "nldi")

# The window the outflow record has to cover. A candidate that does not span
# this is reported but not silently accepted.
WINDOW_START = "2005-10-01"
WINDOW_END = "2025-09-30"

# How far downstream to look for a gauge, in km. Big enough to reach past a
# re-regulating dam, small enough not to run to the next project.
SEARCH_KM = 40

NLDI_BASES = [
    "https://api.water.usgs.gov/nldi/linked-data",
    "https://labs.waterdata.usgs.gov/api/nldi/linked-data",
]
NWIS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"
HTTP_TIMEOUT = 90
DISCHARGE_PARM = "00060"

# Projects whose release is re-regulated before the first gauge. Keyed by the
# forebay site, valued with the project that owns the gauge they share.
SHARED_TAILWATER = {
    "14180500": "Detroit is re-regulated by Big Cliff",
    "14149000": "Lookout Point is re-regulated by Dexter",
}


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------
def repo_root():
    """Recognise the repository root by its contents, not by a fixed "..".

    These scripts live in src/<workflow>/, so counting directory levels breaks
    the moment one moves.
    """
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


def ensure_cache_dir():
    directory = resolve_path(CACHE_DIR)
    if not os.path.isdir(directory):
        os.makedirs(directory)


def http_get(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        print("      fetch failed: %s" % exc)
        return None


def nldi_get(path, params=None):
    """Try each NLDI host in turn; return the first response with features."""
    for base in NLDI_BASES:
        url = "%s/%s" % (base, path.lstrip("/"))
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


def downstream_sites(site):
    """NWIS sites on the downstream mainstem below `site`, nearest first."""
    cache = cache_path("dm_%s.json" % site)
    if os.path.isfile(cache):
        with open(cache, "r") as handle:
            data = json.load(handle)
    else:
        data = nldi_get(
            "nwissite/USGS-%s/navigation/DM/nwissite" % site,
            {"f": "json", "distance": SEARCH_KM},
        )
        if data:
            ensure_cache_dir()
            with open(cache, "w") as handle:
                json.dump(data, handle)
    if not data:
        return []

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        identifier = str(props.get("identifier", ""))
        number = identifier.split("-", 1)[1] if "-" in identifier else identifier
        if not number or number == site:
            continue
        rows.append(
            {
                "site_no": number,
                "station_nm": props.get("name", ""),
                # NLDI reports path distance from the navigation origin in km.
                "km_downstream": _as_float(props.get("distance")),
            }
        )
    rows.sort(key=lambda r: (r["km_downstream"] is None, r["km_downstream"]))
    return rows


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def site_catalog(numbers):
    """
    Expanded site metadata plus the period-of-record catalog, as one frame.

    seriesCatalogOutput lists one row per parameter per site, so a site that
    publishes discharge appears with parm_cd 00060 and its begin/end dates.
    """
    if not numbers:
        return pd.DataFrame()

    text = http_get(
        NWIS_SITE_URL,
        {
            "format": "rdb",
            "sites": ",".join(sorted(set(numbers))),
            "siteOutput": "expanded",
            "seriesCatalogOutput": "true",
            "outputDataTypeCd": "dv,iv",
        },
    )
    if not text:
        return pd.DataFrame()

    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return pd.DataFrame()

    header = lines[0].split("\t")
    records = []
    for line in lines[2:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        records.append(dict(zip(header, parts)))

    frame = pd.DataFrame(records)
    for column in ("dec_lat_va", "dec_long_va", "drain_area_va"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def discharge_record(catalog, site):
    """(begin, end, data_type) for the longest 00060 series at `site`."""
    if catalog.empty or "parm_cd" not in catalog.columns:
        return None, None, None
    rows = catalog[
        (catalog["site_no"].astype(str) == str(site))
        & (catalog["parm_cd"].astype(str).str.strip() == DISCHARGE_PARM)
    ]
    if rows.empty:
        return None, None, None
    rows = rows.copy()
    rows["begin"] = pd.to_datetime(rows.get("begin_date"), errors="coerce")
    rows["end"] = pd.to_datetime(rows.get("end_date"), errors="coerce")
    rows = rows.dropna(subset=["begin", "end"])
    if rows.empty:
        return None, None, None
    best = rows.loc[(rows["end"] - rows["begin"]).idxmax()]
    return best["begin"], best["end"], str(best.get("data_type_cd", "")).strip()


def covers_window(begin, end):
    if begin is None or end is None:
        return False
    return begin <= pd.Timestamp(WINDOW_START) and end >= pd.Timestamp(WINDOW_END)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
def resolve():
    elev = pd.read_csv(resolve_path(ELEV_DICT_PATH), dtype={"Download_Key": str})
    candidates = pd.read_csv(
        resolve_path(CANDIDATES_PATH), dtype={"Forebay_Site": str, "Outflow_Site": str}
    )
    expected = dict(
        zip(candidates["Forebay_Site"], candidates["Outflow_Site"])
    )
    names = dict(zip(candidates["Forebay_Site"], candidates["Reservoir"]))

    review_rows = []
    chosen = {}

    for forebay in elev["Download_Key"].astype(str):
        label = names.get(forebay, forebay)
        print("\n%s (forebay %s)" % (label, forebay))

        found = downstream_sites(forebay)
        if not found:
            print("   NLDI returned nothing downstream")
        time.sleep(0.5)

        catalog = site_catalog([r["site_no"] for r in found] + [expected.get(forebay, "")])

        pick = None
        for row in found:
            begin, end, data_type = discharge_record(catalog, row["site_no"])
            spans = covers_window(begin, end)
            has_q = begin is not None
            review_rows.append(
                {
                    "Reservoir": label,
                    "Forebay_Site": forebay,
                    "Candidate_Site": row["site_no"],
                    "Candidate_Name": row["station_nm"],
                    "Km_Downstream": row["km_downstream"],
                    "Has_Discharge": has_q,
                    "Q_Begin": None if begin is None else begin.date(),
                    "Q_End": None if end is None else end.date(),
                    "Data_Type": data_type,
                    "Covers_Window": spans,
                    "Matches_Candidate": row["site_no"] == expected.get(forebay),
                }
            )
            if pick is None and has_q:
                pick = row["site_no"]

        proposed = expected.get(forebay)
        if pick is None:
            print("   no downstream gauge publishes 00060 within %d km" % SEARCH_KM)
            pick = proposed
        elif proposed and pick != proposed:
            print("   *** DISAGREEMENT: network says %s, candidate list says %s"
                  % (pick, proposed))
            print("       review data/WIL_OUTFLOW_REVIEW.csv before trusting either")
        else:
            print("   %s confirmed" % pick)

        if forebay in SHARED_TAILWATER:
            print("   note: %s - sub-daily shape will not match the release"
                  % SHARED_TAILWATER[forebay])

        if pick:
            begin, end, _ = discharge_record(catalog, pick)
            if not covers_window(begin, end):
                print("   *** %s does NOT span %s to %s (record %s to %s)"
                      % (pick, WINDOW_START, WINDOW_END,
                         None if begin is None else begin.date(),
                         None if end is None else end.date()))
            chosen[forebay] = (pick, catalog)

    return chosen, pd.DataFrame(review_rows)


def build_dict(chosen):
    """ResSim-style download dictionary rows for the resolved outflow gauges."""
    rows = []
    for forebay, (site, catalog) in chosen.items():
        name = ""
        if not catalog.empty and "station_nm" in catalog.columns:
            match = catalog[catalog["site_no"].astype(str) == str(site)]
            if not match.empty:
                name = str(match.iloc[0]["station_nm"]).strip()
        rows.append(
            {
                # Matches the shape of the ELEV dictionary: A-part is the
                # station name, B-part the site number, C-part the parameter.
                # Check these against your ResSim alternative before use.
                "ResSimPath": "/%s/%s/FLOW//1HOUR/USGS/" % (name.upper(), site),
                "Download_Key": site,
                "Source": "USGS",
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["Download_Key"])


if __name__ == "__main__":
    chosen, review = resolve()

    os.makedirs(os.path.dirname(resolve_path(REVIEW_OUT)), exist_ok=True)
    review.to_csv(resolve_path(REVIEW_OUT), index=False)
    print("\nwrote %s (%d candidate rows)" % (REVIEW_OUT, len(review)))

    dictionary = build_dict(chosen)
    dictionary.to_csv(resolve_path(DICT_OUT), index=False)
    print("wrote %s (%d outflow records)" % (DICT_OUT, len(dictionary)))
    print("\nReview the disagreements above before concatenating this with "
          "WIL_ELEV_DICT.csv.")
