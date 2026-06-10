"""Generate the WorldBench README demo video, GIF, and thumbnail.

The demo is generated entirely from code: no external footage, models, or
recordings are required. It renders a polished synthetic robotics evaluation
moment that shows WorldBench catching a plausible-looking but control-wrong
world-model prediction.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
SCALE = 2
FPS = 24
DURATION_SECONDS = 24
FRAME_COUNT = FPS * DURATION_SECONDS
GIF_FPS = 12
GIF_WIDTH = 900

BAD_SCORES = {
    "Overall": 42,
    "Action consistency": 31,
    "Contact realism": 20,
    "Object permanence": 55,
}

GOOD_SCORES = {
    "Overall": 88,
    "Action consistency": 91,
    "Contact realism": 84,
    "Object permanence": 95,
}


class Painter:
    """Small scaled drawing wrapper for anti-aliased Pillow rendering."""

    def __init__(self, draw: ImageDraw.ImageDraw, scale: int = SCALE) -> None:
        self.draw = draw
        self.scale = scale

    def xy(self, values: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(int(round(value * self.scale)) for value in values)

    def line(self, xy: tuple[float, ...], fill: str | tuple[int, int, int, int], width: float = 1) -> None:
        self.draw.line(self.xy(xy), fill=fill, width=max(1, int(round(width * self.scale))))

    def polygon(self, points: list[tuple[float, float]], fill: str | tuple[int, int, int, int], outline: Any = None) -> None:
        self.draw.polygon([self.xy(point) for point in points], fill=fill, outline=outline)

    def rectangle(
        self,
        box: tuple[float, float, float, float],
        fill: str | tuple[int, int, int, int] | None = None,
        outline: str | tuple[int, int, int, int] | None = None,
        width: float = 1,
    ) -> None:
        self.draw.rectangle(self.xy(box), fill=fill, outline=outline, width=max(1, int(round(width * self.scale))))

    def rounded(
        self,
        box: tuple[float, float, float, float],
        radius: float,
        fill: str | tuple[int, int, int, int] | None = None,
        outline: str | tuple[int, int, int, int] | None = None,
        width: float = 1,
    ) -> None:
        self.draw.rounded_rectangle(
            self.xy(box),
            radius=int(round(radius * self.scale)),
            fill=fill,
            outline=outline,
            width=max(1, int(round(width * self.scale))),
        )

    def ellipse(
        self,
        box: tuple[float, float, float, float],
        fill: str | tuple[int, int, int, int] | None = None,
        outline: str | tuple[int, int, int, int] | None = None,
        width: float = 1,
    ) -> None:
        self.draw.ellipse(self.xy(box), fill=fill, outline=outline, width=max(1, int(round(width * self.scale))))

    def text(
        self,
        xy: tuple[float, float],
        text: str,
        fill: str | tuple[int, int, int, int],
        font: ImageFont.ImageFont,
        anchor: str | None = None,
    ) -> None:
        self.draw.text(self.xy(xy), text, fill=fill, font=font, anchor=anchor)


def make_demo_video(output_dir: str | Path = "assets/demo") -> dict[str, Path | bool | int | float]:
    """Generate MP4, GIF, and thumbnail assets."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mp4_path = output / "worldbench_demo.mp4"
    gif_path = output / "worldbench_demo.gif"
    thumbnail_path = output / "thumbnail.png"

    with tempfile.TemporaryDirectory(prefix="worldbench-demo-") as tmp:
        frame_dir = Path(tmp)
        for idx in range(FRAME_COUNT):
            frame = render_frame(idx)
            frame.save(frame_dir / f"frame_{idx:04d}.png", compress_level=1)
            if idx == 0:
                frame.save(thumbnail_path)

        mp4_written = _write_mp4(frame_dir, mp4_path)
        _write_gif(frame_dir, gif_path)

    return {
        "mp4": mp4_path,
        "mp4_written": mp4_written,
        "gif": gif_path,
        "thumbnail": thumbnail_path,
        "gif_size_bytes": gif_path.stat().st_size,
        "frame_count": FRAME_COUNT,
        "duration_seconds": DURATION_SECONDS,
    }


