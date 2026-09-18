# -*- coding: utf-8 -*-
"""
download_elevations.py

Ten years of daily reservoir elevation for the thirteen Willamette Valley
Project pools in WIL_ELEV_DICT.csv, written as one tidy CSV for the boat ramp
analysis.

WHY THIS IS SEPARATE FROM DP_DL_28Aug2026.py
    That script is the Damages Prevented download and does three things at
    once - USGS elevation, USGS flow, CWMS - then writes DSS for ResSim. This
    needs one of those three, over a much longer window, at a different
    timestep, and its output feeds a plotting script rather than a model. It
    reuses that script's proven SSL setup and download loop verbatim; it does
    not import them, because DP_DL_28Aug2026.py runs its downloads at module
    scope and importing it would kick off the whole Damages Prevented pull.

DAILY, NOT INSTANTANEOUS
    DP_DL_28Aug2026.py downloads 'iv' and resamples. Over a ten-year window
    that quietly fails: USGS instantaneous values generally do not reach back
    that far - many sites start around 2007 - so the early years come back
    thin or empty while the recent years look fine. Daily values go back
    decades. Boat ramp availability is a per-day question anyway, so 'dv'
    with the daily mean statistic is both the reliable choice and the correct
    one.

WHICH ENDPOINT
    The daily endpoint is one request per pool and reaches back decades, so it
    is tried first. It returns nothing for parameter 62614 at these lake sites,
    which is why the first version of this script downloaded thirteen empty
    frames. The continuous endpoint does carry them - it is what
    DP_DL_28Aug2026.py uses - so the script falls through to it and resamples
    to a daily mean. Each run prints which route answered for each pool.

    Continuous costs far more requests: the service caps one call at three
    years, so ten years is four calls per pool, each paged. If the run stops
    partway with a rate-limit error, the budget is the reason - lower
    MAX_CONTINUOUS_YEARS to shrink each page set, or narrow START/END_DATE and
    run it in two passes.

OUTPUT
    out/wil_elev_daily.csv    date, project, site_no, elev_ft
    out/wil_elev_summary.csv  per-pool record span, day count and gaps
"""

import os
import sys
import tempfile

import pandas as pd
import dataretrieval
from dataretrieval import waterdata

# dataretrieval grew a Configuration/configure() API in 1.3.0. Before that -
# 1.2.0 still has waterdata, so the rest of this script runs fine on it - the
# key is passed by setting API_USGS_PAT, which utils._default_headers turns
# into the X-Api-Key header. Import the new API if it is there and fall back to
# the environment if it is not, rather than pinning a version this script does
# not otherwise need.
try:
    from dataretrieval import Configuration
    HAVE_CONFIGURE = True
except ImportError:
    Configuration = None
    HAVE_CONFIGURE = False

import ssl
import certifi

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
# Where the USGS Water Data API key lives. Relative paths resolve from this
# script's own folder, not the shell's working directory, so running it from
# anywhere behaves the same. An absolute Windows path works too:
#     API_KEY_FILE = r"C:\Projects\A_REPOSITORIES\Ephemeral\data\usgs_api_key.txt"
#
# The file holds the key and nothing else. `api_key = <key>` is also accepted,
# so a line copied out of config.toml does not have to be edited down.
#
# It stays OUT of version control - .gitignore already carries
# usgs_api_key.txt, which git matches at any depth, so data/ is covered.
# Setting API_USGS_PAT in the environment instead also works and this file
# then does not need to exist.
API_KEY_FILE = os.path.join("..", "data", "usgs_api_key.txt")

ELEV_DICT_PATH = os.path.join("..", "data", "WIL_ELEV_DICT.csv")
DAILY_OUT = os.path.join("..", "out", "wil_elev_daily.csv")
SUMMARY_OUT = os.path.join("..", "out", "wil_elev_summary.csv")

# Ten complete calendar years. The boat ramp season runs Feb 1 - Dec 15, so
# calendar years divide the record more naturally here than water years do.
START_DATE = "2016-01-01"
END_DATE = "2025-12-31"

