# Third-party sources and dependencies

Versions below describe this delivery's tested/reproduction environment. Dependencies are installed separately; their own licences and notices remain applicable. This document does not replace those notices.

| Component | Version / source | Licence or retained notice | Use |
|---|---|---|---|
| EirGrid planning data | TYTFS2024 Winter Peak 2024, original RAW source | EirGrid accompanying disclaimer retained with source material; do not infer operational approval | Irish planning-network inputs |
| PYPOWER | 5.1.19 | BSD licence in distribution; reference-case notice retained in `data/reference_PYPOWER_LICENSE.txt` | AC calculations and public case9 |
| NumPy | 2.3.5 | BSD-3-Clause; distribution notices apply | Numerical arrays |
| SciPy | 1.17.0 | BSD-3-Clause; bundled-library notices apply | Numerical routines |
| grg-pssedata | 0.1.4 | BSD metadata in published distribution | RAW parsing for Irish reproduction |
| Python | 3.12 used | Python Software Foundation licence | Local application/runtime |
| jsdom | 30.1.1 | MIT | Optional DOM verification, not a shipped browser runtime |
| Microsoft Azure OpenAI | Optional v1 API service | Organiser/resource service terms and access conditions | Live AI integration after access arrives |

The delivered core interface is custom vanilla HTML/CSS/JavaScript with no CDN or third-party UI runtime. Existing supplementary forecast and presentation reproduction components have their own requirements files. VeraGridEngine 6.7.1 and PuLP 3.3.0 were used only in an optional prior independent-import diagnostic; their code is not bundled. Their failed/different outcomes are retained and are not substituted for the current engine.

Source URL: https://cms.eirgrid.ie/all-island-ten-year-transmission-forecast-statement-2024

PYPOWER: https://github.com/rwl/PYPOWER

NumPy: https://numpy.org/doc/stable/license.html

SciPy: https://scipy.org/license/

No third-party branding implies endorsement of this prototype. External presentation materials remain the earlier version and require revision before presenting the current study.
