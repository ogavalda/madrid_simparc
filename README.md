# SimParc-R Simulator: Madrid case study

<p align="center">
	<img src="docs/figures/logo.png" alt="SimParc-R logo" width="180">
</p>

This repository takes the [SimParc-R](https://github.com/hq-opensource/simparc-r-simulator) residential building-stock simulator (developed by Hydro-Québec for Quebec) and applies it to **10 Madrid residential archetypes**: 5 single-family row houses and 5 apartments, one per construction period from ≤1940 to 2008–2011.

**Read first:**

- [Summary: SimParc-R and the Madrid work](docs/en/madrid-summary.md)
- [Simulation hypotheses of the ten cases](docs/en/madrid-hypotheses.md)

All Madrid-specific code and data live in [`madrid/`](madrid). Run the case with:

```bash
uv run local.py project.yaml
uv run python madrid/madrid_results_summary.py
```

The rest of this README documents the underlying SimParc-R simulator.

## Overview

SIMPARC-R Simulator runs large-scale residential building stock simulations based on the NLR OpenStudio-HPXML workflow. It reads a building stock CSV file, validates and transforms inputs, optionally applies upgrade scenarios, runs OpenStudio simulations in parallel, then generates post-processed outputs ready for analysis.

Key characteristics:

- OpenStudio-HPXML based simulation pipeline.
- Parallel execution for many buildings.
- Rule-based upgrade scenarios (filters + adoption rates).
- Stochastic profiles for selected end uses (e.g., EV, pool, spa, heating setpoint).
- Structured outputs for metadata, timeseries, and errors.

## Repository Structure

Main entry points and modules:

- `local.py`: command-line entry point and orchestration of the full batch workflow.
- `project.yaml`: simulation configuration (input sample, weather mode, output options, upgrades, etc.).
- `base.py`: shared batch base class and simulation directory cleanup helpers.
- `preprocessing.py`: input casting, schema-aligned validation logic, and conversion to per-building dictionaries.
- `upgrading.py`: filter engine and upgrade application logic.
- `building.py`: per-building workflow generation and stochastic profile generation.
- `postprocessing.py`: extraction and write-out of annual/timeseries/error outputs.
- `hpxml_input_schema.py`: extraction of HPXML argument constraints from `measure.xml`.
- `measures/`: OpenStudio measures used in generated OSW (OpenStudio Workflow) files.
- `schemas/`: YAML schema versions for project file validation.
- `weather/`: weather files and mappings used during simulation setup.
- `results/`: simulation artifacts and post-processed datasets.
- `madrid/`: Madrid case study (source spreadsheet, CSV generator, the 10-case building stock, results summary, 3D geometry tools).

## End-to-End Workflow

1. Load and validate project configuration (`project.yaml`) against `schemas/v{SCHEMA_VERSION}.yaml`.
2. Read building stock CSV (`SAMPLE_FILE`) and preprocess data types according to HPXML argument constraints.
3. Apply upgrade sets defined in `UPGRADES_SETTINGS` (filters + adoption rates).
4. Build per-building simulation inputs (HPXML args + non-HPXML args).
5. For each building:
	 - Create simulation folder and metadata JSON.
	 - Generate optional stochastic profiles.
	 - Generate `in.osw` (OpenStudio workflow).
	 - Run OpenStudio CLI.
	 - Read simulation outputs and optionally post-process/cleanup immediately in batch mode.
6. Write global run summary (`results/results_job0.json.gz`).
7. Generate partitioned parquet datasets (metadata, timeseries, errors) during post-processing.

## Requirements

- Python 3.11+
- OpenStudio SDK 3.9.0
- One of:
	- Local Python environment managed with UV
	- Dev Container environment (Docker + VS Code Dev Containers)

Python dependencies are declared in `pyproject.toml`.

## Installation

### Option A: UV + local OpenStudio SDK

1. Install UV: https://docs.astral.sh/uv/getting-started/installation/
2. Install OpenStudio SDK 3.9.0: https://github.com/NREL/OpenStudio/releases/tag/v3.9.0
3. Clone this repository.
4. Sync dependencies:

```bash
uv sync
```

5. Make OpenStudio available:
	 - Preferred: set `OPENSTUDIO_EXE` to the full executable path.
	 - Alternative: add OpenStudio `bin` to your `PATH`.

Example (PowerShell):

```powershell
$env:OPENSTUDIO_EXE = "C:\path\to\OpenStudio-3.9.0\bin\openstudio.exe"
```

### Option B: Dev Container

1. Install Docker.
2. Install VS Code.
3. Install the Dev Containers extension.
4. Reopen this repository in the provided development container.

In container mode, the runtime checks `AM_I_IN_A_DOCKER_CONTAINER` and uses `openstudio` directly.

## Quick Start

Run a full simulation batch:

```bash
uv run local.py project.yaml
```

## Configuration (`project.yaml`)

Important fields include:

- `SCHEMA_VERSION`: selects the validation schema under `schemas/`.
- `SAMPLE_FILE`: path to the CSV file listing the buildings to simulate.
- `HPXML_SCHEMA_FILE`: path to measure XML used to infer HPXML constraints.
- `N_JOBS`: parallel workers. If omitted, defaults to CPU count minus 8.
- `SIMULATION_TIMESTEP`, `SIMULATION_YEAR`, `SIMULATION_RUN_PERIOD`.
- `WEATHER_FILE_TYPE`: weather mapping mode (e.g., AMY, CWEC, PCIC, TMYx for Madrid).
- `BATCH_MODE`: controls immediate post-process/cleanup behavior per building.
- Output switches (`INCLUDE_ANNUAL_*`, `INCLUDE_TIMESERIES_*`, etc.).
- `UPGRADES_SETTINGS`: named upgrade sets with:
	- `Filters` (`all`, `any`, `not` logic)
	- `Adoption rate`
	- `Upgrades` arguments

## Inputs and Outputs

Typical inputs:

- Building stock CSV with both HPXML-related and custom columns.
- Project configuration YAML.
- Weather file mappings and EPW files.

Typical outputs in `results/`:

- Per-building folders (logs, workflow artifacts, optional intermediate files).
- `results_job0.json.gz`: condensed per-simulation summary.
- `metadata.parquet/`: partitioned metadata by building.
- `timeseries.parquet/`: partitioned timeseries by building (if enabled).
- `errors.parquet/`: failures with status and messages.

## Upgrade Filter Syntax

Supported operators in filter conditions:

- `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`

Logical structures:

- `{"all": [...]}`: logical AND
- `{"any": [...]}`: logical OR
- `{"not": [...]}`: logical NOT on grouped conditions

Atomic condition format:

```yaml
["column_name", "operator", value]
```

## Notes and Limitations

- This repository currently runs through `local.py`.
- Parallelism currently uses Joblib backends configured in code.
- OpenStudio path resolution order is:
	1. `OPENSTUDIO_EXE`
	2. `openstudio` from system `PATH`
- Large batches can generate substantial disk usage in `results/`.

## Troubleshooting

- OpenStudio not found:
	- Verify `OPENSTUDIO_EXE` or `PATH`.
- Schema validation error:
	- Ensure `SCHEMA_VERSION` matches a file in `schemas/`.
- Missing weather mapping or EPW:
	- Check `WEATHER_FILE_TYPE`, `SIMULATION_YEAR`, and region naming in input CSV.
- Empty/partial outputs:
	- Inspect `openstudio_output.log` and per-building status in post-processed outputs.

## Related Tooling

The CSV file listing the buildings in the stock to simulate can be prepared using the dedicated sampler repository:

- https://github.com/hq-opensource/simparc-r-sampler

## Contributing

1. Create a feature branch.
2. Keep configuration changes explicit and reproducible.
3. Validate with a small sample before large batch runs.
4. Open a pull request with context, assumptions, and test evidence.

## License

See `LICENSE`.

## Scientific Publication

For more information on the methodology and preliminary results, please refer to the following conference paper (eSim 2026): [Residential Building Stock Model of the Province of Quebec, Canada: Methodology, Preliminary Results](https://www.researchgate.net/publication/410669894_Residential_Building_Stock_Model_of_the_Province_of_Quebec_Canada_Methodology_Preliminary_Results)

## Acknowledgements and Underlying Software

This tool relies on the open-source ResStock and BuildStockBatch projects developed by
Alliance for Energy Innovation, LLC.

These two tools are distributed under their own licenses, copies of which are available in the [third_party_licenses](third_party_licenses) directory. You can also consult the official repositories and license terms in the following GitHub repositories:

- https://github.com/NatLabRockies/resstock
- https://github.com/NatLabRockies/buildstockbatch

This project is not affiliated with, approved by, or endorsed by the authors of
ResStock and BuildStockBatch.
  