# 62614 = lake or reservoir water surface elevation above NGVD 1929, feet.
# A pool that comes back empty is worth retrying on 62615 (above NAVD 1988)
# before assuming the gauge is dead.
PARAMETER_CD = "62614"
FALLBACK_PARAMETER_CD = "62615"
STATISTIC_ID = "00003"  # daily mean

# get_continuous refuses more than three years per call, so a ten-year window
# has to be chunked. Three keeps the number of calls - and the API request
# budget this burns - as low as the service allows.
MAX_CONTINUOUS_YEARS = 3


# --- SSL Certificate Setup ---------------------------------------------------
# Lifted from DP_DL_28Aug2026.py. Builds a combined CA bundle (certifi plus the
# Windows ROOT store) and points REQUESTS_CA_BUNDLE at it, so requests trusts
# USACE's internally-issued certs. Must run before any network call below. On
# non-Windows platforms ssl.enum_certificates does not exist and this falls
# back to certifi alone.
pem_path = os.path.join(tempfile.gettempdir(), "corp_plus_certifi.pem")


def build_windows_ca_bundle(target_pem):
    base_bundle = certifi.where()
    with open(base_bundle, "rb") as src, open(target_pem, "wb") as dst:
        dst.write(src.read())
        try:
            for cert_tuple in ssl.enum_certificates("ROOT"):
                dst.write(ssl.DER_cert_to_PEM_cert(cert_tuple[0]).encode("ascii"))
        except AttributeError:
            print("[WARNING] ssl.enum_certificates not available; using certifi only.")
        except Exception as exc:
            print("[WARNING] Error reading Windows ROOT store: %s" % exc)
    return target_pem


if not os.path.exists(pem_path):
    try:
        bundle_path = build_windows_ca_bundle(pem_path)
        print("[INFO] Built combined CA bundle: %s" % bundle_path)
    except Exception as exc:
        print("[WARNING] Failed to build combined CA bundle: %s" % exc)
        bundle_path = certifi.where()
else:
    bundle_path = pem_path

os.environ["REQUESTS_CA_BUNDLE"] = bundle_path
print("[INFO] Using CA bundle: %s" % bundle_path)
# --- End SSL Setup -----------------------------------------------------------


def resolve_path(path):
    """Anchor a relative path to this script's folder rather than the cwd."""
    if os.path.isabs(path):
        return path
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    )


def read_api_key():
    """
    The key, from API_KEY_FILE if it is there.

    Returns None when there is no file, which is not an error: the key may be
    coming from API_USGS_PAT or ~/.dataretrieval/config.toml instead, and
    dataretrieval resolves those on its own.
    """
    path = resolve_path(API_KEY_FILE)
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read().strip()

    if not text:
        sys.exit("%s is empty." % path)

    # Tolerate a line lifted straight out of config.toml, quotes and all.
    if "=" in text.split("\n", 1)[0]:
        text = text.split("=", 1)[1]
    key = text.strip().strip("\"'").strip()

    if not key:
        sys.exit("%s holds no key once blanks and quotes are stripped." % path)

    print("[INFO] API key read from %s" % path)
    return key


def check_api_key(key):
    """Say where the key is coming from, or that there is not one, up front."""
    if key:
        return
    if os.environ.get("API_USGS_PAT"):
        print("[INFO] Using the API key in API_USGS_PAT.")
        return
    config = os.path.join(
        os.path.expanduser("~"), ".dataretrieval", "config.toml"
    )
    if os.path.isfile(config):
        print("[INFO] Using the API key in %s." % config)
        return
    if not HAVE_CONFIGURE:
        # On 1.2.0 the token only raises the rate limit; requests without one
        # still succeed. Worth saying, so a warning here is not mistaken for
        # the reason a download failed.
        print(
            "\n[INFO] No USGS API key found, and this dataretrieval (%s) uses "
            "the key\n       only to raise the rate limit. The download should "
            "still work.\n" % getattr(dataretrieval, "__version__", "unknown")
        )
        return
    print(
        "\n[WARNING] No USGS API key found. Looked at:\n"
        "            %s\n"
        "            the API_USGS_PAT environment variable\n"
        "            %s\n"
        "          `python -c \"import dataretrieval; "
        "dataretrieval.show_configuration()\"` reports what is in effect.\n"
        "          Continuing anyway in case a configure() block supplies it.\n"
        % (resolve_path(API_KEY_FILE), config)
    )


