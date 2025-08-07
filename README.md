# ATLAS EXPLORER Python library

## Overview

Atlas Explorer python library

## Setup

### Prerequisites

* Python 3.12 (required)
* [uv](https://github.com/astral-sh/uv) (recommended for dependency management)
* Git (for cloning the repository)

### Setup and Installation

This project uses [uv](https://github.com/astral-sh/uv) to manage a virtual environment and dependencies. Follow these steps to get set up:

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MIPS/mips-ae-pylib.git
   cd mips-ae-pylib
   ```

2. **Create a virtual environment:**

   ```bash
   uv venv
   ```

   This creates a `.venv` folder containing a local Python environment.

3. **Activate the virtual environment:**

   On macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```
   On Windows (PowerShell):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. **Install dependencies and set up the project:**

   ```bash
   uv pip install -e .
   ```

   This command installs the package in "editable" mode, so any changes you make to the code are reflected immediately. It also installs all required dependencies listed in `setup.py` and `pyproject.toml`.

You do not need a `requirements.txt` file—`uv` will handle dependencies based on your project configuration files.

---

### Configuration

You must configure Atlas Explorer Cloud Access before running experiments or tests. You can do this in two ways:

1. **Interactive configuration:**

   ```bash
   python atlasexplorer/atlasexplorer.py configure
   ```
   This will prompt you for your API key, channel, and region, and store them in a config file.

2. **Environment variable (recommended for CI):**

   ```bash
   export MIPS_ATLAS_CONFIG=<apikey>:<channel>:<region>
   ```
   In GitHub Actions, set this as a secret and expose it in your workflow:
   ```yaml
   env:
     MIPS_ATLAS_CONFIG: ${{ secrets.MIPS_ATLAS_CONFIG }}
   ```

---

## Usage

### Running Examples

You can run the provided example scripts using uv:

- **Single core experiment:**
  ```bash
  uv run examples/ae_singlecore.py --elf resources/mandelbrot_rv64_O0.elf --channel development --core I8500_(1_thread)
  ```
- **Multicore experiment:**
  ```bash
  uv run examples/ae_multicore.py --elf resources/mandelbrot_rv64_O0.elf resources/memcpy_rv64.elf --channel development --core I8500_(2_threads)
  ```

You can also specify `--expdir`, `--region`, and `--verbose` as needed. See `examples/ae_singlecore.py` and `examples/ae_multicore.py` for full CLI options.

### Running Tests

1. **Install pytest (if not already installed):**

   ```bash
   uv pip install pytest
   uv pip install pytest-cov  # Optional: for coverage reports
   ```

2. **Run all tests from the project root:**

   ```bash
   python -m pytest -s
   ```

   - To run a specific test file:
     ```bash
     python -m pytest tests/test_ae_singlecore.py
     ```

**CI/CD:**
- The GitHub Actions workflow uses the `MIPS_ATLAS_CONFIG` secret for API credentials.
- All tests are run in a virtual environment using uv and pytest.

---

## Tips for Junior Python Developers

- Always activate your virtual environment before installing or running anything.
- Use `uv pip install -e .` to install your project in editable mode for easy development.
- Store secrets (like API keys) in environment variables, not in code or config files.
- Run tests from the project root directory (where `pyproject.toml` and `setup.py` are located).
- If you see import errors, double-check your Python version and that you installed dependencies with `uv pip install -e .`.
- Use argparse in your scripts for flexible CLI options.
- Read and follow example scripts—they show best practices for using the library.
- Use `print()` and `assert` in your tests to debug and validate results.
- Check the `tests/` directory for sample test cases and usage patterns.
- Use `pytest -s` to see print output during test runs.
- For CI, use secrets and environment variables for sensitive data.
- If you get API errors, check your credentials and network access.

---

## Project Structure

```
mips-ae-pylib/
├── atlasexplorer/              # Main package directory
│   ├── __init__.py
│   └── atlasexplorer.py
├── resources/                  # Example ELF files and other resources
│   ├── mandelbrot_rv64_O0.elf
│   ├── mandelbrot_rv64_O3.elf
│   └── memcpy_rv64.elf
├── tests/                      # Test files
│   ├── test_ae_singlecore.py
│   ├── test_ae_multicore.py
│   └── __pycache__/
├── examples/                   # Example CLI scripts
│   ├── ae_singlecore.py
│   └── ae_multicore.py
├── testharness.py              # Example script for running experiments
├── README.md                   # Project documentation
├── setup.py                    # Python packaging setup
├── pyproject.toml              # Project metadata and dependencies
├── Pipfile                     # (optional) Pipenv file
├── Pipfile.lock                # (optional) Pipenv lock file
├── uv.lock                     # (optional) uv lock file
└── .python-version             # Python version file
```

- The `atlasexplorer/` directory contains your main library code.
- The `examples/` directory contains CLI scripts for running experiments.
- The `tests/` directory contains your test scripts.
- The `resources/` directory contains example ELF files for experiments.
- The root directory contains configuration and setup files.

