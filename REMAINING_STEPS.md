# Remaining Steps - Residual_Carbon Project

This document outlines all remaining steps after STEP 4 (Export to GeoTIFF Format).

## Completed Steps

- **STEP 1**: Project Structure Setup [COMPLETED]
- **STEP 2**: Google Earth Engine Data Retrieval [COMPLETED]
- **STEP 3**: Clipping to Mato Grosso State [COMPLETED]
- **STEP 4**: Export to GeoTIFF Format (multi-band, interactive confirmation) [COMPLETED]
- **STEP 5**: User Interface - Coordinate Input [COMPLETED]
- **STEP 6**: Radius Clipping (100km circles) [COMPLETED]
- **STEP 7**: Convert Maps to DataFrames (within circles) [COMPLETED]
- **STEP 8**: H3 Index Conversion [COMPLETED]

---

## STEP 5 onward

All planned steps (5 through 14) have been implemented. Key highlights:

- Coordinate input prompts and validation (`user_input.py`) work for both CLI parameters and interactive sessions.
- Raster clipping supports partial coverage when circles touch state boundaries, while still flagging pixels that extend beyond the radius.
- DataFrame conversion, H3 aggregation, suitability scoring, and PyDeck visualization run end-to-end from `main.py`, producing maps in `output/html/`.
- Documentation (README, PROJECT_PLAN, SETUP_GUIDE, TROUBLESHOOTING, PyCharm setup) is kept in sync with the latest pipeline changes.

---

## Optional Enhancements (Backlog)

- Add automated unit/integration tests to complement the manual regression workflow.
- Introduce feedstock-specific weighting or alternative threshold profiles.
- Provide UI controls for filtering hexagons by score range or toggling datasets.
- Package the project for distribution (CLI entry points, installer scripts).

---

## Notes

- Keep the `data/raw/` directory populated with the latest GEE exports before running the pipeline.
- Ensure `PYTHONPATH` includes the project root when running scripts outside PyCharm (System Properties → Environment Variables → add/edit `PYTHONPATH`).
- Use the verification helpers in `src/data/processing/raster_clip.py` and `src/analysis/suitability.py` when validating unfamiliar datasets.
- Review the backlog items above for potential future improvements.