def project_name(res_sim_path):
    """'/BIG CLIFF LAKE NEAR NIAGARA, OR/14181400/ELEV...' -> the A-part."""
    parts = [p for p in str(res_sim_path).split("/") if p]
    return parts[0] if parts else str(res_sim_path)


def _time_range(start, end):
    return "%sT00:00:00Z/%sT23:59:59Z" % (
        pd.Timestamp(start).strftime("%Y-%m-%d"),
        pd.Timestamp(end).strftime("%Y-%m-%d"),
    )


def _to_series(frame, site):
    """The value column out of a waterdata frame, indexed by time."""
    if frame is None or frame.empty:
        return None

    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"])
    frame = frame.set_index("time").sort_index()

    # The modernized API returns the observation in a 'value' column; the
    # legacy nwis module used a numeric-named column. Same fallback as
    # process_usgs_data in DP_DL_28Aug2026.py.
    if "value" in frame.columns:
        series = frame["value"]
    else:
        numeric = [c for c in frame.columns if c.replace("_", "").isdigit()]
        if not numeric:
            raise ValueError("no value column found for %s" % site)
        series = frame[numeric[0]]

    series = pd.to_numeric(series, errors="coerce")
    # DSS missing-value standins, in case any leak through from the source.
    series[series < -9000] = pd.NA
    series[series == -902] = pd.NA
    series[series == -901] = pd.NA
    series = series.dropna()
    return None if series.empty else series


def fetch_daily(location, parameter_cd, statistic_id):
    """One call to the daily endpoint. Returns None when it has nothing."""
    data, _ = waterdata.get_daily(
        monitoring_location_id=location,
        parameter_code=parameter_cd,
        statistic_id=statistic_id,
        time=_time_range(START_DATE, END_DATE),
        skip_geometry=True,
    )
    return data


def fetch_continuous(location, parameter_cd):
    """
    The continuous endpoint, in chunks, resampled to a daily mean.

    This is the route DP_DL_28Aug2026.py uses and the one known to carry 62614
    for these pools. It costs far more requests than the daily endpoint - hence
    only reaching for it when daily comes back empty - and the service caps a
    single call at three years, so the window is walked in chunks.
    """
    pieces = []
    start = pd.Timestamp(START_DATE)
    final = pd.Timestamp(END_DATE)

    while start <= final:
        stop = min(
            start + pd.DateOffset(years=MAX_CONTINUOUS_YEARS) - pd.Timedelta(days=1),
            final,
        )
        data, _ = waterdata.get_continuous(
            monitoring_location_id=location,
            parameter_code=parameter_cd,
            time=_time_range(start, stop),
        )
        if data is not None and not data.empty:
            pieces.append(data)
        start = stop + pd.Timedelta(days=1)

    if not pieces:
        return None
    return pd.concat(pieces, ignore_index=True)


def download_pool(site, name, parameter_cd):
    """
    Daily elevation for one pool, by whichever route actually returns data.

    Tried in order, cheapest first:
      1. the daily endpoint, filtered to the daily mean
      2. the daily endpoint with no statistic filter, in case this pool
         publishes its daily value under some other statistic
      3. the continuous endpoint, chunked and resampled to a daily mean

    Returns (frame, route) so the caller can report which one answered - if a
    pool silently falls through to the expensive route every run, that is worth
    seeing rather than discovering in the request budget.
    """
    location = (
        site if str(site).upper().startswith("USGS-") else "USGS-%s" % site
    )

    attempts = (
        ("daily", lambda: fetch_daily(location, parameter_cd, STATISTIC_ID)),
        ("daily/any-stat", lambda: fetch_daily(location, parameter_cd, None)),
        ("continuous", lambda: fetch_continuous(location, parameter_cd)),
    )

    for route, call in attempts:
        series = _to_series(call(), site)
        if series is None:
            continue
        if route == "continuous":
            # Sub-daily values collapse to one number per day, matching what
            # the daily endpoint would have returned.
            series = series.resample("D").mean().dropna()
        else:
            series.index = series.index.normalize()

        return (
            pd.DataFrame(
                {
                    "date": series.index,
                    "project": name,
                    "site_no": str(site),
                    "elev_ft": series.to_numpy(),
                }
            ),
            route,
        )

    return None, None


