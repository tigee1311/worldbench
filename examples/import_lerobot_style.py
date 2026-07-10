"""Convert a tiny LeRobot-style local folder into WorldBench format."""

from pathlib import Path
import tempfile

from rich.console import Console

from worldbench.backends.lerobot import (
    create_lerobot_style_demo_source,
    import_lerobot_style,
)


console = Console()
output_path = Path("examples/lerobot_push_cube")

with tempfile.TemporaryDirectory(prefix="worldbench-lerobot-example-") as tmpdir:
    source = create_lerobot_style_demo_source(Path(tmpdir) / "source")
    report = import_lerobot_style(source, output_path)

console.print(f"Converted dataset: {output_path}")
console.print(f"Valid: {report.is_valid}")
for issue in report.issues:
    console.print(f"{issue.level}: {issue.message}")
