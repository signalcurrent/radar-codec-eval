"""Search and download Sentinel-1 L0 (RAW) and matching SLC via ASF.

Auth: EDL bearer token in ~/.edl_token (generate at urs.earthdata.nasa.gov ->
Generate Token; URS basic-auth rejects this account, token works). Usage:

    python scripts/download_s1.py --aoi "POINT(-76.33 36.93)" --max 1 --out data
    python scripts/download_s1.py ... --levels RAW SLC   # add SLC when needed
"""

import argparse
from pathlib import Path

import asf_search as asf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", default="POINT(-76.33 36.93)")  # Norfolk/Hampton Roads port
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--out", default="data")
    ap.add_argument("--levels", nargs="+", default=["RAW"], choices=["RAW", "SLC"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = (Path.home() / ".edl_token").read_text().strip()
    session = asf.ASFSession().auth_with_token(token)

    for level in args.levels:
        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=level,
            beamMode="IW",
            intersectsWith=args.aoi,
            maxResults=args.max,
        )
        subdir = Path(args.out) / ("s1_l0" if level == "RAW" else "s1_slc")
        subdir.mkdir(parents=True, exist_ok=True)
        for r in results:
            p = r.properties
            size_gb = p["bytes"] / 1e9
            print(f"[{level}] {p['sceneName']}  {p['startTime']}  {size_gb:.2f} GB")
        if not args.dry_run:
            results.download(path=str(subdir), session=session, processes=2)
            print(f"[{level}] downloaded {len(results)} product(s) to {subdir}")


if __name__ == "__main__":
    main()
