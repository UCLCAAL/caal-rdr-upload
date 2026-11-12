# CAAL RDR Upload

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Tests status][tests-badge]][tests-link]
[![Linting status][linting-badge]][linting-link]
[![Documentation status][documentation-badge]][documentation-link]
[![License][license-badge]](./LICENSE.md)

<!-- prettier-ignore-start -->
[tests-badge]:              https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/tests.yml/badge.svg
[tests-link]:               https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/tests.yml
[linting-badge]:            https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/linting.yml/badge.svg
[linting-link]:             https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/linting.yml
[documentation-badge]:      https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/docs.yml/badge.svg
[documentation-link]:       https://github.com/UCLCAAL/caal-rdr-upload/actions/workflows/docs.yml
[license-badge]:            https://img.shields.io/badge/License-MIT-yellow.svg
<!-- prettier-ignore-end -->

🚧 **Under development**

Bulk uploads of CAAL monument reports and metadata to UCL RDR via Figshare API.

This project is being developed in collaboration with the
[Centre for Advanced Research Computing](https://ucl.ac.uk/arc), University
College London.

## About

### Project Team

This project is a collaboration between **UCL CAAL** and **UCL Advanced Research Computing (ARC)**.

## Getting Started

### Prerequisites

<!-- Any tools or versions of languages needed to run code. For example specific Python or Node versions. Minimum hardware requirements also go here. -->

`caal-rdr-upload` requires Python 3.11&ndash;3.14.

### Installation

We recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage Python environments.

**For developers:** Clone the repository and install the project with all development, testing and documentation dependencies:

```sh
git clone https://github.com/UCLCAAL/caal-rdr-upload.git
cd caal-rdr-upload
uv venv
uv pip install -e . --group dev
```

**For users:** Create a virtual environment and install the package directly from GitHub:

```sh
uv venv
uv pip install git+https://github.com/UCLCAAL/caal-rdr-upload.git
```

Activate the virtual environment:

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```sh
source .venv/bin/activate
```

### Running Locally

Usage instructions will be added when available.

### Running Tests

Install the testing dependencies:

```sh
uv pip install -e . --group test
```

Run the tests:

```sh
pytest tests
```

To run tests across Python 3.11–3.14 using [tox](https://tox.wiki/en/latest/), run:

```sh
uv python install 3.11 3.12 3.13 3.14
uv run tox
```
### Building Documentation

Install the documentation dependencies:

```sh
uv pip install -e . --group docs
```

Preview the documentation locally:

```sh
mkdocs serve
```

To build and validate the HTML documentation in `site/`:

```sh
mkdocs build --strict
```

Alternatively, build in an isolated environment using [tox](https://tox.wiki/en/latest/):

```sh
tox -e docs
```

## Acknowledgements

This work was funded by Arcadia Charity.
