"""Synthetic benchmark scenario generator."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from worldbench.utils import ensure_dir, write_json


SCENARIO_NAMES = [
    "push_cube",
    "action_mismatch",
    "pre_contact_motion",
    "object_disappears",
    "temporal_flicker",
]


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    failure_mode: str


class BenchmarkBackend:
    """Generate lightweight synthetic benchmark scenarios."""

    width = 128
    height = 96

    scenarios = [
        ScenarioConfig("push_cube", "combined control/contact failures"),
        ScenarioConfig("action_mismatch", "robot moves opposite the commanded action"),
        ScenarioConfig("pre_contact_motion", "object moves before robot/object contact"),
        ScenarioConfig("object_disappears", "object disappears during prediction"),
        ScenarioConfig("temporal_flicker", "prediction flickers or jumps between frames"),
    ]

    def create(self, output_path: str | Path = "benchmarks", overwrite: bool = True) -> Path:
        root = Path(output_path)
        if root.exists() and overwrite:
            shutil.rmtree(root)
        ensure_dir(root)

        for scenario in self.scenarios:
            self._write_scenario(root / scenario.name, scenario)
        return root

    def _write_scenario(self, root: Path, scenario: ScenarioConfig) -> None:
        ensure_dir(root)
        states = _ground_truth_states()
        actions = _actions()
        self._write_episode(root, scenario, states, actions)
        self._write_model(root, "good_model", scenario, states, quality="good")
        self._write_model(root, "bad_model", scenario, states, quality="bad")

    def _write_episode(
        self,
        root: Path,
        scenario: ScenarioConfig,
        states: list[dict[str, tuple[int, int]]],
        actions: list[dict[str, object]],
    ) -> None:
        episode = root / "episode_001"
        frames = ensure_dir(episode / "frames")
        predictions = ensure_dir(episode / "predictions")
        for idx, state in enumerate(states):
            image = self._render_frame(state["robot"], state["object"], f"gt {idx:03d}")
            image.save(frames / f"{idx:03d}.png")
            image.save(predictions / f"{idx:03d}.png")

        write_json(episode / "actions.json", actions)
        write_json(
            episode / "states.json",
            [
                {
                    "t": idx,
                    "robot_x": state["robot"][0],
                    "robot_y": state["robot"][1],
                    "object_x": state["object"][0],
                    "object_y": state["object"][1],
                }
                for idx, state in enumerate(states)
            ],
        )
        write_json(
            episode / "metadata.json",
            {
                "name": scenario.name,
                "robot": "synthetic_2d_mobile_manipulator",
                "task": "push cube",
                "fps": 5,
                "description": f"Synthetic benchmark scenario: {scenario.failure_mode}.",
            },
        )

    def _write_model(
        self,
        root: Path,
        model_name: str,
        scenario: ScenarioConfig,
        states: list[dict[str, tuple[int, int]]],
        quality: str,
    ) -> None:
        model_dir = ensure_dir(root / model_name / "episode_001")
        generated = states if quality == "good" else _bad_states_for_scenario(scenario.name, states)
        for idx, state in enumerate(generated):
            hide_object = quality == "bad" and scenario.name == "object_disappears" and idx in {2, 3, 4, 5, 6, 7, 8, 9}
            flicker = quality == "bad" and scenario.name == "temporal_flicker" and idx in {4, 6, 8}
            if quality == "bad" and scenario.name == "push_cube":
                hide_object = idx == 4
                flicker = idx == 6
            label = f"{quality[:4]} {idx:03d}"
            self._render_frame(
                state["robot"],
                state["object"],
                label,
                hide_object=hide_object,
                flicker=flicker,
            ).save(model_dir / f"{idx:03d}.png")

    def _render_frame(
        self,
        robot: tuple[int, int],
        obj: tuple[int, int],
        label: str,
        hide_object: bool = False,
        flicker: bool = False,
    ) -> Image.Image:
        background = (10, 18, 28) if not flicker else (44, 17, 20)
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)
        for x in range(0, self.width, 16):
            draw.line((x, 0, x, self.height), fill=(25, 38, 50), width=1)
        for y in range(0, self.height, 16):
            draw.line((0, y, self.width, y), fill=(25, 38, 50), width=1)
        draw.rectangle((5, 5, self.width - 6, self.height - 6), outline=(54, 78, 96), width=1)
        draw.text((8, 7), label, fill=(128, 152, 170))

        rx, ry = robot
        ox, oy = obj
        draw.line((rx, ry, ox, oy), fill=(52, 72, 88), width=2)
        draw.rounded_rectangle((rx - 10, ry - 8, rx + 10, ry + 8), radius=4, fill=(80, 172, 214), outline=(190, 236, 255), width=1)
        draw.ellipse((rx - 5, ry - 5, rx + 5, ry + 5), fill=(231, 76, 60), outline=(255, 180, 160), width=1)
        draw.rectangle((rx - 4, ry + 8, rx + 4, ry + 12), fill=(7, 14, 22))
        if not hide_object:
            draw.rectangle((ox - 8, oy - 8, ox + 8, oy + 8), fill=(46, 204, 113), outline=(179, 255, 204), width=2)
        return image


def _ground_truth_states() -> list[dict[str, tuple[int, int]]]:
    robot = (24, 50)
    obj = (84, 50)
    states = [{"robot": robot, "object": obj}]
    for _ in range(9):
        contact = ((robot[0] - obj[0]) ** 2 + (robot[1] - obj[1]) ** 2) ** 0.5 <= 18.0
        robot = (robot[0] + 8, robot[1])
        if contact:
            obj = (obj[0] + 8, obj[1])
        states.append({"robot": robot, "object": obj})
    return states


def _actions() -> list[dict[str, object]]:
    return [
        {"t": idx, "action": "move_right", "dx": 1.0, "dy": 0.0, "gripper": "open"}
        for idx in range(9)
    ]


def _bad_states_for_scenario(name: str, states: list[dict[str, tuple[int, int]]]) -> list[dict[str, tuple[int, int]]]:
    bad: list[dict[str, tuple[int, int]]] = []
    start_robot = states[0]["robot"]
    start_object = states[0]["object"]
    for idx, state in enumerate(states):
        robot = state["robot"]
        obj = state["object"]
        if name == "action_mismatch":
            robot = (max(14, start_robot[0] - idx * 5), start_robot[1])
        elif name == "pre_contact_motion":
            if idx >= 1:
                obj = (start_object[0] + idx * 7, start_object[1])
        elif name == "object_disappears":
            robot = state["robot"]
        elif name == "temporal_flicker":
            if idx in {4, 6, 8}:
                robot = (112, 18)
                obj = (34 + idx * 3, 76)
        elif name == "push_cube":
            robot = (max(14, start_robot[0] - idx * 5), start_robot[1])
            if idx >= 2:
                obj = (start_object[0] + idx * 4, start_object[1])
            if idx == 6:
                robot = (110, 18)
        bad.append({"robot": robot, "object": obj})
    return bad
