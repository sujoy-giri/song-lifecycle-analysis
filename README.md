# Songs Streaming Lifecycle Analytics

Lifecycle and churn analytics on Spain's daily Top 50 streaming chart: how songs enter, peak, fade and return, how fast the chart rotates, and whether content attributes (explicit vs clean, single vs album, track length) relate to chart longevity.

Based on a Unified Mentor project brief (client scenario: Atlantic Recording Corporation). The analysis is descriptive and rule-based. No predictive model is trained.

## Data

- Source file: `data/raw/Atlantic_Spain.csv`, daily Spain Top 50 snapshots from 18 May 2024 to 27 Nov 2025.
- 27,800 raw rows, 10 columns: `date`, `position`, `song`, `artist`, `popularity`, `duration_ms`, `album_type`, `total_tracks`, `is_explicit`, `album_cover_url`.
- After cleaning: 27,750 rows, 575 unique songs, 555 of 559 calendar days, and 1,003 chart runs (a run is an unbroken streak of chart days).

## Key findings

- **Entry and peak:** among the 422 songs whose first chart run was a genuine run, 52% reached their best position on the day they entered, and 71% within 4 days.
- **Stages:** across all chart days, 34% were Mature, 30% Decline, 20% Peak, 14% New Entry or Growth, and 2% Fringe (brief bottom-of-chart appearances).
- **Churn:** a typical day has 1 new entry (median); the mean is 1.7 because of occasional release-day reshuffles of 13 to 23 entries. About a third of entries are fringe flicker, and 45% are re-entries of songs that had charted before.
- **Explicit vs clean:** no detectable difference in chart longevity (median gap 0 days, 95% interval -8.5 to +7).
- **Single vs album:** singles stayed a median of 16 days longer in their first 90 days (95% interval 5 to 27), but most of that gap comes from release-day clusters. 47% of album tracks debuted alongside 8 or more other new songs, against 4% of singles, and within the same debut-group size no difference was detectable.
- **Track length:** a weak positive association (Spearman 0.13, interval 0.04 to 0.23), mainly because tracks under about 2.75 minutes stayed 8.5 days less (interval 1 to 16). This was an exploratory comparison.
- **Popularity vs rank:** popularity usually peaks after chart rank (median lag about 9 to 18 days depending on the filter). The reason was not tested, and the result covers only about one in five runs.

## Repository structure

```
app/
  streamlit_app.py         Streamlit dashboard
data/
  raw/                     Original CSV, never modified
  processed/               Cleaned and derived tables (see pipeline below)
notebooks/                 Analysis notebooks, run in numbered order
outputs/
  figures/                 Charts exported from the notebooks
  tables/                  Summary tables exported from the notebooks
requirements.txt
```

The research paper and executive summary will be added under `reports/`.

## Analysis pipeline

| Notebook | What it does | Main outputs |
|---|---|---|
| `01_data_validation` | Finds and fixes data problems: a duplicated date, missing dates, inconsistent name capitalization, song details that changed over time | `spain_top50_clean.csv`, `known_gap_dates.csv` |
| `02_lifecycle_construction` | Builds one row per song (entry, exit, peak, days on chart) and detects separate chart runs | `lifecycle_table.csv`, `spain_top50_with_runs.csv` |
| `03_stage_classification` | Labels every song-day as New Entry, Growth, Peak, Mature, Decline or Fringe | `spain_top50_staged.csv`, `stage_distribution.csv` |
| `04_churn_rotation_analysis` | Daily and monthly entries, fringe and re-entry shares, release-day spikes | `daily_churn.csv`, `monthly_churn.csv`, `churn_over_time.png` |
| `05_attribute_vs_lifecycle` | Explicit vs clean, single vs album, debut-group size, track length | `lifecycle_enriched.csv`, comparison tables, `debut_group_size_vs_stay.png` |
| `06_popularity_analysis` | Timing of the popularity peak relative to the rank peak | `popularity_rank_lag.csv`, `rank_vs_popularity_timing.png` |

## Setup

Requires Python 3 (developed on Python 3.14, Windows). From the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the notebooks in order (01 to 06) with the `venv` selected as the kernel. Each one reads the files written by the one before it, and the notebooks use relative paths, so run them from the `notebooks/` folder.

## Run the dashboard

```powershell
streamlit run app/streamlit_app.py
```

The dashboard has four tabs (Song explorer, Stages, Churn, Content) and sidebar filters for date range, explicit or clean, release format and lifecycle stage. The Stages and Churn tabs ignore the stage filter, and the Content tab ignores all filters. The dashboard reads the files in `data/processed/` and `outputs/tables/`, so run the notebooks first.

## Method notes and limitations

- **Duplicate date:** 2025-03-01 had two conflicting snapshots (100 rows). The first was kept, because neither fit the neighbouring days better.
- **Missing dates:** four dates (2025-03-14, 2025-03-25, 2025-07-11, 2025-08-13) are absent from the source and were not filled. Churn measures skip the day after each gap.
- **Names and metadata:** songs and artists are matched ignoring capitalization. Fields that changed over time (duration, album type, explicit flag, track count) use the most recent value.
- **Fringe runs:** runs of 5 days or fewer that never rise above position 41 get no lifecycle stage. They are 31% of runs but 2% of chart days.
- **Stage rules:** New Entry is the first 3 days of a run, Peak is within 3 positions of the run's best, and Decline is more than 10 positions below the best and still sliding versus a week earlier. These thresholds are choices, not estimates from the data.
- **Longevity measure:** days on the chart in the first 90 days after entry, so songs cut off at the edges of the data can be compared fairly. Intervals are bootstrap 95% intervals on median differences.
- **Popularity:** values of 0, mostly on a run's first day, look like placeholders and are treated as missing.
- **Correlation, not cause:** group differences are associations in this data. Artist and genre were not examined.
