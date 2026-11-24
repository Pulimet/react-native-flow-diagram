# FlowDiagram CLI (2.0.0)

Python CLI that launches a release app with the FlowDiagram flag, pulls the JSONL run files and builds CSV, averages and
PNG reports. Setup, flags per target, output files and troubleshooting are in the package README (`../README.md`).

```shell
npm run flow-setup                              # from the repository root
npm run flow:android -- --launch_times 10
npm run flow -- --from-dir output/<date>/raw    # no device needed
```

Tests: `.venv-test/bin/python -m pytest -q` from this directory.
