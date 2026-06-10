"""Minimal WorldBench SDK quickstart.

Run `worldbench demo` first to create examples/demo_dataset.
"""

from worldbench import WorldBench


bench = WorldBench("examples/demo_dataset")
result = bench.evaluate(predictions="examples/demo_dataset/good_model")
result.print_summary()
result.save_report("quickstart_report.md")
