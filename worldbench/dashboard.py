"""Dependency-free local dashboard server for WorldBench."""

from __future__ import annotations

import html
import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from worldbench.dataset import load_dataset
from worldbench.runners.comparator import load_result
from worldbench.runners.evaluator import EvaluationRunner, resolve_prediction_frames
from worldbench.schemas import EvaluationResult


def launch_dashboard(
    target: str | Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Launch a small local HTML dashboard for a result file or dataset."""

    result = load_result_or_evaluate(Path(target))
    frame_index = build_frame_index(result)
    html_payload = build_dashboard_html(result, frame_index)
    result_json = json.dumps(result.to_dict(), indent=2)

    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_text(html_payload, "text/html; charset=utf-8")
                return
            if parsed.path == "/result.json":
                self._send_text(result_json, "application/json; charset=utf-8")
                return
            if parsed.path == "/frame":
                self._send_frame(parsed.query)
                return
            if parsed.path == "/healthz":
                self._send_text("ok", "text/plain; charset=utf-8")
                return
            self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send_text(self, payload: str, content_type: str) -> None:
            encoded = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_frame(self, query: str) -> None:
            params = parse_qs(query)
            episode = params.get("episode", [""])[0]
            kind = params.get("kind", [""])[0]
            try:
                idx = int(params.get("idx", ["0"])[0])
            except ValueError:
                self.send_error(400, "Invalid frame index")
                return

            path = frame_index.get(episode, {}).get(kind, [])
            if idx < 0 or idx >= len(path):
                self.send_error(404, "Frame not found")
                return

            frame_path = path[idx]
            if not frame_path.is_file():
                self.send_error(404, "Frame not found")
                return

            payload = frame_path.read_bytes()
            content_type = mimetypes.guess_type(frame_path.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    try:
        server = ThreadingHTTPServer((host, port), DashboardHandler)
    except OSError as exc:
        raise RuntimeError(f"Could not start dashboard on {host}:{port}: {exc}") from exc
    url = f"http://{host}:{server.server_port}"
    print(f"WorldBench dashboard running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping WorldBench dashboard.")
    finally:
        server.server_close()


def load_result_or_evaluate(path: Path) -> EvaluationResult:
    if path.is_file() or (path.is_dir() and (path / "result.json").is_file()):
        return load_result(path)
    return EvaluationRunner(path).run()


def build_frame_index(result: EvaluationResult) -> dict[str, dict[str, list[Path]]]:
    try:
        dataset = load_dataset(result.dataset_path)
    except Exception:  # noqa: BLE001
        return {}

    predictions_root = Path(result.predictions_path) if result.predictions_path else None
    index: dict[str, dict[str, list[Path]]] = {}
    for episode in dataset.episodes:
        predictions = resolve_prediction_frames(episode, predictions_root)
        frame_count = min(len(episode.frames), len(predictions))
        index[episode.name] = {
            "gt": episode.frames[:frame_count],
            "pred": predictions[:frame_count],
        }
    return index


def build_dashboard_html(result: EvaluationResult, frame_index: dict[str, dict[str, list[Path]]]) -> str:
    data = {
        "result": result.to_dict(),
        "frames": {
            episode: min(len(paths.get("gt", [])), len(paths.get("pred", [])))
            for episode, paths in frame_index.items()
        },
    }
    payload = json.dumps(data).replace("</", "<\\/")
    metric_cards = "\n".join(_metric_card(name, metric.score) for name, metric in result.metrics.items())
    episode_rows = "\n".join(_episode_row(episode) for episode in result.episodes)
    issue_items = _issue_items(result)
    timeline = _timeline_svg(result)
    raw_json = html.escape(json.dumps(result.to_dict(), indent=2))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WorldBench Dashboard</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #14212b;
      --muted: #617282;
      --line: #d8e1ea;
      --red: #d94c45;
      --green: #198f5d;
      --blue: #2563eb;
      --amber: #b7791f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: #101820;
      color: #fff;
      padding: 28px 32px;
    }}
    header h1 {{ margin: 0; font-size: 32px; letter-spacing: 0; }}
    header p {{ margin: 6px 0 0; color: #bdd0dd; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 28px 24px 56px; }}
    .summary {{
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: 16px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    .score, .panel, .metric-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 32, 0.04);
    }}
    .score {{ padding: 22px; }}
    .score .label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; }}
    .score .value {{ font-size: 48px; font-weight: 760; margin-top: 4px; }}
    .score .value small {{ font-size: 18px; color: var(--muted); }}
    .main-failure {{ padding: 22px; }}
    .main-failure h2, section h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .main-failure p {{ margin: 0; color: var(--muted); font-size: 16px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(140px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric-card {{ padding: 16px; min-height: 112px; }}
    .metric-card .name {{ color: var(--muted); font-size: 13px; min-height: 38px; }}
    .metric-card .metric-score {{ font-size: 28px; font-weight: 720; margin-top: 8px; }}
    .bar {{ height: 8px; border-radius: 999px; background: #e8edf3; overflow: hidden; margin-top: 10px; }}
    .bar span {{ display: block; height: 100%; background: var(--blue); }}
    section {{ margin-top: 18px; }}
    .panel {{ padding: 18px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .issues {{ display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }}
    .issues li {{ border-left: 4px solid var(--amber); background: #fff9eb; padding: 10px 12px; border-radius: 4px; }}
    .viewer-controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }}
    select, input[type="range"] {{ accent-color: var(--blue); }}
    select {{ padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px; background: white; }}
    .frames {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .frame h3 {{ margin: 0 0 8px; font-size: 14px; color: var(--muted); }}
    .frame img {{ width: 100%; image-rendering: auto; border-radius: 6px; border: 1px solid var(--line); background: #0e141a; }}
    .chart {{ width: 100%; overflow-x: auto; }}
    details pre {{ overflow: auto; max-height: 420px; background: #0f1720; color: #dbe9f3; padding: 14px; border-radius: 6px; }}
    @media (max-width: 900px) {{
      .summary {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .frames {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>WorldBench</h1>
    <p>Not another world model. The test suite for world models.</p>
  </header>
  <main>
    <div class="summary">
      <div class="score">
        <div class="label">Overall Score</div>
        <div class="value">{result.score:.1f}<small>/100</small></div>
      </div>
      <div class="panel main-failure">
        <h2>Main Failure</h2>
        <p>{html.escape(result.main_failure)}</p>
      </div>
    </div>

    <div class="metrics">{metric_cards}</div>

    <section class="panel">
      <h2>Per-Episode Scores</h2>
      <table>
        <thead><tr><th>Episode</th><th>Score</th><th>Metric Breakdown</th></tr></thead>
        <tbody>{episode_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Metric Timeline</h2>
      <div class="chart">{timeline}</div>
    </section>

    <section class="panel">
      <h2>Issues</h2>
      <ul class="issues">{issue_items}</ul>
    </section>

    <section class="panel">
      <h2>Frame Viewer</h2>
      <div class="viewer-controls">
        <label>Episode <select id="episodeSelect"></select></label>
        <label>Frame <input id="frameSlider" type="range" min="0" max="0" value="0"></label>
        <strong id="frameLabel">000</strong>
      </div>
      <div class="frames">
        <div class="frame">
          <h3>Ground Truth</h3>
          <img id="gtFrame" alt="Ground truth frame">
        </div>
        <div class="frame">
          <h3>Prediction</h3>
          <img id="predFrame" alt="Prediction frame">
        </div>
      </div>
    </section>

    <section class="panel">
      <details>
        <summary>Raw JSON</summary>
        <pre>{raw_json}</pre>
      </details>
    </section>
  </main>
  <script type="application/json" id="worldbench-data">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('worldbench-data').textContent);
    const select = document.getElementById('episodeSelect');
    const slider = document.getElementById('frameSlider');
    const label = document.getElementById('frameLabel');
    const gt = document.getElementById('gtFrame');
    const pred = document.getElementById('predFrame');

    function pad(n) {{ return String(n).padStart(3, '0'); }}
    function episodes() {{ return Object.keys(data.frames).filter(name => data.frames[name] > 0); }}
    function update() {{
      const episode = select.value;
      const idx = Number(slider.value);
      label.textContent = pad(idx);
      gt.src = `/frame?episode=${{encodeURIComponent(episode)}}&kind=gt&idx=${{idx}}`;
      pred.src = `/frame?episode=${{encodeURIComponent(episode)}}&kind=pred&idx=${{idx}}`;
    }}
    for (const episode of episodes()) {{
      const option = document.createElement('option');
      option.value = episode;
      option.textContent = episode;
      select.appendChild(option);
    }}
    select.addEventListener('change', () => {{
      slider.max = Math.max(0, data.frames[select.value] - 1);
      slider.value = 0;
      update();
    }});
    slider.addEventListener('input', update);
    if (select.options.length > 0) {{
      slider.max = Math.max(0, data.frames[select.value] - 1);
      update();
    }}
  </script>
</body>
</html>"""


def _metric_card(name: str, score: float) -> str:
    label = html.escape(name.replace("_", " ").title())
    width = max(0, min(100, score))
    color = "#198f5d" if score >= 85 else "#b7791f" if score >= 60 else "#d94c45"
    return (
        '<div class="metric-card">'
        f'<div class="name">{label}</div>'
        f'<div class="metric-score">{score:.1f}</div>'
        f'<div class="bar"><span style="width:{width:.1f}%; background:{color}"></span></div>'
        "</div>"
    )


def _episode_row(episode) -> str:
    breakdown = ", ".join(
        f"{html.escape(name.replace('_', ' ').title())}: {metric.score:.1f}"
        for name, metric in episode.metrics.items()
    )
    return (
        "<tr>"
        f"<td>{html.escape(episode.episode)}</td>"
        f"<td>{episode.score:.1f}/100</td>"
        f"<td>{breakdown}</td>"
        "</tr>"
    )


def _issue_items(result: EvaluationResult) -> str:
    issues: list[str] = []
    for episode in result.episodes:
        issues.extend(f"{episode.episode}: {issue}" for issue in episode.issues)
    if not issues:
        return "<li>No major issues detected.</li>"
    return "\n".join(f"<li>{html.escape(issue)}</li>" for issue in issues[:20])


def _timeline_svg(result: EvaluationResult) -> str:
    if not result.episodes:
        return "<p>No episode scores available.</p>"

    width = max(720, 180 * len(result.episodes))
    height = 280
    left = 64
    top = 24
    plot_height = 200
    names = list(result.metrics)
    colors = ["#2563eb", "#198f5d", "#d94c45", "#b7791f", "#6b46c1"]
    group_width = (width - left - 24) / max(1, len(result.episodes))
    bar_width = max(10, min(22, group_width / max(1, len(names) + 1)))
    parts = [
        f'<svg width="{width}" height="{height}" role="img" aria-label="Metric timeline">',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{width - 16}" y2="{top + plot_height}" stroke="#d8e1ea"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#d8e1ea"/>',
    ]
    for tick in [0, 25, 50, 75, 100]:
        y = top + plot_height - (tick / 100) * plot_height
        parts.append(f'<line x1="{left - 4}" y1="{y}" x2="{width - 16}" y2="{y}" stroke="#edf2f7"/>')
        parts.append(f'<text x="12" y="{y + 4}" font-size="11" fill="#617282">{tick}</text>')

    for episode_idx, episode in enumerate(result.episodes):
        base_x = left + episode_idx * group_width + 20
        for metric_idx, name in enumerate(names):
            metric = episode.metrics.get(name)
            if metric is None:
                continue
            bar_height = (metric.score / 100) * plot_height
            x = base_x + metric_idx * (bar_width + 4)
            y = top + plot_height - bar_height
            color = colors[metric_idx % len(colors)]
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" rx="2" fill="{color}"><title>{name}: {metric.score:.1f}</title></rect>'
            )
        parts.append(
            f'<text x="{base_x:.1f}" y="{height - 26}" font-size="12" fill="#617282">{html.escape(episode.episode)}</text>'
        )

    legend_x = left
    for idx, name in enumerate(names):
        color = colors[idx % len(colors)]
        label = html.escape(name.replace("_", " ").title())
        x = legend_x + idx * 150
        parts.append(f'<rect x="{x}" y="{height - 14}" width="10" height="10" fill="{color}"/>')
        parts.append(f'<text x="{x + 14}" y="{height - 5}" font-size="11" fill="#617282">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m worldbench.dashboard <result_json_or_dataset_path>")
    launch_dashboard(sys.argv[1])
