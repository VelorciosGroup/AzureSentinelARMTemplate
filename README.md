# Template Automation

Template Automation is a Python tool to apply a master template over a set of JSON playbooks.  
It allows you to standardize, transform, and validate your automation playbooks efficiently.

---

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Documentation](#documentation)
  - [Core Modules](#core-modules)
  - [Utility Modules](#utility-modules)

---

## Installation

To install the `template_automation` module locally:

1. Clone the repository:

git clone https://github.com/<your-username>/AzureSentinelARMTemplate.git
cd AzureSentinelARMTemplate

2. Create and activate a virtual environment:

python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

3. Install the package in editable mode using `pyproject.toml`:

pip install -e .

This will make the `template_automation` command available as a Python module.

---

## Usage

Run the module via the command line:

python3 -m template_automation --help

You will see:

usage: template_automation [-h] -master MASTER_PATH -dirin DIR_IN -dirout DIR_OUT [-v]

Tool to apply a master template over a set of JSON playbooks.

options:
  -h, --help            show this help message and exit
  -master MASTER_PATH, -m MASTER_PATH
                        Path to the master template JSON file (e.g., Deploy_CrowdStrike.json).
  -dirin DIR_IN, -i DIR_IN
                        Input directory containing the playbooks to process.
  -dirout DIR_OUT, -o DIR_OUT
                        Output directory to write the transformed playbooks.
  -v, --verbose         Increase verbosity level (use -v, -vv, etc.).

### Example

python3 -m template_automation \
    -master ./docs/master_templates/Deploy_CrowdStrike.json \
    -dirin ./examples/good_playbooks/CrowdStrike \
    -dirout ./out/CrowdStrike \
    -v

- `-master` (`-m`): Path to the master template JSON file. **Required**.
- `-dirin` (`-i`): Input directory containing the JSON playbooks. **Required**.
- `-dirout` (`-o`): Directory to write transformed playbooks. **Required**.
- `-v`: Optional verbosity flag. Use `-vv` for more detailed logging.

---

## Examples Directory

- `examples/good_playbooks/`: Playbooks that comply with expected schema.
- `examples/bad_playbooks/`: Playbooks designed to trigger validation errors.

---

## Documentation

Full documentation is generated using `pdoc` and is available in `pdocs/`.

To serve the documentation locally:

mkdocs serve

To generate static HTML:

mkdocs build

### Modules

- Main Index: pdocs/template_automation/index.md
- Configuration: pdocs/template_automation/config.md
- Command-line Interface: pdocs/template_automation/cli.md

### Core Modules

- Core Index: pdocs/template_automation/core/index.md
- Master Loader: pdocs/template_automation/core/master_loader.md
- Playbook Loader: pdocs/template_automation/core/playbook_loader.md
- Transformer: pdocs/template_automation/core/transformer.md
- Writer: pdocs/template_automation/core/writer.md

### Utility Modules

- Utils Index: pdocs/template_automation/utils/index.md
- File System Utilities: pdocs/template_automation/utils/file_system.md
- Logging Utilities: pdocs/template_automation/utils/logging_utils.md
- Validation Utilities: pdocs/template_automation/utils/validation.md

---

## Contributing

Contributions are welcome! Please ensure:

- Code follows Python 3.12+ syntax.
- Documentation is updated in the relevant module.
- Playbooks in `examples/` remain organized as good or bad examples.

---

## License

This project is licensed under the MIT License.
