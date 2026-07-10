"""Minimal WorldBench SDK quickstart.

This example uses the deterministic development fixture. Generate it first with:
`python scripts/dev/make_synthetic_fixture.py`.
"""

from worldbench import WorldBench


bench = WorldBench("examples/demo_dataset")
result = bench.evaluate(predictions="examples/demo_dataset/good_model")
result.print_summary()
result.save_report("quickstart_report.md")
