"""Experimental LeRobot-style local import adapter.

This is not official LeRobot integration. It converts a small local folder that
resembles common LeRobot exports into the WorldBench episode layout.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from worldbench.dataset import validate_dataset
from worldbench.schemas import ValidationReport
from worldbench.utils import ensure_dir, list_image_files, write_json


REQUIRED_JSON_FILES = ("actions.json", "states.json", "metadata.json")


def import_lerobot_style(input_path: str | Path, output_path: str | Path, overwrite: bool = True) -> ValidationReport:
    """Convert a local LeRobot-style folder into a WorldBench dataset."""

    source = Path(input_path)
    destination = Path(output_path)
    _validate_lerobot_source(source)

    if destination.exists() and overwrite:
        shutil.rmtree(destination)
    elif destination.exists():
        raise FileExistsError(f"Output path already exists: {destination}")

    episode_dir = destination / "episode_001"
    frames_dir = ensure_dir(episode_dir / "frames")
    for index, image_path in enumerate(list_image_files(source / "images")):
        shutil.copy2(image_path, frames_dir / f"{index:03d}{image_path.suffix.lower()}")

    for name in REQUIRED_JSON_FILES:
        shutil.copy2(source / name, episode_dir / name)

    return validate_dataset(destination)


def create_lerobot_style_demo_source(output_path: str | Path, overwrite: bool = True) -> Path:
    """Create a tiny synthetic LeRobot-style source folder for adapter demos."""

    root = Path(output_path)
    if root.exists() and overwrite:
        shutil.rmtree(root)
    elif root.exists():
        raise FileExistsError(f"Output path already exists: {root}")

    images_dir = ensure_dir(root / "images")
    states = []
    actions = []
    robot_x, robot_y = 24, 54
    object_x, object_y = 88, 54

    for t in range(8):
        if t > 0:
            robot_x += 8
            if robot_x >= object_x - 18:
                object_x += 5
        states.append({"t": t, "robot_x": robot_x, "robot_y": robot_y, "object_x": object_x, "object_y": object_y})
        _render_lerobot_demo_frame((robot_x, robot_y), (object_x, object_y), f"{t:03d}").save(images_dir / f"{t:03d}.png")

    for t in range(7):
        actions.append({"t": t, "action": "move_right", "dx": 1.0, "dy": 0.0, "gripper": "open"})

    write_json(root / "actions.json", actions)
    write_json(root / "states.json", states)
    write_json(
        root / "metadata.json",
        {
            "name": "lerobot_style_push_cube_demo",
            "robot": "synthetic_2d_arm",
            "task": "push cube",
            "fps": 5,
            "description": "Tiny synthetic source folder for the experimental LeRobot-style WorldBench adapter.",
        },
    )
    return root


def _validate_lerobot_source(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"LeRobot-style input path does not exist: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"LeRobot-style input path is not a directory: {source}")
    images_dir = source / "images"
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Missing images/ directory: {images_dir}")
    if not list_image_files(images_dir):
        raise ValueError(f"No image files found in {images_dir}")
    for name in REQUIRED_JSON_FILES:
        if not (source / name).is_file():
            raise FileNotFoundError(f"Missing {name}: {source / name}")


def _render_lerobot_demo_frame(robot: tuple[int, int], obj: tuple[int, int], label: str) -> Image.Image:
    width, height = 128, 96
    image = Image.new("RGB", (width, height), (245, 248, 250))
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 16):
        draw.line((x, 0, x, height), fill=(222, 229, 235), width=1)
    for y in range(0, height, 16):
        draw.line((0, y, width, y), fill=(222, 229, 235), width=1)
    draw.rectangle((5, 5, width - 6, height - 6), outline=(175, 188, 199), width=1)
    draw.text((8, 7), f"lerobot-style {label}", fill=(82, 96, 110))

    rx, ry = robot
    ox, oy = obj
    draw.line((rx, ry, ox, oy), fill=(140, 154, 165), width=2)
    draw.ellipse((rx - 8, ry - 8, rx + 8, ry + 8), fill=(218, 65, 54), outline=(148, 43, 35), width=2)
    draw.rectangle((ox - 8, oy - 8, ox + 8, oy + 8), fill=(35, 170, 95), outline=(18, 102, 60), width=2)
    return image
