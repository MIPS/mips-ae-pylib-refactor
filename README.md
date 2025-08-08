# ATLAS EXPLORER Python Library

## Overview

Atlas Explorer Python Library

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

#### API Version Control

The library uses an API extension version (`API_EXT_VERSION`) for cloud requests. By default, this is set internally, but you can override it by setting the `API_EXT_VERSION` environment variable in your `.env` file or your shell environment:

```
API_EXT_VERSION=0.0.97
```

If `API_EXT_VERSION` is set in your environment or `.env`, it will be used; otherwise, the default version is used. This allows you to test or upgrade API versions without changing the code.

#### Atlas Cloud Credentials

1. **Interactive configuration:**

   ```bash
   uv run atlasexplorer/atlasexplorer.py configure
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
  uv run examples/ae_singlecore.py --elf resources/mandelbrot_rv64_O0.elf --channel development --core "I8500_(1_thread)"
  ```
- **Multicore experiment:**
  ```bash
  uv run examples/ae_multicore.py --elf resources/mandelbrot_rv64_O0.elf resources/memcpy_rv64.elf --channel development --core "I8500_(2_threads)"
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
     python -m pytest -s tests/test_ae_singlecore.py
     ```

**CI/CD:**
- The GitHub Actions workflow uses the `MIPS_ATLAS_CONFIG` secret for API credentials.
- All tests are run in a virtual environment using uv and pytest.

---

### Environment Variables with python-dotenv

This project supports loading environment variables from a `.env` file using [python-dotenv](https://github.com/theskumar/python-dotenv). This is useful for local development and testing.

#### Where configuration is stored
- **.env file**: Always in your project root (auto-generated or copied from env-example)
- **User config file**: Location depends on your OS:
  - **Linux/macOS**: `$HOME/.config/mips/atlaspy/config.json`
  - **Windows**: `%USERPROFILE%\.config\mips\atlaspy\config.json`

#### How to set up
1. Run interactive configuration:
   ```bash
   uv run atlasexplorer/atlasexplorer.py configure
   ```
   After successful configuration, your credentials will be saved to both the user config file (see above) and a `.env` file in your project root. The `.env` file will look like:
   ```env
   MIPS_ATLAS_CONFIG=<apikey>:<channel>:<region>
   ```
2. If you want to set up manually, copy the provided `env-example` file to `.env` and fill in your credentials:
   ```bash
   cp env-example .env
   ```
3. The library and tests will automatically load this file if present.

You can still use shell `export` or CI secrets as before.

## Tips for Python Developers

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
├── .env                        # Local environment variables (auto-generated or copied from env-example)
├── env-example                 # Example .env file for onboarding
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
- The `.env` file stores local environment variables for development/testing.
- The `env-example` file helps new developers set up their environment quickly.
- The root directory contains configuration and setup files.

