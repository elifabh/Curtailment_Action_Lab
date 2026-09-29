# Data guide

The v2 interface reads the reference experiment (`reference_*.json`), `recorded.json`, the current agent evaluation and the reports under `validation/` and `evaluation/`.

`TYTFS2024_WP2024_V33.raw` is the public EirGrid planning source. `engine/TYTFS2024_WP2024_V33_model.npz` is its legacy exploratory numerical conversion. The separate ideal-tie diagnostic lives under `validation/irish_*`; it has not replaced the live legacy screen.

The older `catalog.json`, `action_result.json`, `keep_line_in_service.json`, `full_wind_during_outage.json`, `wind_limit_search.json`, `VERIFICATION.json` and `audit/` files are retained research records. They are not the v2 validated result and are not served as validated recommendations. In particular, a partial thermal-screen threshold is not a verified Irish curtailment reduction.

No private data-centre, factory or battery measurement is fabricated or required for this network experiment. See the root README for the separation between source data, synthetic assumptions and calculated outputs.
