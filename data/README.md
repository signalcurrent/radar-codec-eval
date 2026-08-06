# Data (git-ignored)

All public, unclassified, non-export-controlled sources.

## Sentinel-1 Level-0 RAW (primary — genuine raw I/Q echoes)

Via Alaska Satellite Facility (free NASA Earthdata login required):

```python
import asf_search as asf
results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    processingLevel="RAW",
    beamMode="IW",
    maxResults=2,
    intersectsWith="POINT(-76.29 36.85)",  # any AOI; pick scenes with point-like targets (ships, corner reflectors)
)
session = asf.ASFSession().auth_with_creds("EARTHDATA_USER", "EARTHDATA_PASS")
results.download(path="data/s1_l0", session=session)
```

Decode with `sentinel1decoder` (pip). Note: L0 samples on the ground have
already been through onboard FDBAQ once — see `radarcodec/baselines/fdbaq.py`
for how that affects baseline accounting.

## Sentinel-1 SLC (image-domain comparison)

Same ASF search with `processingLevel="SLC"`, same scene footprint as the L0
picks so image-domain metrics are apples-to-apples.

## MSTAR public targets (ATR evaluation)

Public release MSTAR chips (T72/BMP2/BTR70 etc.), available via SDMS
(https://www.sdms.afrl.af.mil/index.php?collection=mstar) after free
registration. Put chips under `data/mstar/<class>/`.

Layout after download:

```
data/
├── s1_l0/       # Sentinel-1 L0 .SAFE products
├── s1_slc/      # matching SLC products
├── mstar/       # MSTAR chips by class
└── patches/     # extracted I/Q patches (generated, npz)
```
