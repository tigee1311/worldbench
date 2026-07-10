"""Synthetic demo dataset generator."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from worldbench.utils import ensure_dir, write_json


class DemoBackend:
    """Generate deterministic synthetic rollouts and model outputs."""

    width = 128
    height = 96

    def create(
        self, output_path: str | Path = "examples/demo_dataset", overwrite: bool = True
    ) -> Path:
        root = Path(output_path)
        if root.exists() and overwrite:
            shutil.rmtree(root)
        ensure_dir(root)

        episodes = [
            _episode_plan(
                name="episode_001",
                task="push cube right",
                robot_start=(24, 50),
                object_start=(84, 50),
                delta=(8, 0),
                actions=["move_right"] * 7 + ["close_gripper", "move_right"],
            ),
            _episode_plan(
                name="episode_002",
                task="push cube down",
                robot_start=(58, 18),
                object_start=(58, 68),
                delta=(0, 7),
                actions=["move_down"] * 7 + ["close_gripper", "move_down"],
            ),
        ]

        for plan in episodes:
            self._write_episode(root, plan)

        self._write_model_outputs(root, episodes, "good_model", quality="good")
        self._write_model_outputs(root, episodes, "bad_model", quality="bad")
        self._mirror_example_outputs(root)
        return root

    def init_structure(self, output_path: str | Path) -> Path:
        root = Path(output_path)
        episode = root / "episode_001"
        ensure_dir(episode / "frames")
        ensure_dir(episode / "predictions")
        write_json(
            episode / "actions.json",
            [
                {
                    "t": 0,
                    "action": "move_right",
                    "dx": 1.0,
                    "dy": 0.0,
                    "gripper": "open",
                },
                {
                    "t": 1,
                    "action": "close_gripper",
                    "dx": 0.0,
                    "dy": 0.0,
                    "gripper": "closed",
                },
            ],
        )
        write_json(
            episode / "states.json",
            [
                {"t": 0, "robot_x": 20, "robot_y": 50, "object_x": 80, "object_y": 50},
                {"t": 1, "robot_x": 30, "robot_y": 50, "object_x": 80, "object_y": 50},
            ],
        )
        write_json(
            episode / "metadata.json",
            {
                "name": "push_cube_template",
                "robot": "synthetic_2d_arm",
                "task": "push cube",
                "fps": 5,
                "description": "Template WorldBench rollout. Add frames and predictions as numbered PNG files.",
            },
        )
        return root

    def _write_episode(self, root: Path, plan: dict[str, object]) -> None:
        episode_dir = root / str(plan["name"])
        frames_dir = episode_dir / "frames"
        predictions_dir = episode_dir / "predictions"
        ensure_dir(frames_dir)
        ensure_dir(predictions_dir)
        states = plan["states"]
        actions = plan["actions_json"]

        for idx, state in enumerate(states):
            image = self._render_frame(
                state["robot"], state["object"], label=f"gt {idx:03d}"
            )
            image.save(frames_dir / f"{idx:03d}.png")
            image.save(predictions_dir / f"{idx:03d}.png")

        write_json(episode_dir / "actions.json", actions)
        write_json(episode_dir / "states.json", plan["states_json"])
        write_json(
            episode_dir / "metadata.json",
            {
                "name": str(plan["name"]),
                "robot": "synthetic_2d_arm",
                "task": str(plan["task"]),
                "fps": 5,
                "description": "Synthetic robot rollout for world-model evaluation.",
            },
        )

    def _write_model_outputs(
        self,
        root: Path,
        episodes: list[dict[str, object]],
        model_name: str,
        quality: str,
    ) -> None:
        model_root = root / model_name
        ensure_dir(model_root)
        for plan in episodes:
            episode_dir = model_root / str(plan["name"])
            ensure_dir(episode_dir)
            states = plan["states"]
            bad_states = _bad_states(plan) if quality == "bad" else states
            for idx, state in enumerate(bad_states):
                hide_object = quality == "bad" and idx in {4}
                flicker = quality == "bad" and idx in {6}
                label = f"gt {idx:03d}" if quality == "good" else f"bad {idx:03d}"
                image = self._render_frame(
                    state["robot"],
                    state["object"],
                    label=label,
                    hide_object=hide_object,
                    flicker=flicker,
                )
                image.save(episode_dir / f"{idx:03d}.png")

    def _mirror_example_outputs(self, root: Path) -> None:
        if root.name != "demo_dataset" or root.parent.name != "examples":
            return
        for model_name, folder_name in [
            ("good_model", "good_model_outputs"),
            ("bad_model", "bad_model_outputs"),
        ]:
            target = root.parent / folder_name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(root / model_name, target)

    def _render_frame(
        self,
        robot: tuple[int, int],
        obj: tuple[int, int],
        label: str,
        hide_object: bool = False,
        flicker: bool = False,
    ) -> Image.Image:
        background = (14, 21, 28) if not flicker else (48, 20, 20)
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)

        for x in range(0, self.width, 16):
            draw.line((x, 0, x, self.height), fill=(24, 34, 43), width=1)
        for y in range(0, self.height, 16):
            draw.line((0, y, self.width, y), fill=(24, 34, 43), width=1)

        draw.rectangle(
            (5, 5, self.width - 6, self.height - 6), outline=(58, 75, 88), width=1
        )
        draw.text((8, 7), label, fill=(129, 152, 166))

        rx, ry = robot
        ox, oy = obj
        draw.line((rx, ry, ox, oy), fill=(51, 68, 80), width=2)
        draw.ellipse(
            (rx - 8, ry - 8, rx + 8, ry + 8),
            fill=(231, 76, 60),
            outline=(255, 180, 160),
            width=2,
        )
        draw.rectangle((rx - 4, ry - 14, rx + 4, ry - 8), fill=(255, 202, 120))

        if not hide_object:
            draw.rectangle(
                (ox - 8, oy - 8, ox + 8, oy + 8),
                fill=(46, 204, 113),
                outline=(179, 255, 204),
                width=2,
            )
            draw.line((ox - 8, oy, ox + 8, oy), fill=(22, 120, 75), width=1)
            draw.line((ox, oy - 8, ox, oy + 8), fill=(22, 120, 75), width=1)

        return image


def _episode_plan(
    name: str,
    task: str,
    robot_start: tuple[int, int],
    object_start: tuple[int, int],
    delta: tuple[int, int],
    actions: list[str],
) -> dict[str, object]:
    states = [{"robot": robot_start, "object": object_start}]
    states_json = [
        {
            "t": 0,
            "robot_x": robot_start[0],
            "robot_y": robot_start[1],
            "object_x": object_start[0],
            "object_y": object_start[1],
        }
    ]
    actions_json = []
    robot = robot_start
    obj = object_start
    for idx, action in enumerate(actions):
        contact_before_action = (
            (robot[0] - obj[0]) ** 2 + (robot[1] - obj[1]) ** 2
        ) ** 0.5 <= 18.0
        if action.startswith("move"):
            robot = (robot[0] + delta[0], robot[1] + delta[1])
            if contact_before_action:
                obj = (obj[0] + delta[0], obj[1] + delta[1])
        states.append({"robot": robot, "object": obj})
        states_json.append(
            {
                "t": idx + 1,
                "robot_x": robot[0],
                "robot_y": robot[1],
                "object_x": obj[0],
                "object_y": obj[1],
            }
        )

    for idx, action in enumerate(actions):
        dx = 1.0 if "right" in action else 0.0
        dy = 1.0 if "down" in action else 0.0
        actions_json.append(
            {
                "t": idx,
                "action": action,
                "dx": dx,
                "dy": dy,
                "gripper": "closed" if action == "close_gripper" else "open",
            }
        )
    return {
        "name": name,
        "task": task,
        "states": states,
        "states_json": states_json,
        "actions_json": actions_json,
    }


def _bad_states(plan: dict[str, object]) -> list[dict[str, tuple[int, int]]]:
    states = plan["states"]
    bad = []
    first = states[0]
    start_robot = first["robot"]
    for idx, state in enumerate(states):
        obj = state["object"]
        if "right" in str(plan["task"]):
            robot = (max(14, start_robot[0] - idx * 5), start_robot[1])
            if idx >= 2:
                obj = (obj[0] + idx * 4, obj[1])
            if idx == 6:
                robot = (110, 18)
        else:
            robot = (start_robot[0], max(14, start_robot[1] - idx * 4))
            if idx >= 2:
                obj = (obj[0], obj[1] + idx * 3)
            if idx == 6:
                robot = (104, 20)
        bad.append({"robot": robot, "object": obj})
    return bad
