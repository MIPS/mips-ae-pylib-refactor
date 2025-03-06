# gyrfalcon-pylib  ATLAS EXPLORER

## Overview

Atlas Explorer python library

## Setup

### Prerequisites

*   [List any software or libraries that need to be installed before using this project.]
    *   Example: Python 3.6+
    *   Example: Pipenv
    *   InquirePy

### Installation

1.  Clone the repository:

    ```bash
    git clone [repository URL]
    cd gyrfalcon-pylib
    ```

2.  Install dependencies using Pipenv:

    ```bash
    pipenv install
    pipenv shell
    ```

## Usage

### Configuration

1.  Configure Atlas Explorer Cloud Access:

    ```bash
    python atlasexplorer.py configure
    ```

    or set the environment variable:

    ```bash
    MIPS_ATLAS_CONFIG = <apikey>:<channel>:<region>
    ```

### Running Experiments

1.  Set the root experiment directory in `testharness.py`:

    ```python
    # filepath: c:\A_LocalGit\MIPS\gyrfalcon-pylib\testharness.py
    # ...existing code...
    myinst.setRootExperimentDirectory("myexperiments")
    # ...existing code...
    ```

2.  Run the test harness:

    ```bash
    python testharness.py
    ```

    This will create a new experiment directory under the `myexperiments` folder.

## Project Structure