def render_frame(idx: int) -> Image.Image:
    """Render one frame at logical 1280x720 resolution."""

    t = idx / FPS
    canvas = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), "#071019")
    draw = ImageDraw.Draw(canvas, "RGBA")
    painter = Painter(draw)
    fonts = _fonts()

    _draw_background(painter)

    if t < 3.0:
        _draw_title_scene(painter, fonts, t)
    elif t < 9.0:
        _draw_comparison_scene(painter, fonts, mode="bad", local_t=t - 3.0, duration=6.0)
    elif t < 13.0:
        _draw_diagnosis_scene(painter, fonts, local_t=t - 9.0, duration=4.0)
    elif t < 20.0:
        _draw_comparison_scene(painter, fonts, mode="good", local_t=t - 13.0, duration=7.0)
    else:
        _draw_final_scene(painter, fonts, local_t=t - 20.0, duration=4.0)

    frame = canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return frame.convert("RGB")


def _draw_background(painter: Painter) -> None:
    for y in range(HEIGHT):
        mix = y / HEIGHT
        r = int(_lerp_raw(6, 12, mix))
        g = int(_lerp_raw(14, 24, mix))
        b = int(_lerp_raw(24, 34, mix))
        painter.line((0, y, WIDTH, y), fill=(r, g, b, 255), width=1)

    painter.ellipse((-170, -140, 360, 360), fill=(35, 92, 122, 42))
    painter.ellipse((900, 450, 1520, 1040), fill=(29, 135, 91, 32))
    for x in range(0, WIDTH, 64):
        painter.line((x, 96, x + 210, HEIGHT), fill=(64, 92, 118, 18), width=1)
    for y in range(124, HEIGHT, 56):
        painter.line((0, y, WIDTH, y), fill=(64, 92, 118, 14), width=1)


def _draw_title_scene(painter: Painter, fonts: dict[str, ImageFont.ImageFont], t: float) -> None:
    intro = ease_out(min(1.0, t / 1.1))
    pulse = 0.5 + 0.5 * math.sin(t * 3.1)

    _draw_mini_simulator(painter, (355, 250, 925, 530), progress=(t / 3.0) % 1.0, alpha=0.92)

    painter.text((640, 86 - 18 * (1.0 - intro)), "WorldBench", fill=(246, 250, 255, int(255 * intro)), font=fonts["hero"], anchor="mm")
    painter.text(
        (640, 148),
        "Test whether robot world models are useful for control.",
        fill=(189, 210, 226, int(235 * intro)),
        font=fonts["subtitle"],
        anchor="mm",
    )
    painter.rounded((438, 584, 842, 630), radius=23, fill=(18, 31, 44, 215), outline=(77, 119, 151, 150), width=1.4)
    painter.text((640, 607), "Not another world model. The test suite for world models.", fill=(232, 241, 247, 235), font=fonts["body"], anchor="mm")

    painter.rounded((544, 668, 736, 672), radius=2, fill=(46, 204, 113, int(130 + 70 * pulse)))


def _draw_comparison_scene(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    mode: str,
    local_t: float,
    duration: float,
) -> None:
    progress = ease_in_out(min(1.0, local_t / duration))
    reveal = ease_out(min(1.0, max(0.0, (local_t - 0.5) / 1.2)))
    scores = BAD_SCORES if mode == "bad" else GOOD_SCORES
    title = "Bad prediction: plausible video, broken control" if mode == "bad" else "Good prediction: actions and contact stay aligned"
    accent = "#ff6b5f" if mode == "bad" else "#41d38a"

    _draw_top_bar(painter, fonts, title, accent)
    _draw_viewport(
        painter,
        fonts,
        box=(52, 126, 612, 492),
        label="Ground truth rollout",
        mode="ground_truth",
        progress=progress,
        show_warnings=False,
    )
    _draw_viewport(
        painter,
        fonts,
        box=(668, 126, 1228, 492),
        label="World-model prediction",
        mode=mode,
        progress=progress,
        show_warnings=True,
    )
    _draw_metric_cards(painter, fonts, scores, mode=mode, reveal=reveal, y=532)
    _draw_footer_timeline(painter, fonts, progress=progress, mode=mode)

    _fade_edges(painter, local_t, duration)


