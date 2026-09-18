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

OUTPUT
    out/wil_elev_daily.csv    date, project, site_no, elev_ft
    out/wil_elev_summary.csv  per-pool record span, day count and gaps
"""

import os
import sys
import tempfile

import pandas as pd
from dataretrieval import waterdata

import ssl
import certifi

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
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


def check_api_key():
    """
    The modernized Water Data API is key-authenticated. dataretrieval resolves
    the key from a configure() block, then API_USGS_PAT, then
    ~/.dataretrieval/config.toml. Failing here with a readable message beats
    thirteen identical HTTP errors further down.
    """
    if os.environ.get("API_USGS_PAT"):
        return
    config = os.path.join(
        os.path.expanduser("~"), ".dataretrieval", "config.toml"
    )
    if os.path.isfile(config):
        return
    print(
        "\n[WARNING] No USGS API key found.\n"
        "          Set API_USGS_PAT, or put api_key in %s.\n"
        "          `python -c \"import dataretrieval; "
        "dataretrieval.show_configuration()\"` reports what is in effect.\n"
        "          Continuing anyway in case a configure() block supplies it.\n"
        % config
    )


def project_name(res_sim_path):
    """'/BIG CLIFF LAKE NEAR NIAGARA, OR/14181400/ELEV...' -> the A-part."""
    parts = [p for p in str(res_sim_path).split("/") if p]
    return parts[0] if parts else str(res_sim_path)


def download_pool(site, name, parameter_cd):
    monitoring_location_id = (
        site if str(site).upper().startswith("USGS-") else "USGS-%s" % site
    )
    time_range = "%sT00:00:00Z/%sT23:59:59Z" % (START_DATE, END_DATE)

    data, _ = waterdata.get_daily(
        monitoring_location_id=monitoring_location_id,
        parameter_code=parameter_cd,
        statistic_id=STATISTIC_ID,
        time=time_range,
        skip_geometry=True,
    )
    if data is None or data.empty:
        return None

    frame = data.copy()
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
    if series.empty:
        return None

    return pd.DataFrame(
        {
            "date": series.index.normalize(),
            "project": name,
            "site_no": str(site),
            "elev_ft": series.to_numpy(),
        }
    )


def main():
    check_api_key()

    elev_dict = pd.read_csv(ELEV_DICT_PATH, dtype={"Download_Key": str})
    print("downloading %s to %s for %d pools\n"
          % (START_DATE, END_DATE, len(elev_dict)))

    collected = []
    failed = []

    for _, row in elev_dict.iterrows():
        site = str(row["Download_Key"])
        name = project_name(row["ResSimPath"])
        try:
            frame = download_pool(site, name, PARAMETER_CD)
            if frame is None:
                print("   %-42s empty on %s, retrying %s"
                      % (name, PARAMETER_CD, FALLBACK_PARAMETER_CD))
                frame = download_pool(site, name, FALLBACK_PARAMETER_CD)
            if frame is None:
                print("   %-42s NO DATA" % name)
                failed.append(site)
                continue
            collected.append(frame)
            print("   %-42s %5d days  %s to %s"
                  % (name, len(frame),
                     frame["date"].min().date(), frame["date"].max().date()))
        except Exception as exc:
            print("   %-42s FAILED: %s" % (name, exc))
            failed.append(site)

    if not collected:
        sys.exit("Nothing downloaded. Check the API key and the network.")

    daily = pd.concat(collected, ignore_index=True)

    out_dir = os.path.dirname(DAILY_OUT)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    daily.to_csv(DAILY_OUT, index=False)
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
    summary.to_csv(SUMMARY_OUT, index=False)
    print("wrote %s" % SUMMARY_OUT)

    print("\n%s" % summary.to_string(index=False))
    if failed:
        print("\n*** no data for: %s" % ", ".join(failed))


if __name__ == "__main__":
    main()
