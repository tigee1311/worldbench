"""Generate README dashboard and report screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "assets" / "screenshots"
WIDTH = 1440
HEIGHT = 920
SCALE = 2


class Canvas:
    """Small scaled drawing helper for anti-aliased screenshots."""

    def __init__(self) -> None:
        self.image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), "#071019")
        self.draw = ImageDraw.Draw(self.image, "RGBA")

    def xy(self, values: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(int(round(value * SCALE)) for value in values)

    def rounded(
        self,
        box: tuple[float, float, float, float],
        radius: float,
        fill: str | tuple[int, int, int, int],
        outline: str | tuple[int, int, int, int] | None = None,
        width: float = 1,
    ) -> None:
        self.draw.rounded_rectangle(
            self.xy(box),
            radius=int(radius * SCALE),
            fill=fill,
            outline=outline,
            width=max(1, int(width * SCALE)),
        )

    def line(self, xy: tuple[float, ...], fill: str | tuple[int, int, int, int], width: float = 1) -> None:
        self.draw.line(self.xy(xy), fill=fill, width=max(1, int(width * SCALE)))

    def text(
        self,
        xy: tuple[float, float],
        text: str,
        fill: str | tuple[int, int, int, int],
        font: ImageFont.ImageFont,
        anchor: str | None = None,
    ) -> None:
        self.draw.text(self.xy(xy), text, fill=fill, font=font, anchor=anchor)

    def ellipse(
        self,
        box: tuple[float, float, float, float],
        fill: str | tuple[int, int, int, int],
        outline: str | tuple[int, int, int, int] | None = None,
        width: float = 1,
    ) -> None:
        self.draw.ellipse(self.xy(box), fill=fill, outline=outline, width=max(1, int(width * SCALE)))

    def polygon(self, points: list[tuple[float, float]], fill: str | tuple[int, int, int, int]) -> None:
        self.draw.polygon([self.xy(point) for point in points], fill=fill)

    def output(self) -> Image.Image:
        return self.image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def make_screenshots(output_dir: str | Path = OUTPUT_DIR) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    dashboard = output / "dashboard.png"
    report = output / "report.png"
    _draw_dashboard().save(dashboard)
    _draw_report().save(report)
    return {"dashboard": dashboard, "report": report}


def _draw_dashboard() -> Image.Image:
    canvas = Canvas()
    fonts = _fonts()
    _background(canvas)

    _top_bar(canvas, fonts, "WorldBench Dashboard", "Local robotics world-model evaluation")
    _score_summary(canvas, fonts)
    _metric_row(canvas, fonts)
    _frame_comparison(canvas, fonts)
    _issue_panel(canvas, fonts)
    _raw_json_panel(canvas, fonts)
    return canvas.output()


def _draw_report() -> Image.Image:
    canvas = Canvas()
    fonts = _fonts()
    _background(canvas)
    _top_bar(canvas, fonts, "WorldBench Report", "Markdown export from .worldbench/runs/latest/result.json")

    canvas.rounded((252, 116, 1188, 840), 24, fill=(9, 18, 29, 238), outline=(64, 96, 124, 150), width=1.4)
    canvas.text((316, 176), "WorldBench Evaluation Report", "#f6faff", fonts["hero"])
    canvas.text((316, 234), "Overall Score", "#91a9bb", fonts["small"])
    canvas.text((316, 294), "42", "#ff6b5f", fonts["score_big"])
    canvas.text((410, 282), "/100", "#91a9bb", fonts["panel"])
    canvas.rounded((532, 234, 1112, 318), 18, fill=(15, 28, 42, 235), outline=(74, 108, 134, 120))
    canvas.text((562, 266), "Main failure", "#f6faff", fonts["panel"])
    canvas.text((562, 296), "Visually plausible, but action-inconsistent.", "#bed2df", fonts["body"])

    rows = [
        ("Visual similarity", "57.8", "#ffb85c"),
        ("Action consistency", "32.8", "#ff6b5f"),
        ("Temporal stability", "44.2", "#ffb85c"),
        ("Object permanence", "60.8", "#ffb85c"),
        ("Contact realism", "0.0", "#ff6b5f"),
    ]
    canvas.text((316, 390), "Metric scores", "#f6faff", fonts["panel"])
    y = 438
    for name, score, color in rows:
        canvas.line((316, y - 16, 1112, y - 16), fill=(62, 87, 109, 150), width=1)
        canvas.text((316, y), name, "#dce8f1", fonts["body"], anchor="lm")
        canvas.text((1016, y), f"{score}/100", "#dce8f1", fonts["body"], anchor="rm")
        canvas.rounded((1034, y - 5, 1112, y + 3), 4, fill=(39, 56, 72, 255))
        canvas.rounded((1034, y - 5, 1034 + float(score) * 0.78, y + 3), 4, fill=color)
        y += 52

    canvas.text((316, 708), "Evidence", "#f6faff", fonts["panel"])
    evidence = [
        "move_right actions did not produce rightward visual motion",
        "object moved before contact",
        "object flicker detected in the prediction window",
    ]
    for idx, item in enumerate(evidence):
        yy = 754 + idx * 34
        canvas.ellipse((316, yy - 4, 324, yy + 4), fill="#ff6b5f")
        canvas.text((342, yy), item, "#bed2df", fonts["body"], anchor="lm")

    _mini_sim(canvas, (852, 684, 1152, 814), mode="bad")
    return canvas.output()


def _background(canvas: Canvas) -> None:
    for y in range(HEIGHT):
        mix = y / HEIGHT
        r = int(6 + 6 * mix)
        g = int(14 + 10 * mix)
        b = int(24 + 12 * mix)
        canvas.line((0, y, WIDTH, y), fill=(r, g, b, 255), width=1)
    canvas.ellipse((-180, -130, 360, 360), fill=(35, 92, 122, 42))
    canvas.ellipse((1010, 560, 1630, 1140), fill=(29, 135, 91, 34))
    for x in range(0, WIDTH, 64):
        canvas.line((x, 110, x + 220, HEIGHT), fill=(64, 92, 118, 16), width=1)
    for y in range(126, HEIGHT, 56):
        canvas.line((0, y, WIDTH, y), fill=(64, 92, 118, 12), width=1)


def _top_bar(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont], title: str, subtitle: str) -> None:
    canvas.rounded((48, 34, 1392, 96), 20, fill=(10, 20, 32, 230), outline=(64, 96, 124, 135))
    canvas.text((78, 65), title, "#f6faff", fonts["top"], anchor="lm")
    canvas.text((430, 65), subtitle, "#91a9bb", fonts["body"], anchor="lm")
    canvas.rounded((1188, 52, 1358, 76), 12, fill=(65, 211, 138, 42), outline=(65, 211, 138, 160))
    canvas.text((1273, 64), "local run", "#dff7eb", fonts["tiny"], anchor="mm")


def _score_summary(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont]) -> None:
    canvas.rounded((48, 128, 300, 326), 22, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
    canvas.text((78, 166), "Overall score", "#91a9bb", fonts["small"])
    canvas.text((78, 218), "42", "#ff6b5f", fonts["score_big"])
    canvas.text((170, 236), "/100", "#91a9bb", fonts["panel"])
    canvas.rounded((78, 298, 252, 308), 5, fill=(39, 56, 72, 255))
    canvas.rounded((78, 298, 151, 308), 5, fill="#ff6b5f")

    canvas.rounded((328, 128, 1392, 326), 22, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
    canvas.text((362, 176), "Main failure", "#f6faff", fonts["panel"])
    canvas.text((362, 226), "bad_model produces plausible frames but violates robot action/contact dynamics.", "#bed2df", fonts["body"])
    _chip(canvas, fonts, (362, 270), "Action mismatch", "#ff6b5f")
    _chip(canvas, fonts, (538, 270), "Pre-contact motion", "#ffb85c")
    _chip(canvas, fonts, (740, 270), "Object flicker", "#ff6b5f")


def _metric_row(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont]) -> None:
    metrics = [
        ("Visual similarity", 57.8, "#ffb85c"),
        ("Action consistency", 32.8, "#ff6b5f"),
        ("Temporal stability", 44.2, "#ffb85c"),
        ("Object permanence", 60.8, "#ffb85c"),
        ("Contact realism", 0.0, "#ff6b5f"),
    ]
    x = 48
    for name, score, color in metrics:
        canvas.rounded((x, 354, x + 252, 492), 18, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
        canvas.text((x + 22, 390), name, "#91a9bb", fonts["small"])
        canvas.text((x + 22, 416), f"{score:.1f}", "#f6faff", fonts["metric"])
        canvas.text((x + 94, 430), "/100", "#91a9bb", fonts["tiny"])
        canvas.rounded((x + 22, 466, x + 222, 474), 4, fill=(39, 56, 72, 255))
        canvas.rounded((x + 22, 466, x + 22 + score * 2, 474), 4, fill=color)
        x += 272


def _frame_comparison(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont]) -> None:
    canvas.rounded((48, 526, 706, 842), 22, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
    canvas.text((78, 570), "Frame comparison", "#f6faff", fonts["panel"])
    canvas.text((78, 604), "Ground truth vs prediction", "#91a9bb", fonts["small"])
    _mini_sim(canvas, (78, 636, 366, 802), mode="ground_truth")
    _mini_sim(canvas, (388, 636, 676, 802), mode="bad")
    canvas.text((222, 824), "ground truth", "#91a9bb", fonts["tiny"], anchor="mm")
    canvas.text((532, 824), "prediction", "#91a9bb", fonts["tiny"], anchor="mm")


def _issue_panel(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont]) -> None:
    canvas.rounded((736, 526, 1392, 726), 22, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
    canvas.text((766, 570), "Issue list", "#f6faff", fonts["panel"])
    issues = [
        ("critical", "move_right actions did not produce rightward motion", "#ff6b5f"),
        ("critical", "object moved before contact", "#ff6b5f"),
        ("warning", "object disappeared briefly", "#ffb85c"),
    ]
    y = 610
    for severity, text, color in issues:
        canvas.rounded((766, y, 1362, y + 34), 10, fill=(16, 29, 42, 235), outline=(64, 96, 124, 100))
        canvas.rounded((766, y, 772, y + 34), 3, fill=color)
        canvas.text((790, y + 17), severity, color, fonts["tiny"], anchor="lm")
        canvas.text((874, y + 17), text, "#dce8f1", fonts["tiny"], anchor="lm")
        y += 46


def _raw_json_panel(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont]) -> None:
    canvas.rounded((736, 752, 1392, 842), 22, fill=(10, 20, 31, 238), outline=(64, 96, 124, 145))
    canvas.text((766, 790), "Raw JSON", "#f6faff", fonts["panel"])
    canvas.text((910, 790), "{ score: 42.2, winner: \"good_model\", main_failure: \"contact_realism\" }", "#91a9bb", fonts["tiny"], anchor="lm")


def _mini_sim(canvas: Canvas, box: tuple[int, int, int, int], mode: str) -> None:
    x1, y1, x2, y2 = box
    canvas.rounded(box, 14, fill=(7, 16, 25, 255), outline=(50, 78, 102, 150))
    floor = [(x1 + 28, y2 - 20), (x2 - 28, y2 - 20), (x2 - 70, y1 + 34), (x1 + 70, y1 + 34)]
    canvas.polygon(floor, fill=(15, 31, 45, 255))
    for i in range(7):
        q = i / 6
        y = y2 - 20 - q**1.5 * (y2 - y1 - 54)
        canvas.line((x1 + 28 + q * 42, y, x2 - 28 - q * 42, y), fill=(80, 118, 147, 42))
    for i in range(8):
        q = i / 7
        canvas.line(
            (x1 + 28 + (x2 - x1 - 56) * q, y2 - 20, x1 + 70 + (x2 - x1 - 140) * q, y1 + 34),
            fill=(80, 118, 147, 32),
        )

    if mode == "ground_truth":
        robot = (x1 + 106, y1 + 104)
        cube = (x1 + 200, y1 + 104)
        heading = "right"
    else:
        robot = (x1 + 82, y1 + 104)
        cube = (x1 + 224, y1 + 104)
        heading = "left"
        canvas.rounded((cube[0] - 24, cube[1] - 24, cube[0] + 24, cube[1] + 24), 6, fill=(255, 107, 95, 18), outline=(255, 107, 95, 160))
    _robot(canvas, robot, heading)
    _cube(canvas, cube)


def _robot(canvas: Canvas, robot: tuple[int, int], heading: str) -> None:
    x, y = robot
    direction = 1 if heading == "right" else -1
    canvas.ellipse((x - 44, y + 14, x + 44, y + 32), fill=(0, 0, 0, 85))
    canvas.rounded((x - 34, y - 22, x + 34, y + 18), 13, fill=(39, 75, 99, 255), outline=(132, 184, 212, 180))
    canvas.ellipse((x - 11, y - 14, x + 11, y + 8), fill=(95, 198, 235, 235), outline=(188, 239, 255, 210))
    canvas.line((x + direction * 32, y - 3, x + direction * 58, y - 3), fill=(242, 181, 91, 235), width=5)
    canvas.line((x + direction * 58, y - 3, x + direction * 70, y - 12), fill=(242, 181, 91, 235), width=3)
    canvas.line((x + direction * 58, y - 3, x + direction * 70, y + 6), fill=(242, 181, 91, 235), width=3)
    canvas.rounded((x - 30, y + 16, x - 12, y + 26), 5, fill=(7, 16, 25, 255))
    canvas.rounded((x + 12, y + 16, x + 30, y + 26), 5, fill=(7, 16, 25, 255))


def _cube(canvas: Canvas, cube: tuple[int, int]) -> None:
    x, y = cube
    canvas.ellipse((x - 30, y + 20, x + 42, y + 34), fill=(0, 0, 0, 80))
    canvas.polygon([(x - 20, y - 20), (x - 10, y - 30), (x + 30, y - 30), (x + 20, y - 20)], fill="#5beb94")
    canvas.polygon([(x + 20, y - 20), (x + 30, y - 30), (x + 30, y + 10), (x + 20, y + 20)], fill="#1e9456")
    canvas.polygon([(x - 20, y - 20), (x + 20, y - 20), (x + 20, y + 20), (x - 20, y + 20)], fill="#37cc73")


def _chip(canvas: Canvas, fonts: dict[str, ImageFont.ImageFont], origin: tuple[int, int], text: str, color: str) -> None:
    x, y = origin
    width = 144 if len(text) < 15 else 184
    canvas.rounded((x, y, x + width, y + 30), 15, fill=_hex(color, 42), outline=_hex(color, 150))
    canvas.text((x + width / 2, y + 15), text, "#f6faff", fonts["tiny"], anchor="mm")


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
    draw.rounded_rectangle(box, radius=10, fill=fill, outline="#d9e2ea", width=1)


def _hex(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def _font(path: str | None, size: int) -> ImageFont.ImageFont:
    if path:
        return ImageFont.truetype(path, size=size * SCALE)
    return ImageFont.load_default()


def _find_font(paths: list[str]) -> str | None:
    return next((path for path in paths if Path(path).exists()), None)


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
    return {
        "hero": _font(bold, 34),
        "top": _font(bold, 30),
        "score_big": _font(bold, 74),
        "score": _font(bold, 44),
        "metric": _font(bold, 30),
        "panel": _font(bold, 22),
        "body": _font(regular, 18),
        "small": _font(regular, 14),
        "tiny": _font(regular, 12),
        "mono": _font(mono, 16),
    }


if __name__ == "__main__":
    outputs = make_screenshots()
    for name, path in outputs.items():
        print(f"{name}: {path}")
