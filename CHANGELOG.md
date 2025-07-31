# Changelog

## [2025/07/31]

- Both scripts (`getVCOEnterpriseGetEnterpriseEvents.py` and `getVCOEnterpriseGetEdgeFlowVisibilityMetrics.py`) now support command-line arguments for `--start_human` and `--stop_human` using argparse.
- Command-line arguments take priority over environment variables, which take priority over config file values, which take priority over defaults.
- Added `--help` output for both scripts, making it easy to discover and add more CLI options.
- Added/updated unittests to verify CLI override and help output for both scripts.
- README updated to document new CLI usage and extensibility.

## [2025/07/30]

- Refactored both scripts to convert `start_human` and `stop_human` to the required format inside `load_config`, ensuring consistent configuration handling.
- Output filenames now use `start_human` and `stop_human` for better readability and traceability.
- Flowmetric script now uses `stop_human` for the end time, instead of reading up to the natural end (`_now_`).
- Improved comments in `config.jsonc` and `config.json.sample` to clarify local time usage and automatic timezone handling.
- Switched debug print statements in `human_to_rfc3339_nano` to `logger.info` for unified logging.
- No change in actual API logic or output data.
- Added a reference to VMWare, Broadcom and Arista

## [2025/07/29]

- Initial release to the public