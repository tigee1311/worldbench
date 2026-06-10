"""Run the synthetic WorldBench benchmark suite."""

from rich.console import Console

from worldbench.backends.benchmark import BenchmarkBackend
from worldbench.runners.benchmark import run_benchmark_suite, save_benchmark_artifacts


console = Console()
benchmark_root = BenchmarkBackend().create("benchmarks")
payload = run_benchmark_suite(benchmark_root)
saved = save_benchmark_artifacts(payload)

console.print(f"good_model average: {payload['good_model_average']:.1f}/100")
console.print(f"bad_model average: {payload['bad_model_average']:.1f}/100")
console.print("largest failure modes:")
for item in payload["largest_failure_modes"]:
    console.print(f"- {item}")
console.print(f"Saved benchmark report: {saved['markdown']}")
