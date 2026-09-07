# Jakarta historical PM2.5 and PM10 series: provenance and quality
Publisher: Open-Meteo / CAMS Global; deposited dataset by Nitiraj Kulkarni and Jagadish Tawade
Source: https://zenodo.org/records/18673885
API source: https://air-quality-api.open-meteo.com/v1/air-quality
Retrieved: 2026-09-07

## What the two lines are

`pm2_5` and `pm10` are separate Open-Meteo Air Quality API variables, both in
µg/m³. They are CAMS global model concentrations near the surface at the
Jakarta coordinate (-6.2088, 106.8456), not DKI station measurements or ISPU
values. The CAMS global product is a roughly 0.4° (about 45 km), 3-hourly model
grid. The Zenodo record covers 2022-08-01 through 2026-02-18; the repository
also contains a separately labelled Open-Meteo refresh from 2026-06-07 through
2026-09-06.

The retained CSV is daily. For the repository's recent refresh, ingestion
groups the API timestamps by local Asia/Jakarta date and averages each
pollutant independently over its available upstream values. The Zenodo
artifact supplies daily date rows, but does not retain raw timestamps or
document its per-day sample count in the metadata available here; its original
resampling method is therefore an evidence gap. Missing PM10 is not filled
from PM2.5, and vice versa. No forward-fill, interpolation, or ISPU conversion
is applied.
The chart sends the stored daily rows directly to the line series; it does not
aggregate them again. The station trend view is a separate data layer.

## Audit of the retained file (1,387 paired daily rows)

The file has 1,390 distinct dates from 2022-08-01 to 2026-09-06, with a
108-day coverage gap after 2026-02-18 before the refresh begins on 2026-06-07.
Each pollutant has 1,387 non-missing values and three missing values; the
paired rows are therefore observations/dates, not station readings. PM2.5 has
mean/median
66.16/67.28 and PM10 has mean/median 83.20/85.78 µg/m³.

Across paired rows, Pearson correlation is 0.883 and Spearman correlation is
0.873. Mean absolute difference is 17.06, median absolute difference 16.80,
and RMSE 23.05 µg/m³. The median PM10:PM2.5 ratio is 1.435 (mean 1.272).
Absolute differences are within 1, 2, and 5 µg/m³ for 30.6%, 36.8%, and
40.1% of pairs; relative differences are within 5%, 10%, and 20% for 39.4%,
40.0%, and 40.1%. Only one pair is exactly equal (0.072%); one pair has
PM10 below PM2.5 (0.072%). Absolute-difference percentiles (50th/90th/95th/
99th/maximum) are 16.80/37.56/41.38/47.87/60.36 µg/m³.

The largest absolute gap is 2023-06-06 (PM2.5 136.59, PM10 196.95; gap
60.36 µg/m³). The smallest is 2025-03-01 (both 93.554; the single exact
equality). These results support `accurate/plausible` for independent mappings:
the lines co-move, as particulate measures can, but are not duplicates. The
co-movement is an interpretation of this model series, not a health or legal
conclusion; the approximately 45 km grid and daily averaging limit local
inference.

The visual near-overlap is concentrated in the 92-row recent refresh: its
Pearson correlation is 0.997, median gap 1.89 µg/m³, and median ratio 1.022.
The 1,295 Zenodo rows have correlation 0.895, median gap 19.66 µg/m³, and
median ratio 1.436. The repository code does not alias the variables, but the
sharp change between source segments is not explained by the Zenodo metadata;
model version, domain selection, or upstream processing may have changed.
Treat the merged file as two provenance segments rather than a fully
homogeneous instrument series until that upstream continuity is documented.

The quality diagnostic flags near-identity, a PM10-below-PM2.5 rate above 5%,
or the combination of correlation at least 0.99999 and mean absolute
difference below 0.01 µg/m³. None is present in the retained file.
