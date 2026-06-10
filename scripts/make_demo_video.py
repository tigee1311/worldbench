"""Generate the WorldBench README demo video, GIF, and thumbnail.

The script is intentionally self-contained: it draws synthetic robot rollout
frames programmatically and writes assets under assets/demo/.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1280
HEIGHT = 720
FPS = 10
DURATION_SECONDS = 26
FRAME_COUNT = FPS * DURATION_SECONDS

BAD_SCORES = {
    "Overall": 42,
    "Action consistency": 31,
    "Contact realism": 20,
    "Object permanence": 55,
    "Temporal stability": 48,
}

GOOD_SCORES = {
    "Overall": 88,
    "Action consistency": 91,
    "Contact realism": 84,
    "Object permanence": 95,
    "Temporal stability": 86,
}


def make_demo_video(output_dir: str | Path = "assets/demo") -> dict[str, Path]:
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
            frame.save(frame_dir / f"frame_{idx:04d}.png")
            if idx == 0:
                frame.save(thumbnail_path)

        _write_mp4(frame_dir, mp4_path)
        _write_gif(frame_dir, gif_path)

    return {"mp4": mp4_path, "gif": gif_path, "thumbnail": thumbnail_path}


def render_frame(idx: int) -> Image.Image:
    t = idx / FPS
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f5f8fb")
    draw = ImageDraw.Draw(image)
    fonts = _fonts()

    if t >= 22:
        _draw_outro(draw, fonts, t)
        return image

    phase = "bad" if t < 11 else "good"
    phase_t = t if phase == "bad" else t - 11
    progress = min(1.0, phase_t / 9.5)
    scores = BAD_SCORES if phase == "bad" else GOOD_SCORES

    _draw_header(draw, fonts, phase)
    _draw_scene_panel(
        draw,
        fonts,
        box=(54, 132, 604, 492),
        title="Ground truth future",
        phase="ground_truth",
        progress=progress,
        flicker=False,
    )
    _draw_scene_panel(
        draw,
        fonts,
        box=(676, 132, 1226, 492),
        title="World-model prediction",
        phase=phase,
        progress=progress,
        flicker=phase == "bad" and 0.46 < progress < 0.56,
    )
    _draw_scores(draw, fonts, scores, phase)
    _draw_timeline(draw, fonts, progress, phase)
    return image


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], phase: str) -> None:
    draw.rectangle((0, 0, WIDTH, 96), fill="#101820")
    draw.text((54, 25), "WorldBench", fill="#ffffff", font=fonts["title"])
    draw.text((262, 34), "robotics world-model evaluation", fill="#b7c8d8", font=fonts["body"])
    pill = "bad model: plausible video, broken control" if phase == "bad" else "good model: action-consistent rollout"
    color = "#d94c45" if phase == "bad" else "#198f5d"
    draw.rounded_rectangle((842, 24, 1226, 64), radius=18, fill=color)
    draw.text((866, 33), pill, fill="#ffffff", font=fonts["small"])


def _draw_scene_panel(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    title: str,
    phase: str,
    progress: float,
    flicker: bool,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=10, fill="#ffffff", outline="#d8e1ea", width=2)
    draw.text((x1 + 20, y1 + 16), title, fill="#14212b", font=fonts["panel"])
    world = (x1 + 22, y1 + 64, x2 - 22, y2 - 28)
    _draw_world(draw, fonts, world, phase, progress, flicker)


def _draw_world(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    box: tuple[int, int, int, int],
    phase: str,
    progress: float,
    flicker: bool,
) -> None:
    x1, y1, x2, y2 = box
    fill = "#17212b" if not flicker else "#421d1d"
    draw.rounded_rectangle(box, radius=8, fill=fill)
    for x in range(x1 + 20, x2, 42):
        draw.line((x, y1, x, y2), fill="#253646", width=1)
    for y in range(y1 + 20, y2, 42):
        draw.line((x1, y, x2, y), fill="#253646", width=1)

    gt_robot_x = _lerp(x1 + 90, x1 + 318, progress)
    gt_robot_y = y1 + 164
    gt_cube_x = x1 + 374 + max(0.0, progress - 0.72) * 180
    gt_cube_y = y1 + 164

    if phase == "bad":
        robot_x = _lerp(x1 + 90, x1 + 28, progress)
        robot_y = y1 + 164
        cube_x = x1 + 374 + progress * 86
        cube_y = y1 + 164
        visible = not (0.45 < progress < 0.56)
        warnings = _bad_warnings(progress)
    else:
        robot_x = gt_robot_x
        robot_y = gt_robot_y
        cube_x = gt_cube_x
        cube_y = gt_cube_y
        visible = True
        warnings = ["action aligned", "contact after reach", "object persistent"] if progress > 0.7 else ["tracking rollout"]

    if phase == "ground_truth":
        robot_x = gt_robot_x
        robot_y = gt_robot_y
        cube_x = gt_cube_x
        cube_y = gt_cube_y
        visible = True
        warnings = ["logged actions", "state-aligned future"]

    _draw_robot(draw, robot_x, robot_y)
    if visible:
        _draw_cube(draw, cube_x, cube_y)
    else:
        draw.rounded_rectangle((cube_x - 26, cube_y - 26, cube_x + 26, cube_y + 26), radius=5, outline="#d94c45", width=4)
        draw.line((cube_x - 30, cube_y - 30, cube_x + 30, cube_y + 30), fill="#d94c45", width=4)
        draw.line((cube_x + 30, cube_y - 30, cube_x - 30, cube_y + 30), fill="#d94c45", width=4)

    draw.line((x1 + 52, y2 - 44, x2 - 52, y2 - 44), fill="#5f7487", width=3)
    draw.text((x1 + 52, y2 - 32), "action: move_right -> contact -> push", fill="#b7c8d8", font=fonts["small"])

    for idx, warning in enumerate(warnings[:3]):
        color = "#d94c45" if phase == "bad" else "#198f5d"
        yy = y1 + 16 + idx * 30
        draw.rounded_rectangle((x2 - 226, yy, x2 - 18, yy + 22), radius=11, fill=color)
        draw.text((x2 - 214, yy + 4), warning, fill="#ffffff", font=fonts["tiny"])


def _draw_robot(draw: ImageDraw.ImageDraw, x: float, y: float) -> None:
    draw.line((x - 46, y, x + 12, y), fill="#f5bd5b", width=9)
    draw.ellipse((x - 24, y - 24, x + 24, y + 24), fill="#e74c3c", outline="#ffd2c8", width=4)
    draw.rectangle((x + 18, y - 8, x + 44, y + 8), fill="#f5bd5b")


def _draw_cube(draw: ImageDraw.ImageDraw, x: float, y: float) -> None:
    draw.rounded_rectangle((x - 28, y - 28, x + 28, y + 28), radius=6, fill="#2ecc71", outline="#b5ffd0", width=4)
    draw.line((x - 28, y, x + 28, y), fill="#167d49", width=2)
    draw.line((x, y - 28, x, y + 28), fill="#167d49", width=2)


def _draw_scores(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    scores: dict[str, int],
    phase: str,
) -> None:
    box = (54, 520, 1226, 646)
    draw.rounded_rectangle(box, radius=10, fill="#ffffff", outline="#d8e1ea", width=2)
    draw.text((76, 542), "WorldBench scores", fill="#14212b", font=fonts["panel"])
    draw.text((76, 574), "control-aware metrics", fill="#617282", font=fonts["small"])

    names = list(scores)
    start_x = 332
    card_w = 158
    for idx, name in enumerate(names):
        score = scores[name]
        x = start_x + idx * (card_w + 12)
        y = 536
        color = "#198f5d" if score >= 80 else "#b7791f" if score >= 55 else "#d94c45"
        draw.rounded_rectangle((x, y, x + card_w, y + 86), radius=8, fill="#f7fafc", outline="#e0e7ef")
        draw.text((x + 12, y + 12), name, fill="#617282", font=fonts["tiny"])
        draw.text((x + 12, y + 37), f"{score}/100", fill="#14212b", font=fonts["score"])
        draw.rounded_rectangle((x + 12, y + 72, x + card_w - 12, y + 78), radius=3, fill="#e8edf3")
        draw.rounded_rectangle((x + 12, y + 72, x + 12 + (card_w - 24) * score / 100, y + 78), radius=3, fill=color)

    label = "bad model failure profile" if phase == "bad" else "good model passes core checks"
    draw.text((76, 612), label, fill="#d94c45" if phase == "bad" else "#198f5d", font=fonts["small"])


def _draw_timeline(
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
    progress: float,
    phase: str,
) -> None:
    x1, y1, x2, y2 = 54, 666, 1226, 690
    draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill="#e7edf4")
    fill = "#d94c45" if phase == "bad" else "#198f5d"
    draw.rounded_rectangle((x1, y1, x1 + (x2 - x1) * progress, y2), radius=10, fill=fill)
    draw.text((54, 696), "evaluate generated futures against action logs and simple physical constraints", fill="#617282", font=fonts["tiny"])


def _draw_outro(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], t: float) -> None:
    del t
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#101820")
    draw.text((96, 120), "WorldBench", fill="#ffffff", font=fonts["hero"])
    draw.text((100, 210), "Not another world model. The test suite for world models.", fill="#c9d8e6", font=fonts["subtitle"])
    commands = ["worldbench demo", "worldbench eval", "worldbench dashboard"]
    for idx, command in enumerate(commands):
        y = 320 + idx * 62
        draw.rounded_rectangle((104, y, 510, y + 42), radius=8, fill="#172736", outline="#355168")
        draw.text((128, y + 10), command, fill="#ffffff", font=fonts["mono"])
    draw.text((740, 350), "Action consistency", fill="#ffffff", font=fonts["panel"])
    draw.text((740, 395), "Contact realism", fill="#ffffff", font=fonts["panel"])
    draw.text((740, 440), "Object permanence", fill="#ffffff", font=fonts["panel"])
    draw.text((740, 485), "Temporal stability", fill="#ffffff", font=fonts["panel"])


def _bad_warnings(progress: float) -> list[str]:
    warnings = ["Action mismatch"]
    if progress > 0.2:
        warnings.append("Object moved before contact")
    if progress > 0.45:
        warnings.append("Object disappeared")
    return warnings


def _write_mp4(frame_dir: Path, output_path: Path) -> None:
    if _write_mp4_with_imageio(frame_dir, output_path):
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "Could not create MP4. Install the video extra with `pip install -e .[video]` "
            "or install ffmpeg and rerun `python scripts/make_demo_video.py`."
        )
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
            "24",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _write_mp4_with_imageio(frame_dir: Path, output_path: Path) -> bool:
    try:
        import imageio.v2 as imageio
    except Exception:
        return False

    writer = imageio.get_writer(output_path, fps=FPS, codec="libx264", quality=8)
    try:
        for idx in range(FRAME_COUNT):
            writer.append_data(imageio.imread(frame_dir / f"frame_{idx:04d}.png"))
    finally:
        writer.close()
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
                "fps=10,scale=960:-1:flags=lanczos,palettegen",
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
                "fps=10,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        palette.unlink(missing_ok=True)
        return

    frames = [Image.open(frame_dir / f"frame_{idx:04d}.png").resize((960, 540)) for idx in range(FRAME_COUNT)]
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )


def _fonts() -> dict[str, ImageFont.ImageFont]:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font_path = next((path for path in candidates if Path(path).exists()), None)

    def font(size: int) -> ImageFont.ImageFont:
        if font_path:
            return ImageFont.truetype(font_path, size=size)
        return ImageFont.load_default()

    return {
        "hero": font(74),
        "title": font(38),
        "subtitle": font(30),
        "panel": font(24),
        "body": font(20),
        "small": font(16),
        "tiny": font(13),
        "score": font(26),
        "mono": font(24),
    }


def _lerp(a: float, b: float, t: float) -> float:
    eased = 0.5 - 0.5 * math.cos(max(0.0, min(1.0, t)) * math.pi)
    return a + (b - a) * eased


if __name__ == "__main__":
    outputs = make_demo_video()
    for label, path in outputs.items():
        print(f"{label}: {path}")
