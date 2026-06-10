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
            if parsed.path == "/report.md":
                report_path = _report_for_target(Path(target))
                if report_path is None:
                    self.send_error(404, "Report not found")
                    return
                self._send_bytes(report_path.read_bytes(), "text/markdown; charset=utf-8")
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

        def _send_bytes(self, payload: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

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


def _report_for_target(path: Path) -> Path | None:
    if path.is_file():
        candidate = path.parent / "report.md"
    else:
        candidate = path / "report.md"
    return candidate if candidate.is_file() else None


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
    report_link = '<a class="report-link" href="/report.md">Open generated report</a>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WorldBench Dashboard</title>
  <style>
    :root {{
      --bg: #071019;
      --panel: rgba(10, 20, 31, 0.94);
      --panel-2: rgba(15, 28, 42, 0.96);
      --ink: #f6faff;
      --muted: #91a9bb;
      --line: #28435a;
      --soft-line: rgba(88, 125, 153, 0.32);
      --red: #ff6b5f;
      --green: #41d38a;
      --blue: #5fc6eb;
      --amber: #ffb85c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 6% 8%, rgba(35, 92, 122, 0.36), transparent 22rem),
        radial-gradient(circle at 88% 88%, rgba(29, 135, 91, 0.28), transparent 28rem),
        linear-gradient(180deg, #071019 0%, #0b1722 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(80, 118, 147, 0.07) 1px, transparent 1px),
        linear-gradient(78deg, rgba(80, 118, 147, 0.06) 1px, transparent 1px);
      background-size: 64px 56px, 80px 80px;
      transform: skewX(-11deg);
      transform-origin: top left;
      opacity: 0.42;
    }}
    header {{
      position: relative;
      z-index: 1;
      max-width: 1240px;
      margin: 34px auto 0;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: rgba(10, 20, 32, 0.9);
      color: var(--ink);
      padding: 16px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 20px 70px rgba(0, 0, 0, 0.26);
    }}
    header h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; line-height: 1.1; }}
    header p {{ margin: 4px 0 0; color: var(--muted); }}
    .run-pill {{
      border: 1px solid rgba(65, 211, 138, 0.62);
      border-radius: 999px;
      color: #dff7eb;
      background: rgba(65, 211, 138, 0.12);
      padding: 5px 18px;
      font-size: 12px;
      white-space: nowrap;
    }}
    main {{ position: relative; z-index: 1; max-width: 1240px; margin: 0 auto; padding: 32px 0 64px; }}
    .summary {{
      display: grid;
      grid-template-columns: 252px minmax(0, 1fr);
      gap: 26px;
      align-items: stretch;
      margin-bottom: 26px;
    }}
    .score, .panel, .metric-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 55px rgba(0, 0, 0, 0.22);
      backdrop-filter: blur(10px);
    }}
    .score {{ padding: 34px 30px 26px; min-height: 178px; }}
    .score .label {{ color: var(--muted); font-size: 13px; }}
    .score .value {{ color: var(--red); font-size: 70px; line-height: 0.95; font-weight: 800; margin-top: 28px; }}
    .score .value small {{ font-size: 21px; color: var(--muted); margin-left: 6px; }}
    .main-failure {{ padding: 34px; min-height: 178px; }}
    .main-failure h2, section h2 {{ margin: 0 0 12px; font-size: 23px; letter-spacing: 0; }}
    .main-failure p {{ margin: 0; color: #d2e0ea; font-size: 17px; max-width: 880px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(140px, 1fr));
      gap: 20px;
      margin: 0 0 34px;
    }}
    .metric-card {{ padding: 22px 20px 18px; min-height: 138px; }}
    .metric-card .name {{ color: var(--muted); font-size: 13px; min-height: 32px; }}
    .metric-card .metric-score {{ color: var(--ink); font-size: 30px; font-weight: 780; margin-top: 12px; }}
    .metric-card .metric-score small {{ color: var(--muted); font-size: 12px; font-weight: 500; margin-left: 5px; }}
    .bar {{ height: 8px; border-radius: 999px; background: #26394a; overflow: hidden; margin-top: 14px; }}
    .bar span {{ display: block; height: 100%; background: var(--blue); }}
    section {{ margin-top: 24px; }}
    .panel {{ padding: 28px 30px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 13px 10px; border-bottom: 1px solid var(--soft-line); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    td {{ color: #dce8f1; }}
    .issues {{ display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }}
    .issues li {{
      border-left: 6px solid var(--amber);
      background: var(--panel-2);
      border-radius: 10px;
      border-top: 1px solid var(--soft-line);
      border-right: 1px solid var(--soft-line);
      border-bottom: 1px solid var(--soft-line);
      color: #dce8f1;
      padding: 10px 14px;
    }}
    .issues li.critical {{ border-left-color: var(--red); }}
    .issues li.ok {{ border-left-color: var(--green); }}
    .issues li.severity-label {{
      margin-top: 12px;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--muted);
      font-size: 12px;
      font-weight: 760;
      text-transform: uppercase;
    }}
    .viewer-controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }}
    select, input[type="range"] {{ accent-color: var(--blue); }}
    label {{ color: var(--muted); }}
    select {{
      color: var(--ink);
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #0f1c2a;
    }}
    input[type="range"] {{ min-width: 220px; }}
    #frameLabel {{ color: var(--ink); }}
    .frames {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .frame h3 {{ margin: 0 0 8px; font-size: 14px; color: var(--muted); }}
    .frame img {{
      width: 100%;
      image-rendering: auto;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #071019;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
    }}
    .chart {{ width: 100%; overflow-x: auto; }}
    .report-link {{
      display: inline-block;
      color: #dff7eb;
      font-weight: 650;
      margin-top: 22px;
      text-decoration: none;
      border: 1px solid rgba(65, 211, 138, 0.55);
      border-radius: 999px;
      padding: 7px 14px;
      background: rgba(65, 211, 138, 0.1);
    }}
    .report-link:hover {{ border-color: var(--green); }}
    summary {{ cursor: pointer; color: var(--ink); font-weight: 700; }}
    details pre {{ overflow: auto; max-height: 420px; background: #06101a; color: #dbe9f3; padding: 16px; border: 1px solid var(--soft-line); border-radius: 14px; }}
    svg text {{ font-family: inherit; }}
    @media (max-width: 900px) {{
      header {{ margin: 18px 16px 0; align-items: flex-start; gap: 12px; flex-direction: column; }}
      main {{ padding: 22px 16px 44px; }}
      .summary {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .frames {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>WorldBench Dashboard</h1>
      <p>Local robotics world-model evaluation</p>
    </div>
    <div class="run-pill">local run</div>
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
        {report_link}
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
    color = "#41d38a" if score >= 85 else "#ffb85c" if score >= 60 else "#ff6b5f"
    return (
        '<div class="metric-card">'
        f'<div class="name">{label}</div>'
        f'<div class="metric-score">{score:.1f}<small>/100</small></div>'
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
        return '<li class="ok">No major issues detected.</li>'

    critical_terms = ("contact", "mismatch", "disappear", "missing", "opposite")
    critical = [issue for issue in issues if any(term in issue.lower() for term in critical_terms)]
    warnings = [issue for issue in issues if issue not in critical]
    parts: list[str] = []
    if critical:
        parts.append('<li class="severity-label">Critical</li>')
        parts.extend(f'<li class="critical">{html.escape(issue)}</li>' for issue in critical[:10])
    if warnings:
        parts.append('<li class="severity-label">Warnings</li>')
        parts.extend(f"<li>{html.escape(issue)}</li>" for issue in warnings[:10])
    return "\n".join(parts)


def _timeline_svg(result: EvaluationResult) -> str:
    if not result.episodes:
        return "<p>No episode scores available.</p>"

    width = max(720, 180 * len(result.episodes))
    height = 280
    left = 64
    top = 24
    plot_height = 200
    names = list(result.metrics)
    colors = ["#5fc6eb", "#41d38a", "#ff6b5f", "#ffb85c", "#9b8cff"]
    group_width = (width - left - 24) / max(1, len(result.episodes))
    bar_width = max(10, min(22, group_width / max(1, len(names) + 1)))
    parts = [
        f'<svg width="{width}" height="{height}" role="img" aria-label="Metric timeline">',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{width - 16}" y2="{top + plot_height}" stroke="#28435a"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#28435a"/>',
    ]
    for tick in [0, 25, 50, 75, 100]:
        y = top + plot_height - (tick / 100) * plot_height
        parts.append(f'<line x1="{left - 4}" y1="{y}" x2="{width - 16}" y2="{y}" stroke="#182b3c"/>')
        parts.append(f'<text x="12" y="{y + 4}" font-size="11" fill="#91a9bb">{tick}</text>')

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
            f'<text x="{base_x:.1f}" y="{height - 26}" font-size="12" fill="#91a9bb">{html.escape(episode.episode)}</text>'
        )

    legend_x = left
    for idx, name in enumerate(names):
        color = colors[idx % len(colors)]
        label = html.escape(name.replace("_", " ").title())
        x = legend_x + idx * 150
        parts.append(f'<rect x="{x}" y="{height - 14}" width="10" height="10" fill="{color}"/>')
        parts.append(f'<text x="{x + 14}" y="{height - 5}" font-size="11" fill="#91a9bb">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m worldbench.dashboard <result_json_or_dataset_path>")
    launch_dashboard(sys.argv[1])
