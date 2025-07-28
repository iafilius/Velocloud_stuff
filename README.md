# Velocloud VCO Event and Flow Logs Fetcher

[![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Update](https://img.shields.io/badge/last%20update-July%202025-blue)]()

This repository contains Python scripts to fetch event logs and flow visibility metrics from a Velocloud VCO (Virtual Cloud Orchestrator) instance using the Velocloud API.

## Background

Velocloud's VCO API allows you to retrieve event logs and flow logs for your enterprise. However, due to a long-standing bug in the VCO portal, only the first page of results is returned by default, making it difficult to collect complete logs for analysis or archiving.

These scripts resolve this problem by automatically handling pagination, allowing you to fetch and save all available event and flow logs, not just the first page.

> **Note:** Experience shows that the available data in the VCO is typically reset around the start of each new year. This means that, in practice, you can retrieve at most one year of logs, but sometimes the available data may be much less (close to zero), depending on when the reset occurred.

## Features
- Fetches all event logs and flow visibility metrics from Velocloud VCO, overcoming the single-page limitation in VCO.
- Uses the official Velocloud API.
- Easy to configure via `config.jsonc`.
- Modular and easy to modify for your own needs.
- Can be scheduled or repeated as needed (e.g., via cron jobs).
- Output in JSON, which can easily be processed or loaded in visidata.
- Uses a concurrent process to fetch the data and to actually save the data to speed up the process when getting huge data
- Memory optimized: Uses pagination and json-"streaming" to disk to prevent the requirement of huge amount of memory when processing huge flow or event logs

## Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure:**
   - Copy `config.json.sample` to `config.jsonc` and fill in your VCO URL, API token, and other details.

3. **Run the scripts:**
   - To fetch event logs:
     ```bash
     python getVCOEnterpriseGetEnterpriseEvents.py
     ```
   - To fetch flow visibility metrics:
     ```bash
     python getVCOEnterpriseGetEdgeFlowVisibilityMetrics.py
     ```

## Python Environment Management

This project was developed and tested using [pyenv](https://github.com/pyenv/pyenv) to easily manage Python versions and prevent conflicts with the system Python and its modules. Using `pyenv` allows you to:
- Install and switch between multiple Python versions without affecting your system Python.
- Avoid dependency collisions with other Python projects or system tools.

Alternatively, using a standard Python `venv` (virtual environment) is also perfectly fine and recommended for most users. Both approaches will help you keep dependencies isolated and your system clean.

To use `venv`:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To use `pyenv`, see the [pyenv documentation](https://github.com/pyenv/pyenv) for installation and usage instructions.

## Customization
- The scripts are modular and well-commented, making it easy to adapt them to your specific requirements.
- You can schedule them using cron or any other scheduler for regular log collection.

## Requirements
See `requirements.txt` for required Python packages.

## Contributing
Contributions, bug reports, and suggestions are welcome! Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer
These scripts are provided as-is and are not officially supported by Velocloud. Use at your own risk.

## Why Not Use a Generated Library from the Velocloud Swagger Spec?

While Velocloud provides a Swagger/OpenAPI specification for its API, this project does **not** use a generated client library for several reasons:

- **Incomplete/Outdated API Documentation:** The official Swagger spec and API documentation from Velocloud have historically been incomplete or out of date. Critical features—such as the correct handling of pagination via `nextPageLink`—are either missing, poorly documented, or behave differently in practice than described.
- **Pagination Issues:** The `nextPageLink` mechanism, which is essential for retrieving more than the first page of results, has been especially under-documented and confusing. Many users have found that generated clients do not handle this correctly out of the box.
- **Practical Reliability:** By using direct, well-tested requests and custom logic, this project ensures robust handling of pagination and error cases, even when the API documentation is lacking or ambiguous.
- **Transparency and Debugging:** Writing the logic explicitly makes it easier to debug, adapt, and extend, especially when the API changes or behaves unexpectedly.

If Velocloud's API documentation and generated libraries improve in the future, it may become practical to use them. For now, this approach is the most reliable for real-world data collection.

---

Feel free to contribute improvements or report issues!
