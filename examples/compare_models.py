"""Compare the synthetic good_model and bad_model runs.

Run `worldbench demo` first to create examples/demo_dataset.
"""

from rich.console import Console
from rich.table import Table

from worldbench.runners.comparator import compare_model_folders, save_comparison_artifacts


console = Console()
comparison = compare_model_folders("examples/demo_dataset", "good_model", "bad_model")
saved = save_comparison_artifacts(comparison)
overall = comparison["overall"]
metrics = comparison["metrics"]
assert isinstance(overall, dict)
assert isinstance(metrics, list)

table = Table(title="WorldBench demo comparison")
table.add_column("Metric")
table.add_column("good_model", justify="right")
table.add_column("bad_model", justify="right")
table.add_column("Delta", justify="right")

table.add_row("Overall", f"{float(overall['score_a']):.1f}", f"{float(overall['score_b']):.1f}", f"{float(overall['delta']):+.1f}")
for metric in metrics:
    table.add_row(
        str(metric["label"]),
        f"{float(metric['score_a']):.1f}",
        f"{float(metric['score_b']):.1f}",
        f"{float(metric['delta']):+.1f}",
    )

console.print(table)
console.print(comparison["conclusion"])
console.print(f"Saved comparison report: {saved['markdown']}")
