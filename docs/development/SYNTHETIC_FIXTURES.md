# Synthetic Development Fixtures

Synthetic rollouts remain useful for deterministic tests, corruption checks, adapter development, and offline CLI smoke tests. They are not product evidence or a standardized robotics benchmark.

Generate the local fixture from a repository checkout:

```bash
python scripts/dev/make_synthetic_fixture.py /tmp/worldbench-fixture
```

Asset generators also live under `scripts/dev/`. Tests may continue importing `DemoBackend` directly so fixtures are created in temporary directories. The checked-in `examples/demo_dataset/` and `benchmarks/` content is retained for backward-compatible development examples and corruption validation; public landing pages do not present it as WorldBench's primary workflow.