def download_all(elev_dict):
    """The download loop, one pool at a time. A pool that fails is recorded and
    the rest carry on - one dead gauge should not cost the other twelve."""
    collected = []
    failed = []

    for _, row in elev_dict.iterrows():
        site = str(row["Download_Key"])
        name = project_name(row["ResSimPath"])
        try:
            frame, route = download_pool(site, name, PARAMETER_CD)
            if frame is None:
                print("   %-42s empty on %s, retrying %s"
                      % (name, PARAMETER_CD, FALLBACK_PARAMETER_CD))
                frame, route = download_pool(site, name, FALLBACK_PARAMETER_CD)
            if frame is None:
                print("   %-42s NO DATA on either parameter code" % name)
                failed.append(site)
                continue
            collected.append(frame)
            print("   %-42s %5d days  %s to %s  via %s"
                  % (name, len(frame),
                     frame["date"].min().date(), frame["date"].max().date(),
                     route))
        except Exception as exc:
            print("   %-42s FAILED: %s" % (name, exc))
            failed.append(site)

    return collected, failed


def main():
    api_key = read_api_key()
    check_api_key(api_key)

    elev_dict = pd.read_csv(resolve_path(ELEV_DICT_PATH),
                            dtype={"Download_Key": str})
    print("downloading %s to %s for %d pools\n"
          % (START_DATE, END_DATE, len(elev_dict)))

    if api_key and HAVE_CONFIGURE:
        # configure() is the library's highest-precedence source and is a
        # context manager, so the whole loop runs inside it. It also keeps the
        # key out of os.environ, where it would be visible to anything else in
        # the process.
        with dataretrieval.configure(Configuration(api_key=api_key)):
            collected, failed = download_all(elev_dict)
    elif api_key:
        # Pre-1.3.0 route: utils._default_headers reads API_USGS_PAT and sends
        # it as X-Api-Key. Restored afterwards so an interactive session that
        # runs this twice does not leave a key behind in its environment.
        previous = os.environ.get("API_USGS_PAT")
        os.environ["API_USGS_PAT"] = api_key
        try:
            collected, failed = download_all(elev_dict)
        finally:
            if previous is None:
                os.environ.pop("API_USGS_PAT", None)
            else:
                os.environ["API_USGS_PAT"] = previous
    else:
        collected, failed = download_all(elev_dict)

    if not collected:
        sys.exit("Nothing downloaded. Check the API key and the network.")

    daily = pd.concat(collected, ignore_index=True)

    out_dir = os.path.dirname(resolve_path(DAILY_OUT))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    daily.to_csv(resolve_path(DAILY_OUT), index=False)
    print("\nwrote %s (%d rows)" % (DAILY_OUT, len(daily)))

    # A gap count is the difference between the calendar span and the days
    # actually returned - the thing most likely to quietly skew a day count.
    summary = (
        daily.groupby(["project", "site_no"])
        .agg(first_day=("date", "min"), last_day=("date", "max"),
             days=("date", "count"))
        .reset_index()
    )
    summary["calendar_days"] = (
        (summary["last_day"] - summary["first_day"]).dt.days + 1
    )
    summary["missing_days"] = summary["calendar_days"] - summary["days"]
    summary.to_csv(resolve_path(SUMMARY_OUT), index=False)
    print("wrote %s" % SUMMARY_OUT)

    print("\n%s" % summary.to_string(index=False))
    if failed:
        print("\n*** no data for: %s" % ", ".join(failed))


if __name__ == "__main__":
    main()
