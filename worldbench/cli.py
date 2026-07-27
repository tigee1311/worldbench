"""WorldBench command line interface."""

from __future__ import annotations

import click

from worldbench.backends.lerobot import import_lerobot_repo
from worldbench.commands.dashboard import dashboard
from worldbench.commands.eval_batch import eval_batch
from worldbench.commands.eval_video import eval_video, eval_videos
from worldbench.commands.gate import gate
from worldbench.commands.import_lerobot import import_lerobot
from worldbench.commands.legacy import (
    benchmark,
    compare,
    demo,
    eval_cmd,
    init,
    make_demo_video,
    make_screenshots,
    report,
    validate,
)
from worldbench.commands.verify import verify_run
from worldbench.version import WORLD_BENCH_VERSION

__all__ = ["app", "import_lerobot_repo"]


@click.group(help="Regression testing for video-based robotics world models.")
@click.version_option(WORLD_BENCH_VERSION, prog_name="worldbench")
def app() -> None:
    pass


for command in (
    init,
    demo,
    validate,
    benchmark,
    import_lerobot,
    eval_cmd,
    eval_video,
    eval_videos,
    eval_batch,
    gate,
    verify_run,
    compare,
    report,
    dashboard,
    make_demo_video,
    make_screenshots,
):
    app.add_command(command)


if __name__ == "__main__":
    app()
