# gyrfalcon-pylib  ATLAS EXPLORER

## Overview

Atlas Explorer python library

## Setup

### Prerequisites

* Python 3.12 (required)
* [uv](https://github.com/astral-sh/uv) (recommended for dependency management)
* Git (for cloning the repository)

### Installation

1.  Clone the repository:

    ```bash
    git clone [repository URL]
    cd gyrfalcon-pylib
    ```

2.  Make sure you are using Python 3.12. If you use pyenv:

    ```bash
    pyenv install 3.12.0
    pyenv local 3.12.0
    ```

    Or ensure your `.python-version` file contains:
    ```
    3.12
    ```

3.  Install uv (if not already installed):

    ```bash
    pip install uv
    ```

4.  Install dependencies and set up the project using uv:

    ```bash
    uv pip install -e .
    ```

    This command installs the package in "editable" mode, so any changes you make to the code are reflected immediately. It also installs all required dependencies listed in `setup.py` and `pyproject.toml`.

## Usage

### Configuration

1.  Configure Atlas Explorer Cloud Access:

    ```bash
    python atlasexplorer/atlasexplorer.py configure
    ```

    or set the environment variable in your shell (replace with your actual values):

    ```bash
    export MIPS_ATLAS_CONFIG=<apikey>:<channel>:<region>
    ```


### Running Tests

1.  Install pytest (if not already installed):

    ```bash
    uv pip install pytest
    uv pip install pytest-cov  # Optional: for coverage reports
    ```

2.  Run all tests from the project root:

    ```bash
    python -m pytest
    ```

    - To see print statements in your tests, add the `-s` option:
      ```bash
      python -m pytest -s
      ```
    - To run a specific test file:
      ```bash
      python -m pytest tests/test_ae_singlecore.py
      ```

**Tips for beginners:**
- Always run tests from the project root directory (where `pyproject.toml` and `setup.py` are located).
- If you see import errors, double-check your Python version and that you installed dependencies with `uv pip install -e .`.

### Running Experiments

1.  Set the root experiment directory in `testharness.py`:

    ```python
    # ...existing code...
    myinst.setRootExperimentDirectory("myexperiments")
    # ...existing code...
    ```

2.  Run the test harness:

    ```bash
    python testharness.py
    ```

    This will create a new experiment directory under the `myexperiments` folder.

3.  Example usage in tests:

    The test files in `tests/` show how to use the `AtlasExplorer` and `Experiment` classes. For example, in `test_ae_singlecore.py`:

    ```python
    from atlasexplorer.atlasexplorer import AtlasExplorer, Experiment

    def test_singlecore():
        aeinst = AtlasExplorer(
            "<your-apikey>",
            "I8500_(1_thread)",
            "us-west-2",
            verbose=True,
        )
        experiment = Experiment("myexperiments", aeinst, verbose=True)
        experiment.addWorkload("resources/mandelbrot_rv64_O0.elf")
        experiment.setCore("I8500_(1_thread)")
        experiment.run()
        total_cycles = experiment.getSummary().getTotalCycles()
        assert total_cycles == 253629
    ```

    Make sure your API key, core name, and region match your configuration.

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
- The `tests/` directory contains your test scripts.
- The `resources/` directory contains example ELF files for experiments.
- The root directory contains configuration and setup files.
