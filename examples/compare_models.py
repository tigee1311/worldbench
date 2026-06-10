"""Compare the synthetic good_model and bad_model runs.

Run `worldbench demo` first to create examples/demo_dataset.
"""

from rich.console import Console
from rich.table import Table

from worldbench import WorldBench


console = Console()
bench = WorldBench("examples/demo_dataset")

good = bench.evaluate(predictions="examples/demo_dataset/good_model")
bad = bench.evaluate(predictions="examples/demo_dataset/bad_model")

table = Table(title="WorldBench demo comparison")
table.add_column("Model")
table.add_column("Overall", justify="right")
table.add_column("Action", justify="right")
table.add_column("Contact", justify="right")
table.add_column("Object", justify="right")

for name, result in [("good_model", good), ("bad_model", bad)]:
    table.add_row(
        name,
        f"{result.score:.1f}",
        f"{result.metrics['action_consistency'].score:.1f}",
        f"{result.metrics['contact_realism'].score:.1f}",
        f"{result.metrics['object_permanence'].score:.1f}",
    )

console.print(table)
console.print(f"good_model beats bad_model: {good.score > bad.score}")