def _draw_diagnosis_scene(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    local_t: float,
    duration: float,
) -> None:
    progress = ease_in_out(min(1.0, local_t / duration))
    _draw_top_bar(painter, fonts, "WorldBench diagnosis", "#ff6b5f")
    _draw_viewport(
        painter,
        fonts,
        box=(52, 126, 612, 492),
        label="Ground truth rollout",
        mode="ground_truth",
        progress=1.0,
        show_warnings=False,
        dim=0.25,
    )
    _draw_viewport(
        painter,
        fonts,
        box=(668, 126, 1228, 492),
        label="World-model prediction",
        mode="bad",
        progress=1.0,
        show_warnings=True,
        dim=0.2,
    )
    _draw_metric_cards(painter, fonts, BAD_SCORES, mode="bad", reveal=progress, y=532)

    card_alpha = int(235 * ease_out(min(1.0, local_t / 0.8)))
    painter.rounded((284, 202, 996, 418), radius=22, fill=(9, 17, 27, card_alpha), outline=(91, 126, 154, 150), width=1.4)
    painter.text((326, 242), "Main failure", fill=(246, 250, 255, card_alpha), font=fonts["panel"])
    painter.text(
        (326, 292),
        "Prediction looks plausible, but ignores action/contact dynamics.",
        fill=(221, 231, 238, card_alpha),
        font=fonts["statement"],
    )
    _draw_small_evidence(painter, fonts, (326, 348), "Action mismatch", "#ff6b5f", card_alpha)
    _draw_small_evidence(painter, fonts, (514, 348), "Pre-contact motion", "#ffb85c", card_alpha)
    _draw_small_evidence(painter, fonts, (746, 348), "Object flicker", "#ff6b5f", card_alpha)

    _fade_edges(painter, local_t, duration)


def _draw_final_scene(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    local_t: float,
    duration: float,
) -> None:
    reveal = ease_out(min(1.0, local_t / 1.0))
    _draw_mini_simulator(painter, (690, 142, 1188, 520), progress=0.86, alpha=0.78)

    painter.text((92, 130), "WorldBench", fill=(246, 250, 255, int(255 * reveal)), font=fonts["hero"])
    painter.text(
        (96, 206),
        "Not another world model.",
        fill=(197, 217, 231, int(245 * reveal)),
        font=fonts["subtitle"],
    )
    painter.text(
        (96, 252),
        "The test suite for world models.",
        fill=(246, 250, 255, int(245 * reveal)),
        font=fonts["subtitle"],
    )

    commands = ["worldbench demo", "worldbench eval", "worldbench compare"]
    for idx, command in enumerate(commands):
        y = 356 + idx * 58
        alpha = int(235 * ease_out(min(1.0, max(0.0, local_t - 0.6 - idx * 0.16) / 0.8)))
        painter.rounded((100, y, 502, y + 42), radius=12, fill=(15, 28, 42, alpha), outline=(74, 113, 145, int(150 * reveal)))
        painter.text((126, y + 21), command, fill=(236, 244, 250, alpha), font=fonts["mono"], anchor="lm")

    painter.rounded((100, 596, 508, 642), radius=23, fill=(42, 211, 139, int(52 * reveal)), outline=(65, 211, 138, int(185 * reveal)))
    painter.text((304, 619), "Catches futures that look right but act wrong.", fill=(221, 242, 232, int(240 * reveal)), font=fonts["body"], anchor="mm")
    _fade_edges(painter, local_t, duration, out_only=True)


def _draw_top_bar(painter: Painter, fonts: dict[str, ImageFont.ImageFont], title: str, accent: str) -> None:
    painter.rounded((52, 36, 1228, 88), radius=18, fill=(11, 22, 34, 230), outline=(64, 96, 124, 120))
    painter.text((80, 62), "WorldBench", fill="#f6faff", font=fonts["top"], anchor="lm")
    painter.text((260, 62), title, fill="#bed2df", font=fonts["body"], anchor="lm")
    painter.rounded((1030, 51, 1200, 73), radius=11, fill=_hex_to_rgba(accent, 52), outline=_hex_to_rgba(accent, 160))
    painter.text((1115, 62), "evaluating rollout", fill="#edf7ff", font=fonts["tiny"], anchor="mm")


