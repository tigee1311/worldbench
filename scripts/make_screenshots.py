"""Generate lightweight dashboard/report screenshots for the README."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "assets" / "screenshots"


def make_screenshots(output_dir: str | Path = OUTPUT_DIR) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    dashboard = output / "dashboard.png"
    report = output / "report.png"
    _draw_dashboard().save(dashboard)
    _draw_report().save(report)
    return {"dashboard": dashboard, "report": report}


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_dashboard() -> Image.Image:
    image = Image.new("RGB", (1440, 920), "#f5f7fb")
    draw = ImageDraw.Draw(image)
    title = _font(36)
    h2 = _font(24)
    body = _font(18)
    small = _font(14)

    draw.rectangle((0, 0, 1440, 104), fill="#101820")
    draw.text((48, 28), "WorldBench Dashboard", fill="#ffffff", font=title)
    draw.text((48, 70), "Local evaluation view for robotics world-model predictions", fill="#bfd1df", font=small)

    _card(draw, (48, 136, 286, 322), "#ffffff")
    draw.text((74, 164), "Overall Score", fill="#5f6f7c", font=small)
    draw.text((74, 198), "42", fill="#182530", font=_font(72))
    draw.text((166, 240), "/100", fill="#6c7a86", font=h2)

    _card(draw, (310, 136, 1392, 322), "#ffffff")
    draw.text((338, 164), "Main failure", fill="#182530", font=h2)
    draw.text(
        (338, 210),
        "bad_model produces plausible frames but violates robot action/contact dynamics.",
        fill="#536371",
        font=body,
    )

    metrics = [
        ("Visual similarity", 62, "#2563eb"),
        ("Action consistency", 31, "#d94c45"),
        ("Temporal stability", 48, "#b7791f"),
        ("Object permanence", 55, "#b7791f"),
        ("Contact realism", 20, "#d94c45"),
    ]
    x = 48
    for name, score, color in metrics:
        _card(draw, (x, 350, x + 254, 500), "#ffffff")
        draw.text((x + 20, 376), name, fill="#5f6f7c", font=small)
        draw.text((x + 20, 414), f"{score}/100", fill="#17232d", font=h2)
        draw.rounded_rectangle((x + 20, 462, x + 218, 472), radius=5, fill="#e7edf3")
        draw.rounded_rectangle((x + 20, 462, x + 20 + int(1.98 * score), 472), radius=5, fill=color)
        x += 272

    _card(draw, (48, 534, 704, 850), "#ffffff")
    draw.text((76, 562), "Frame comparison", fill="#182530", font=h2)
    _mini_world(draw, 76, 610, "Ground truth", "right")
    _mini_world(draw, 388, 610, "Prediction", "left")

    _card(draw, (736, 534, 1392, 850), "#ffffff")
    draw.text((764, 562), "Issue list", fill="#182530", font=h2)
    issues = [
        ("Critical", "move_right actions did not produce rightward motion"),
        ("Critical", "object moved before contact"),
        ("Warning", "object disappeared briefly"),
        ("Warning", "temporal flicker detected around t=6"),
    ]
    y = 612
    for severity, text in issues:
        color = "#d94c45" if severity == "Critical" else "#b7791f"
        fill = "#fff1f1" if severity == "Critical" else "#fff8e7"
        draw.rounded_rectangle((764, y, 1360, y + 46), radius=6, fill=fill)
        draw.rectangle((764, y, 770, y + 46), fill=color)
        draw.text((786, y + 13), f"{severity}: {text}", fill="#22313d", font=small)
        y += 58
    return image


def _draw_report() -> Image.Image:
    image = Image.new("RGB", (1440, 920), "#eef2f6")
    draw = ImageDraw.Draw(image)
    title = _font(34)
    h2 = _font(22)
    body = _font(17)
    small = _font(14)

    _card(draw, (270, 58, 1170, 862), "#ffffff")
    draw.text((330, 110), "WorldBench Evaluation Report", fill="#13212b", font=title)
    draw.text((330, 170), "Overall Score: 42/100", fill="#d94c45", font=h2)
    draw.text((330, 220), "Main failure: visually plausible but action-inconsistent", fill="#465663", font=body)

    draw.text((330, 292), "Metric Scores", fill="#13212b", font=h2)
    rows = [
        ("Visual Similarity", "62/100"),
        ("Action Consistency", "31/100"),
        ("Temporal Stability", "48/100"),
        ("Object Permanence", "55/100"),
        ("Contact Realism", "20/100"),
    ]
    y = 338
    for name, score in rows:
        draw.line((330, y - 12, 1110, y - 12), fill="#dce4ec", width=1)
        draw.text((330, y), name, fill="#22313d", font=body)
        draw.text((990, y), score, fill="#22313d", font=body)
        y += 44

    draw.text((330, 604), "Evidence", fill="#13212b", font=h2)
    evidence = [
        "move_right actions did not produce rightward motion",
        "object moved before contact",
        "object disappeared briefly",
        "temporal flicker detected",
    ]
    y = 652
    for item in evidence:
        draw.text((350, y), f"- {item}", fill="#465663", font=body)
        y += 34

    draw.text((330, 800), "Generated locally from .worldbench/runs/latest/result.json", fill="#6b7b88", font=small)
    return image


def _mini_world(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, direction: str) -> None:
    draw.text((x, y), label, fill="#5f6f7c", font=_font(14))
    draw.rounded_rectangle((x, y + 30, x + 270, y + 190), radius=8, fill="#101820")
    for gx in range(x + 20, x + 270, 36):
        draw.line((gx, y + 30, gx, y + 190), fill="#22313d", width=1)
    for gy in range(y + 50, y + 190, 36):
        draw.line((x, gy, x + 270, gy), fill="#22313d", width=1)
    if direction == "right":
        robot = (x + 96, y + 116)
        obj = (x + 182, y + 116)
    else:
        robot = (x + 72, y + 116)
        obj = (x + 202, y + 116)
    draw.line((*robot, *obj), fill="#435463", width=3)
    rx, ry = robot
    ox, oy = obj
    draw.ellipse((rx - 16, ry - 16, rx + 16, ry + 16), fill="#e44d42", outline="#ffc3bc", width=2)
    draw.rectangle((ox - 18, oy - 18, ox + 18, oy + 18), fill="#2ecc71", outline="#b7ffd0", width=2)
    arrow = "->" if direction == "right" else "<-"
    draw.text((x + 112, y + 150), arrow, fill="#bfd1df", font=_font(22))


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
    draw.rounded_rectangle(box, radius=10, fill=fill, outline="#d9e2ea", width=1)


if __name__ == "__main__":
    outputs = make_screenshots()
    for name, path in outputs.items():
        print(f"{name}: {path}")