def _draw_viewport(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[float, float, float, float],
    label: str,
    mode: str,
    progress: float,
    show_warnings: bool,
    dim: float = 0.0,
) -> None:
    x1, y1, x2, y2 = box
    shadow = (0, 0, 0, 85)
    painter.rounded((x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius=22, fill=shadow)
    painter.rounded(box, radius=22, fill=(10, 20, 31, 240), outline=(57, 87, 116, 150), width=1.3)
    painter.text((x1 + 24, y1 + 28), label, fill="#eff7ff", font=fonts["panel"], anchor="lm")
    mode_label = "logged future" if mode == "ground_truth" else "predicted future"
    painter.text((x2 - 24, y1 + 28), mode_label, fill="#91a9bb", font=fonts["small"], anchor="rm")

    world = (x1 + 18, y1 + 58, x2 - 18, y2 - 22)
    _draw_sim_floor(painter, world, mode, progress)
    _draw_rollout(painter, fonts, world, mode, progress, show_warnings)
    if dim > 0:
        painter.rounded(world, radius=16, fill=(5, 10, 16, int(155 * dim)))


def _draw_sim_floor(painter: Painter, box: tuple[float, float, float, float], mode: str, progress: float) -> None:
    x1, y1, x2, y2 = box
    painter.rounded(box, radius=16, fill=(9, 18, 28, 255), outline=(34, 58, 80, 175), width=1)
    floor = [(x1 + 28, y2 - 20), (x2 - 28, y2 - 20), (x2 - 128, y1 + 70), (x1 + 128, y1 + 70)]
    painter.polygon(floor, fill=(15, 31, 45, 255))

    for i in range(10):
        q = i / 9
        y = _lerp_raw(y2 - 20, y1 + 70, q**1.65)
        left = _lerp_raw(x1 + 28, x1 + 128, q)
        right = _lerp_raw(x2 - 28, x2 - 128, q)
        alpha = int(_lerp_raw(70, 22, q))
        painter.line((left, y, right, y), fill=(80, 118, 147, alpha), width=1)

    for i in range(11):
        q = i / 10
        bottom_x = _lerp_raw(x1 + 28, x2 - 28, q)
        top_x = _lerp_raw(x1 + 128, x2 - 128, q)
        painter.line((bottom_x, y2 - 20, top_x, y1 + 70), fill=(80, 118, 147, 38), width=1)

    # Subtle scan line keeps the simulator viewport alive without clutter.
    scan_x = _lerp_raw(x1 + 90, x2 - 90, progress)
    scan_color = (67, 211, 139, 45) if mode != "bad" else (255, 107, 95, 38)
    painter.line((scan_x, y1 + 72, scan_x + 68, y2 - 26), fill=scan_color, width=2)


def _draw_rollout(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[float, float, float, float],
    mode: str,
    progress: float,
    show_warnings: bool,
) -> None:
    robot, cube, visible = _state_for_mode(box, mode, progress)
    contact_distance = abs(robot[0] - cube[0])
    in_contact = contact_distance < 82 and visible

    _draw_trajectory(painter, box, mode, progress, kind="robot")
    _draw_trajectory(painter, box, mode, progress, kind="cube")

    if in_contact:
        contact_alpha = int(120 + 80 * math.sin(progress * math.pi * 5) ** 2)
        painter.ellipse((cube[0] - 58, cube[1] - 44, cube[0] + 58, cube[1] + 44), fill=(65, 211, 138, 34), outline=(65, 211, 138, contact_alpha), width=2)
        painter.text((cube[0], cube[1] - 64), "contact zone", fill=(147, 233, 185, 190), font=fonts["tiny"], anchor="mm")

    for ghost_idx in range(5, 0, -1):
        ghost_progress = max(0.0, progress - ghost_idx * 0.035)
        ghost_robot, _, _ = _state_for_mode(box, mode, ghost_progress)
        alpha = int(16 + 18 * (5 - ghost_idx))
        painter.ellipse((ghost_robot[0] - 22, ghost_robot[1] - 16, ghost_robot[0] + 22, ghost_robot[1] + 16), fill=(98, 184, 226, alpha))

    _draw_robot(painter, robot[0], robot[1], heading="right" if mode != "bad" else "left")
    if visible:
        _draw_cube(painter, cube[0], cube[1], alpha=255)
    else:
        _draw_missing_cube(painter, cube[0], cube[1], progress)

    _draw_action_strip(painter, fonts, box)
    if show_warnings:
        if mode == "bad":
            _draw_warning_tags(painter, fonts, box, progress)
        else:
            _draw_good_tags(painter, fonts, box, progress)


def _draw_robot(painter: Painter, x: float, y: float, heading: str) -> None:
    direction = 1 if heading == "right" else -1
    painter.ellipse((x - 58, y + 16, x + 58, y + 42), fill=(0, 0, 0, 75))
    painter.rounded((x - 48, y - 26, x + 48, y + 24), radius=18, fill=(39, 75, 99, 255), outline=(132, 184, 212, 180), width=1.5)
    painter.rounded((x - 38, y - 35, x + 38, y - 18), radius=8, fill=(14, 28, 42, 255), outline=(90, 132, 164, 150), width=1)
    painter.rounded((x - 42, y + 20, x - 18, y + 34), radius=7, fill=(8, 16, 26, 255), outline=(83, 113, 134, 130))
    painter.rounded((x + 18, y + 20, x + 42, y + 34), radius=7, fill=(8, 16, 26, 255), outline=(83, 113, 134, 130))
    painter.ellipse((x - 15, y - 18, x + 15, y + 12), fill=(95, 198, 235, 235), outline=(188, 239, 255, 210), width=1.4)

    arm_base_x = x + direction * 43
    arm_tip_x = x + direction * 78
    painter.line((arm_base_x, y - 4, arm_tip_x, y - 4), fill=(242, 181, 91, 235), width=6)
    painter.line((arm_tip_x, y - 4, arm_tip_x + direction * 16, y - 16), fill=(242, 181, 91, 235), width=4)
    painter.line((arm_tip_x, y - 4, arm_tip_x + direction * 16, y + 8), fill=(242, 181, 91, 235), width=4)


def _draw_cube(painter: Painter, x: float, y: float, alpha: int = 255) -> None:
    s = 28
    top = [(x - s, y - s), (x - s + 12, y - s - 12), (x + s + 12, y - s - 12), (x + s, y - s)]
    side = [(x + s, y - s), (x + s + 12, y - s - 12), (x + s + 12, y + s - 12), (x + s, y + s)]
    front = [(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)]
    painter.ellipse((x - 42, y + 22, x + 54, y + 44), fill=(0, 0, 0, int(72 * alpha / 255)))
    painter.polygon(top, fill=(91, 235, 148, alpha))
    painter.polygon(side, fill=(30, 148, 86, alpha))
    painter.polygon(front, fill=(55, 204, 115, alpha))
    painter.line((x - s, y - s, x + s, y - s), fill=(179, 255, 208, int(180 * alpha / 255)), width=1.5)
    painter.line((x - s, y - s, x - s, y + s), fill=(179, 255, 208, int(120 * alpha / 255)), width=1)


def _draw_missing_cube(painter: Painter, x: float, y: float, progress: float) -> None:
    alpha = int(110 + 80 * math.sin(progress * 40) ** 2)
    painter.rounded((x - 32, y - 32, x + 32, y + 32), radius=8, fill=(255, 107, 95, 16), outline=(255, 107, 95, alpha), width=2)
    painter.line((x - 34, y - 34, x + 34, y + 34), fill=(255, 107, 95, alpha), width=2.3)
    painter.line((x + 34, y - 34, x - 34, y + 34), fill=(255, 107, 95, alpha), width=2.3)


def _draw_trajectory(
    painter: Painter,
    box: tuple[float, float, float, float],
    mode: str,
    progress: float,
    kind: str,
) -> None:
    points = []
    for step in range(26):
        p = min(progress, step / 25)
        robot, cube, visible = _state_for_mode(box, mode, p)
        if kind == "robot":
            points.append(robot)
        elif visible:
            points.append(cube)
    color = (94, 190, 235, 80) if kind == "robot" else (80, 230, 142, 76)
    for a, b in zip(points, points[1:]):
        painter.line((a[0], a[1], b[0], b[1]), fill=color, width=2)


def _draw_action_strip(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[float, float, float, float],
) -> None:
    x1, _, x2, y2 = box
    y = y2 - 34
    painter.rounded((x1 + 24, y, x2 - 24, y + 24), radius=12, fill=(8, 16, 26, 190), outline=(61, 92, 120, 92))
    painter.text((x1 + 42, y + 12), "action log: move_right -> contact -> push", fill=(185, 205, 220, 220), font=fonts["tiny"], anchor="lm")


def _draw_warning_tags(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[float, float, float, float],
    progress: float,
) -> None:
    tags: list[tuple[str, str, float]] = []
    if progress > 0.16:
        tags.append(("Action mismatch", "#ff6b5f", progress))
    if progress > 0.28:
        tags.append(("Pre-contact motion", "#ffb85c", progress - 0.12))
    if progress > 0.48:
        tags.append(("Object flicker", "#ff6b5f", progress - 0.3))
    x1, y1, x2, _ = box
    for idx, (text, color, tag_progress) in enumerate(tags[:3]):
        alpha = int(230 * ease_out(min(1.0, tag_progress * 4)))
        y = y1 + 24 + idx * 32
        _draw_tag(painter, fonts, (x2 - 202, y), text, color, alpha)


def _draw_good_tags(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[float, float, float, float],
    progress: float,
) -> None:
    labels = [("Action aligned", 0.16), ("Contact gated", 0.42), ("Object stable", 0.58)]
    _, y1, x2, _ = box
    for idx, (text, threshold) in enumerate(labels):
        if progress < threshold:
            continue
        alpha = int(220 * ease_out(min(1.0, (progress - threshold) * 5)))
        _draw_tag(painter, fonts, (x2 - 188, y1 + 24 + idx * 32), text, "#41d38a", alpha)


def _draw_tag(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    origin: tuple[float, float],
    text: str,
    color: str,
    alpha: int,
) -> None:
    x, y = origin
    painter.rounded((x, y, x + 164, y + 24), radius=12, fill=_hex_to_rgba(color, min(alpha, 180)), outline=_hex_to_rgba(color, alpha))
    painter.text((x + 12, y + 12), text, fill=(255, 255, 255, alpha), font=fonts["tiny"], anchor="lm")


def _draw_metric_cards(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    scores: dict[str, int],
    mode: str,
    reveal: float,
    y: float,
) -> None:
    alpha = int(235 * reveal)
    painter.rounded((52, y - 20, 1228, y + 106), radius=20, fill=(10, 20, 31, alpha), outline=(57, 87, 116, int(145 * reveal)))
    painter.text((82, y + 2), "WorldBench metrics", fill=(238, 246, 252, alpha), font=fonts["panel"])
    painter.text((82, y + 34), "control-aware checks", fill=(144, 166, 183, alpha), font=fonts["small"])

    start_x = 352
    card_w = 196
    gap = 18
    for idx, (name, target) in enumerate(scores.items()):
        card_reveal = ease_out(min(1.0, max(0.0, reveal * 1.25 - idx * 0.08)))
        score = int(round(target * card_reveal))
        x = start_x + idx * (card_w + gap)
        color = _score_color(target, mode)
        painter.rounded((x, y, x + card_w, y + 78), radius=14, fill=(16, 29, 42, int(235 * reveal)), outline=(72, 102, 126, int(145 * reveal)))
        painter.text((x + 16, y + 18), name, fill=(170, 190, 205, alpha), font=fonts["tiny"], anchor="lm")
        painter.text((x + 16, y + 50), f"{score}", fill=(246, 250, 255, alpha), font=fonts["score"], anchor="lm")
        painter.text((x + 62, y + 50), "/100", fill=(139, 162, 180, alpha), font=fonts["tiny"], anchor="lm")
        painter.rounded((x + 112, y + 47, x + card_w - 16, y + 55), radius=4, fill=(41, 57, 72, alpha))
        painter.rounded((x + 112, y + 47, x + 112 + (card_w - 128) * score / 100, y + 55), radius=4, fill=_hex_to_rgba(color, alpha))

    summary = (
        "plausible frames, failed dynamics"
        if mode == "bad"
        else "prediction follows actions and contact"
    )
    summary_color = "#ff6b5f" if mode == "bad" else "#41d38a"
    painter.text((82, y + 76), summary, fill=_hex_to_rgba(summary_color, alpha), font=fonts["small"])


def _draw_footer_timeline(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    progress: float,
    mode: str,
) -> None:
    x1, y1, x2, y2 = 52, 678, 1228, 690
    color = "#ff6b5f" if mode == "bad" else "#41d38a"
    painter.rounded((x1, y1, x2, y2), radius=6, fill=(38, 53, 68, 210))
    painter.rounded((x1, y1, x1 + (x2 - x1) * progress, y2), radius=6, fill=_hex_to_rgba(color, 225))
    painter.text((52, 658), "compare predictions against ground truth, action logs, and contact timing", fill=(150, 171, 188, 210), font=fonts["tiny"])


def _draw_small_evidence(
    painter: Painter,
    fonts: dict[str, ImageFont.ImageFont],
    origin: tuple[float, float],
    text: str,
    color: str,
    alpha: int,
) -> None:
    x, y = origin
    painter.rounded((x, y, x + 166, y + 34), radius=17, fill=_hex_to_rgba(color, int(45 * alpha / 255)), outline=_hex_to_rgba(color, int(160 * alpha / 255)))
    painter.text((x + 83, y + 17), text, fill=(235, 244, 250, alpha), font=fonts["tiny"], anchor="mm")


def _draw_mini_simulator(
    painter: Painter,
    box: tuple[float, float, float, float],
    progress: float,
    alpha: float,
) -> None:
    x1, y1, x2, y2 = box
    painter.rounded((x1 + 10, y1 + 16, x2 + 10, y2 + 16), radius=28, fill=(0, 0, 0, int(110 * alpha)))
    painter.rounded(box, radius=28, fill=(10, 20, 31, int(230 * alpha)), outline=(79, 115, 142, int(125 * alpha)))
    _draw_sim_floor(painter, (x1 + 22, y1 + 22, x2 - 22, y2 - 22), "good", progress)
    robot, cube, _ = _state_for_mode((x1 + 22, y1 + 22, x2 - 22, y2 - 22), "good", progress)
    _draw_trajectory(painter, (x1 + 22, y1 + 22, x2 - 22, y2 - 22), "good", progress, "robot")
    _draw_robot(painter, robot[0], robot[1], "right")
    _draw_cube(painter, cube[0], cube[1])


def _state_for_mode(
    box: tuple[float, float, float, float],
    mode: str,
    progress: float,
) -> tuple[tuple[float, float], tuple[float, float], bool]:
    x1, y1, x2, y2 = box
    lane_y = _lerp_raw(y1 + 178, y2 - 70, 0.28)
    start = x1 + 86
    cube_start = x1 + (x2 - x1) * 0.72
    robot_target = x1 + (x2 - x1) * 0.61
    cube_push = max(0.0, progress - 0.72) / 0.28

    if mode in {"ground_truth", "good"}:
        robot_x = _lerp_raw(start, robot_target, ease_in_out(progress))
        cube_x = cube_start + ease_in_out(cube_push) * 78
        if mode == "good":
            robot_x += math.sin(progress * math.pi * 3.0) * 2.0
        return (robot_x, lane_y), (cube_x, lane_y), True

    robot_x = _lerp_raw(start, x1 + 54, ease_in_out(progress))
    robot_y = lane_y + math.sin(progress * math.pi * 3) * 3
    cube_x = cube_start + ease_in_out(min(1.0, max(0.0, progress - 0.13) / 0.72)) * 88
    visible = not (0.49 < progress < 0.59)
    return (robot_x, robot_y), (cube_x, lane_y), visible


def _score_color(score: int, mode: str) -> str:
    if mode == "good":
        return "#41d38a"
    if score < 45:
        return "#ff6b5f"
    if score < 65:
        return "#ffb85c"
    return "#41d38a"


def _fade_edges(painter: Painter, local_t: float, duration: float, out_only: bool = False) -> None:
    if not out_only:
        fade_in = 1.0 - ease_out(min(1.0, local_t / 0.35))
        if fade_in > 0:
            painter.rectangle((0, 0, WIDTH, HEIGHT), fill=(7, 16, 25, int(210 * fade_in)))
    fade_out = ease_in(max(0.0, local_t - duration + 0.4) / 0.4)
    if fade_out > 0:
        painter.rectangle((0, 0, WIDTH, HEIGHT), fill=(7, 16, 25, int(210 * fade_out)))


def _write_mp4(frame_dir: Path, output_path: Path) -> bool:
    if _write_mp4_with_imageio(frame_dir, output_path):
        return True
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-framerate",
                    str(FPS),
                    "-i",
                    str(frame_dir / "frame_%04d.png"),
                    "-vcodec",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "21",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    print('MP4 export skipped. Install video dependencies with: python -m pip install -e ".[video]"')
    return False


def _write_mp4_with_imageio(frame_dir: Path, output_path: Path) -> bool:
    try:
        import imageio.v2 as imageio
    except Exception:
        return False

    try:
        with imageio.get_writer(output_path, fps=FPS, codec="libx264", quality=8, macro_block_size=16) as writer:
            for idx in range(FRAME_COUNT):
                writer.append_data(imageio.imread(frame_dir / f"frame_{idx:04d}.png"))
    except Exception:
        return False
    return True


def _write_gif(frame_dir: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        palette = output_path.with_suffix(".palette.png")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(frame_dir / "frame_%04d.png"),
                "-vf",
                f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff",
                str(palette),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(frame_dir / "frame_%04d.png"),
                "-i",
                str(palette),
                "-lavfi",
                f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        palette.unlink(missing_ok=True)
        return

    try:
        import imageio.v2 as imageio
    except Exception:
        _write_gif_with_pillow(frame_dir, output_path)
        return

    with imageio.get_writer(output_path, mode="I", duration=1 / GIF_FPS, loop=0) as writer:
        for idx in range(0, FRAME_COUNT, max(1, FPS // GIF_FPS)):
            frame = Image.open(frame_dir / f"frame_{idx:04d}.png").resize(
                (GIF_WIDTH, int(GIF_WIDTH * HEIGHT / WIDTH)),
                Image.Resampling.LANCZOS,
            )
            writer.append_data(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))


def _write_gif_with_pillow(frame_dir: Path, output_path: Path) -> None:
    print('GIF fallback is using Pillow. For faster export, install: python -m pip install -e ".[video]"')
    step = max(1, FPS // GIF_FPS)
    frames = [
        Image.open(frame_dir / f"frame_{idx:04d}.png")
        .resize((GIF_WIDTH, int(GIF_WIDTH * HEIGHT / WIDTH)), Image.Resampling.LANCZOS)
        .convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        for idx in range(0, FRAME_COUNT, step)
    ]
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / GIF_FPS),
        loop=0,
        optimize=True,
    )


def _fonts() -> dict[str, ImageFont.ImageFont]:
    regular = _find_font(
        [
            "/System/Library/Fonts/Supplemental/Helvetica.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    bold = _find_font(
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    ) or regular
    mono = _find_font(
        [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    ) or regular

    def font(path: str | None, size: int) -> ImageFont.ImageFont:
        if path:
            return ImageFont.truetype(path, size=size * SCALE)
        return ImageFont.load_default()

    return {
        "hero": font(bold, 68),
        "top": font(bold, 27),
        "title": font(bold, 42),
        "subtitle": font(regular, 26),
        "statement": font(regular, 28),
        "panel": font(bold, 20),
        "body": font(regular, 18),
        "small": font(regular, 15),
        "tiny": font(regular, 12),
        "score": font(bold, 28),
        "mono": font(mono, 20),
    }


def _find_font(paths: list[str]) -> str | None:
    return next((path for path in paths if Path(path).exists()), None)


def _hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def _lerp_raw(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(t * math.pi)


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t**3


if __name__ == "__main__":
    outputs = make_demo_video()
    mp4_path = outputs["mp4"]
    gif_path = outputs["gif"]
    thumbnail_path = outputs["thumbnail"]
    gif_size = int(outputs["gif_size_bytes"]) / (1024 * 1024)
    print(f"generated MP4 path: {mp4_path} ({'written' if outputs['mp4_written'] else 'skipped'})")
    print(f"generated GIF path: {gif_path}")
    print(f"generated thumbnail path: {thumbnail_path}")
    print(f"GIF file size: {gif_size:.2f} MB")
    print(f"frame count: {outputs['frame_count']}")
    print(f"duration: {outputs['duration_seconds']} seconds")
