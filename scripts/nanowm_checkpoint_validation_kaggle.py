"""Run the NanoWM 50k vs 300k checkpoint validation on a Kaggle GPU.

This script is intended to run inside Kaggle, not as part of normal WorldBench
CI. It keeps raw videos, datasets, and checkpoints in /kaggle/working and emits
only compact JSON artifacts.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import traceback
import zipfile


START_MONO = time.time()
STARTED_AT = datetime.now(timezone.utc).isoformat()
WORK = Path("/kaggle/working")
RUN_ROOT = WORK / "checkpoint_validation"
VIDEO_ROOT = RUN_ROOT / "videos"
COMPACT = RUN_ROOT / "compact"
LOGS = RUN_ROOT / "logs"
STATUS_PATH = RUN_ROOT / "status.json"
PROVENANCE_PATH = COMPACT / "provenance.json"

for path in [RUN_ROOT, VIDEO_ROOT, COMPACT, LOGS]:
    path.mkdir(parents=True, exist_ok=True)
for subdir in ["ground_truth", "baseline", "candidate"]:
    (VIDEO_ROOT / subdir).mkdir(parents=True, exist_ok=True)

EPISODES = list(range(10))
SEEDS = {episode: 2026070900 + episode for episode in EPISODES}
DATASET_REPO = "IPEC-COMMUNITY/fractal20220817_data_lerobot"
MODEL_FAMILY = "NanoWM-B/2"
BASELINE_REPO = "knightnemo/nanowm-b2-rt1-abl-pred-v-50k"
CANDIDATE_REPO = "knightnemo/nanowm-b2-rt1-300k"
BASELINE_NAME = "nanowm-b2-rt1-50k"
CANDIDATE_NAME = "nanowm-b2-rt1-300k"
WORLDBENCH_COMMIT = "75f2f7b0549653c955671dc695fcdaec5e742377"

SETTINGS = {
    "history_length": 4,
    "rollout_length": 12,
    "future_frames_evaluated": 8,
    "num_sampling_steps": 50,
    "batch_size": 1,
    "num_samples": 1,
    "fps": 3,
    "resolution": [256, 256],
    "precision": "fp16",
    "action_conditioning": "enabled, identical actions from RT-1 / Fractal",
    "seeds": SEEDS,
}

os.environ.setdefault("HF_HOME", str(WORK / "hf_home"))
os.environ.setdefault("HF_HUB_CACHE", str(WORK / "hf_home" / "hub"))
os.environ.setdefault("WANDB_MODE", "offline")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ["RT1_DATA_ROOT"] = str(WORK / "rt1_checkpoint_validation")
DATA_ROOT = Path(os.environ["RT1_DATA_ROOT"])
DATA_ROOT.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def folder_stats(path: Path) -> dict[str, object]:
    total = 0
    count = 0
    largest: list[dict[str, object]] = []
    if path.exists():
        for file in path.rglob("*"):
            if file.is_file():
                try:
                    size = file.stat().st_size
                except OSError:
                    continue
                total += size
                count += 1
                largest.append({"path": str(file.relative_to(path)), "bytes": size})
    largest.sort(key=lambda item: int(item["bytes"]), reverse=True)
    return {"bytes": total, "files": count, "largest_files": largest[:12]}


def mark(stage: str, **extra: object) -> None:
    payload = {
        "stage": stage,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - START_MONO, 2),
    }
    payload.update(extra)
    write_json(STATUS_PATH, payload)
    print("STATUS", json.dumps(payload, sort_keys=True), flush=True)


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    allow_codes: tuple[int, ...] = (0,),
    log_name: str | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or WORK),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if log_name:
        (LOGS / log_name).write_text(proc.stdout, encoding="utf-8")
    if proc.returncode not in allow_codes:
        tail = "\n".join(proc.stdout.splitlines()[-80:])
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n--- tail ---\n{tail}")
    return proc


def bootstrap_code() -> dict[str, object]:
    mark("environment_check")
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the Kaggle runtime.")
    gpu = {
        "cuda_available": True,
        "gpu_name": torch.cuda.get_device_name(0),
        "cuda_version": torch.version.cuda,
        "torch_version": torch.__version__,
        "python_version": sys.version.split()[0],
        "vram_bytes": int(torch.cuda.get_device_properties(0).total_memory),
    }
    mark("gpu_ready", **gpu)

    worldbench_dir = WORK / "worldbench"
    if not (worldbench_dir / ".git").exists():
        mark("clone_worldbench")
        run_cmd(
            ["git", "clone", "https://github.com/tigee1311/worldbench.git", str(worldbench_dir)],
            log_name="git_clone_worldbench.log",
            timeout=600,
        )
    run_cmd(["git", "fetch", "origin", "main"], cwd=worldbench_dir, log_name="git_fetch_worldbench.log", timeout=600)
    run_cmd(["git", "checkout", WORLDBENCH_COMMIT], cwd=worldbench_dir, log_name="git_checkout_worldbench.log")
    os.environ["PYTHONPATH"] = str(worldbench_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")
    if str(worldbench_dir) not in sys.path:
        sys.path.insert(0, str(worldbench_dir))

    import worldbench

    if worldbench.__version__ != "0.3.0.dev0":
        raise RuntimeError(f"Unexpected WorldBench version: {worldbench.__version__}")

    nano_dir = WORK / "nano-world-model"
    if not (nano_dir / ".git").exists():
        mark("clone_nanowm")
        run_cmd(
            ["git", "clone", "https://github.com/simchowitzlabpublic/nano-world-model.git", str(nano_dir)],
            log_name="git_clone_nanowm.log",
            timeout=600,
        )
    nano_commit = run_cmd(["git", "rev-parse", "HEAD"], cwd=nano_dir).stdout.strip()
    mark("code_ready", worldbench_version=worldbench.__version__, nanowm_commit=nano_commit)
    return {"gpu": gpu, "worldbench_dir": str(worldbench_dir), "nano_dir": str(nano_dir), "nano_commit": nano_commit}


def download_checkpoints() -> dict[str, dict[str, object]]:
    mark("download_checkpoints")
    from huggingface_hub import hf_hub_download, model_info

    ckpt_root = RUN_ROOT / "checkpoints"
    ckpt_root.mkdir(parents=True, exist_ok=True)

    def one(repo: str, label: str) -> dict[str, object]:
        local = ckpt_root / label
        local.mkdir(parents=True, exist_ok=True)
        config_path = Path(hf_hub_download(repo, filename="config.yaml", local_dir=str(local)))
        weights_path = Path(hf_hub_download(repo, filename="model.safetensors", local_dir=str(local)))
        info = model_info(repo)
        return {
            "repo": repo,
            "revision": getattr(info, "sha", None),
            "config_path": str(config_path),
            "weights_path": str(weights_path),
            "weights_bytes": weights_path.stat().st_size,
        }

    payload = {
        "baseline": one(BASELINE_REPO, "baseline"),
        "candidate": one(CANDIDATE_REPO, "candidate"),
    }
    write_json(COMPACT / "checkpoint_metadata.json", payload)
    mark(
        "checkpoints_ready",
        baseline_revision=payload["baseline"]["revision"],
        candidate_revision=payload["candidate"]["revision"],
    )
    return payload


def patch_lerobot_backend(nano_dir: Path) -> dict[str, object]:
    mark("check_lerobot_backend")
    # The previous successful NanoWM Kaggle workflow required PyAV for RT-1
    # decoding. Avoid a slow stock-backend probe here; apply the same patch
    # before the actual episode loads.
    patch_path = nano_dir / "src/wm_datasets/data_source/lerobot/lerobot_data_source.py"
    patched = False
    text = patch_path.read_text(encoding="utf-8")
    old = """        self.dataset = LeRobotDataset(
            repo_id=repo_id,
            root=root,
            image_transforms=None,
            episodes=episodes
        )"""
    new = """        self.dataset = LeRobotDataset(
            repo_id=repo_id,
            root=root,
            image_transforms=None,
            episodes=episodes,
            video_backend="pyav"
        )"""
    if 'video_backend="pyav"' not in text:
        if old not in text:
            raise RuntimeError("Could not locate LeRobotDataset constructor block for PyAV patch.")
        patch_path.write_text(text.replace(old, new), encoding="utf-8")
        patched = True
    result = {"stock_backend_probe": "skipped", "pyav_patch_applied": patched}
    write_json(COMPACT / "lerobot_backend.json", result)
    mark("lerobot_backend_ready", **result)
    return result


def load_runtime(nano_dir: Path) -> dict[str, object]:
    src = nano_dir / "src"
    sample_src = src / "sample"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(sample_src) not in sys.path:
        sys.path.insert(0, str(sample_src))
    import torch
    from diffusion import create_diffusion
    from diffusion.df_sample import dfot_sample
    from einops import rearrange
    from latent_codecs import (
        get_model_latent_channels,
        get_model_latent_size,
        load_autoencoder_kl,
        resolve_latent_codec_config,
    )
    from models import get_models
    from omegaconf import OmegaConf
    from sampling_utils import decode_latents, encode_frames, resize_frames, save_video
    from utils.nanowm_utils import find_model
    from wm_datasets.data_source.lerobot.lerobot_data_source import LeRobotDataSource
    from wm_datasets.world_model_dataset import WorldModelDataset

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    return {
        "OmegaConf": OmegaConf,
        "LeRobotDataSource": LeRobotDataSource,
        "WorldModelDataset": WorldModelDataset,
        "create_diffusion": create_diffusion,
        "decode_latents": decode_latents,
        "dfot_sample": dfot_sample,
        "encode_frames": encode_frames,
        "find_model": find_model,
        "get_model_latent_channels": get_model_latent_channels,
        "get_model_latent_size": get_model_latent_size,
        "get_models": get_models,
        "load_autoencoder_kl": load_autoencoder_kl,
        "rearrange": rearrange,
        "resize_frames": resize_frames,
        "resolve_latent_codec_config": resolve_latent_codec_config,
        "save_video": save_video,
        "torch": torch,
    }


def set_seed(torch_module: object, seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        pass
    torch_module.manual_seed(seed)
    if torch_module.cuda.is_available():
        torch_module.cuda.manual_seed_all(seed)


def prepare_cfg(runtime: dict[str, object], config_path: str):
    cfg = runtime["OmegaConf"].load(config_path)
    cfg.model.num_sampling_steps = SETTINGS["num_sampling_steps"]
    cfg.history_length = SETTINGS["history_length"]
    cfg.rollout_length = SETTINGS["rollout_length"]
    cfg.batch_size = SETTINGS["batch_size"]
    cfg.fps = SETTINGS["fps"]
    cfg.use_fp16 = True
    cfg.dataset.loader.root = str(DATA_ROOT)
    cfg.dataset.loader.data_path = DATASET_REPO
    cfg.dataset.loader.image_key = "observation.images.image"
    cfg.dataset.loader.normalize_action = True
    cfg.dataset.loader.normalize_state = False
    return cfg


def cfg_value(cfg: object, dotted: str) -> object:
    cur = cfg
    try:
        for part in dotted.split("."):
            cur = cur[part]
        return cur
    except Exception:  # noqa: BLE001
        return None


def check_config_compatibility(baseline_cfg: object, candidate_cfg: object) -> None:
    fields = [
        "model.arch",
        "model.name",
        "model.num_frames",
        "model.use_action",
        "model.action_injection.type",
        "model.causal",
        "model.image_size",
        "model.latent_channels",
        "dataset.name",
        "dataset.frame_interval",
        "dataset.spec.action_dim",
        "experiment.diffusion.pred_name",
        "experiment.diffusion.zero_terminal_snr",
        "experiment.diffusion.diffusion_steps",
    ]
    rows = []
    mismatches = []
    for field in fields:
        left = cfg_value(baseline_cfg, field)
        right = cfg_value(candidate_cfg, field)
        row = {"field": field, "baseline": str(left), "candidate": str(right), "matches": left == right}
        rows.append(row)
        if left != right:
            mismatches.append(row)
    write_json(COMPACT / "config_compatibility.json", {"fields": rows, "mismatches": mismatches})
    if mismatches:
        raise RuntimeError(f"Checkpoint configs differ on required compatibility fields: {mismatches}")


def build_model_bundle(runtime: dict[str, object], cfg: object, weights_path: str) -> dict[str, object]:
    torch = runtime["torch"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cfg.model.latent_size = runtime["get_model_latent_size"](cfg)
    latent_channels = runtime["get_model_latent_channels"](cfg)
    model = runtime["get_models"](cfg).to(device)
    if weights_path.endswith(".safetensors"):
        from safetensors.torch import load_file

        state_dict = load_file(weights_path)
    else:
        state_dict = runtime["find_model"](weights_path)
    if "model" in state_dict:
        state_dict = state_dict["model"]
    state_dict = {key[6:] if key.startswith("model.") else key: value for key, value in state_dict.items()}
    model.load_state_dict(state_dict)
    if cfg.use_fp16:
        model = model.half()
    model.eval()
    codec_cfg = runtime["resolve_latent_codec_config"](cfg)
    if not codec_cfg.has_decoder:
        raise RuntimeError(f"NanoWM codec has no decoder: {codec_cfg.kind}")
    vae = runtime["load_autoencoder_kl"](codec_cfg.model_path).to(device)
    vae.eval()
    diffusion = runtime["create_diffusion"](
        timestep_respacing=str(cfg.model.num_sampling_steps),
        noise_schedule=cfg.experiment.diffusion.noise_schedule,
        pred_name=cfg.experiment.diffusion.pred_name,
        diffusion_steps=cfg.experiment.diffusion.diffusion_steps,
        snr_gamma=cfg.experiment.diffusion.snr_gamma,
        zero_terminal_snr=cfg.experiment.diffusion.zero_terminal_snr,
    )
    return {
        "device": device,
        "model": model,
        "vae": vae,
        "diffusion": diffusion,
        "latent_channels": latent_channels,
        "latent_size": int(cfg.model.latent_size),
        "vae_precision": getattr(cfg.experiment.infra, "vae_precision", "fp32"),
    }


def make_dataset(runtime: dict[str, object], cfg: object, episode_id: int):
    data_source = runtime["LeRobotDataSource"](
        repo_id=DATASET_REPO,
        root=str(DATA_ROOT),
        episodes=[episode_id],
        image_key="observation.images.image",
        preload_trajectories=False,
    )
    seq_len = data_source.get_seq_length(0)
    if seq_len < SETTINGS["rollout_length"]:
        raise RuntimeError(f"Episode {episode_id} too short: {seq_len} frames")
    dataset = runtime["WorldModelDataset"](
        data_source=data_source,
        num_frames=int(cfg.model.num_frames),
        frame_interval=int(cfg.dataset.frame_interval),
        image_size=cfg.model.image_size,
        split="val",
        split_ratio=0.0,
        normalize_action=True,
        normalize_state=False,
        normalize_pixel=True,
        random_seed=42,
        slice_mode="exhaustive",
        stride=1,
        resize_mode="stretch",
        use_data_source_stats=True,
        precomputed_slices=[{"traj_idx": 0, "start_frame": 0, "end_frame": int(cfg.model.num_frames)}],
    )
    return dataset, seq_len


def inspect_video(path: Path) -> dict[str, object]:
    import imageio.v2 as imageio

    reader = imageio.get_reader(str(path))
    meta = reader.get_meta_data()
    count = 0
    first_shape = None
    for frame in reader:
        if first_shape is None:
            first_shape = list(frame.shape)
        count += 1
    reader.close()
    return {"path": str(path), "frames": count, "shape": first_shape, "fps": float(meta.get("fps", 0.0) or 0.0)}


def run_one_episode(runtime: dict[str, object], cfg: object, bundle: dict[str, object], episode_id: int, out_dir: Path, save_gt: bool) -> dict[str, object]:
    torch = runtime["torch"]
    set_seed(torch, SEEDS[episode_id])
    t0 = time.time()
    dataset, seq_len = make_dataset(runtime, cfg, episode_id)
    frame_interval = int(cfg.dataset.frame_interval)
    model_context_frames = int(getattr(cfg.model, "n_context_frames", 1))
    model_window_frames = int(cfg.model.num_frames)
    if model_context_frames < 0 or model_context_frames >= model_window_frames:
        raise RuntimeError(
            f"Invalid NanoWM context/window configuration: "
            f"n_context_frames={model_context_frames}, num_frames={model_window_frames}"
        )
    if model_context_frames > SETTINGS["history_length"]:
        raise RuntimeError(
            f"NanoWM requires {model_context_frames} context frames, but rollout history has "
            f"{SETTINGS['history_length']}"
        )
    end_frame = SETTINGS["rollout_length"] * frame_interval
    visual_frames = dataset.data_source.load_visual_frames(index=0, start=0, end=end_frame, step=frame_interval)
    visual_frames = runtime["resize_frames"](visual_frames, dataset.image_size, dataset.resize_mode)
    visual_frames = visual_frames * 2.0 - 1.0
    traj_data = dataset.data_source.load_trajectory(0)
    raw_actions = traj_data.actions[0:end_frame].clone()
    if dataset.normalize_action:
        raw_actions = (raw_actions - dataset._raw_action_mean) / dataset._raw_action_std
    gt_visual = visual_frames.unsqueeze(0).to(bundle["device"])
    batch_raw_actions = raw_actions.unsqueeze(0).to(bundle["device"])
    gt_latents = runtime["encode_frames"](bundle["vae"], gt_visual, bundle["device"], vae_precision=bundle["vae_precision"])
    generated_latents = gt_latents[:, : SETTINGS["history_length"]]
    peak_before = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
    for t in range(SETTINGS["history_length"], SETTINGS["rollout_length"]):
        context_latents = generated_latents[:, -model_context_frames:] if model_context_frames > 0 else None
        start_frame_idx = t - model_context_frames
        end_frame_idx = start_frame_idx + model_window_frames
        start_raw_idx = start_frame_idx * frame_interval
        end_raw_idx = end_frame_idx * frame_interval
        if end_raw_idx > batch_raw_actions.shape[1]:
            pad_len = end_raw_idx - batch_raw_actions.shape[1]
            last_act = batch_raw_actions[:, -1:]
            window_raw_actions = torch.cat([batch_raw_actions[:, start_raw_idx:], last_act.repeat(1, pad_len, 1)], dim=1)
        else:
            window_raw_actions = batch_raw_actions[:, start_raw_idx:end_raw_idx]
        window_actions = runtime["rearrange"](window_raw_actions, "b (n f) d -> b n (f d)", n=model_window_frames)
        model_kwargs = {"y": None, "use_fp16": True}
        if bool(cfg.model.use_action):
            if cfg.use_fp16:
                window_actions = window_actions.to(dtype=torch.float16)
            model_kwargs["action"] = window_actions
        shape = (1, model_window_frames, bundle["latent_channels"], bundle["latent_size"], bundle["latent_size"])
        pred_latents = runtime["dfot_sample"](
            diffusion=bundle["diffusion"],
            model=bundle["model"].forward,
            shape=shape,
            context=context_latents,
            n_context_frames=model_context_frames,
            scheduling_mode=cfg.model.scheduling_mode,
            num_sampling_steps=cfg.model.num_sampling_steps,
            model_kwargs=model_kwargs,
            device=bundle["device"],
            progress=False,
            eta=0.0,
            clip_denoised=False,
            n_generate_frames=1,
            history_stabilization_level=cfg.experiment.diffusion.history_stabilization_level,
        )
        generated_latents = torch.cat(
            [generated_latents, pred_latents[:, model_context_frames : model_context_frames + 1]],
            dim=1,
        )
    gen_frames = runtime["decode_latents"](bundle["vae"], generated_latents, vae_precision=bundle["vae_precision"])
    gt_frames = runtime["decode_latents"](bundle["vae"], gt_latents, vae_precision=bundle["vae_precision"])
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / f"episode_{episode_id:03d}.mp4"
    runtime["save_video"](gen_frames[0], str(pred_path), fps=SETTINGS["fps"])
    gt_path = VIDEO_ROOT / "ground_truth" / f"episode_{episode_id:03d}.mp4"
    if save_gt:
        runtime["save_video"](gt_frames[0], str(gt_path), fps=SETTINGS["fps"])
    peak_after = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
    pred_info = inspect_video(pred_path)
    gt_info = inspect_video(gt_path)
    for label, info in [("prediction", pred_info), ("ground_truth", gt_info)]:
        if info["frames"] != SETTINGS["rollout_length"]:
            raise RuntimeError(f"{label} episode {episode_id} has {info['frames']} frames, expected {SETTINGS['rollout_length']}")
        if info["shape"][:2] != SETTINGS["resolution"]:
            raise RuntimeError(f"{label} episode {episode_id} shape {info['shape']}, expected 256x256 RGB")
        if abs(float(info["fps"]) - SETTINGS["fps"]) > 0.2:
            raise RuntimeError(f"{label} episode {episode_id} FPS {info['fps']}, expected {SETTINGS['fps']}")
    return {
        "episode_id": episode_id,
        "seed": SEEDS[episode_id],
        "sequence_length": int(seq_len),
        "nanowm_model_context_frames": model_context_frames,
        "nanowm_model_window_frames": model_window_frames,
        "runtime_seconds": round(time.time() - t0, 3),
        "gpu_peak_memory_bytes_delta": int(max(0, peak_after - peak_before)),
        "prediction_video": pred_info,
        "ground_truth_video": gt_info,
    }


def run_checkpoint(runtime: dict[str, object], label: str, name: str, cfg: object, weights_path: str, save_gt: bool) -> list[dict[str, object]]:
    torch = runtime["torch"]
    mark(f"inference_{label}_loading")
    bundle = build_model_bundle(runtime, cfg, weights_path)
    results = []
    for episode_id in EPISODES:
        mark(f"inference_{label}_episode", episode=episode_id)
        result = run_one_episode(runtime, cfg, bundle, episode_id, VIDEO_ROOT / label, save_gt)
        results.append(result)
        print(f"EPISODE_DONE {label} episode={episode_id} runtime={result['runtime_seconds']}", flush=True)
    del bundle["model"]
    del bundle["vae"]
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    payload = {"checkpoint_name": name, "episodes": results, "total_runtime_seconds": round(sum(float(r["runtime_seconds"]) for r in results), 3)}
    write_json(COMPACT / f"{label}_inference_runtime.json", payload)
    mark(f"inference_{label}_complete", episodes=len(results), total_runtime_seconds=payload["total_runtime_seconds"])
    return results


def run_worldbench_eval() -> dict[str, object]:
    mark("worldbench_eval_batch")
    baseline_out = COMPACT / "baseline_batch_result.json"
    candidate_out = COMPACT / "candidate_batch_result.json"
    batches_root = RUN_ROOT / "worldbench_batches"
    run_cmd([
        sys.executable,
        "-m",
        "worldbench.cli",
        "eval-batch",
        "--ground-truth",
        str(VIDEO_ROOT / "ground_truth"),
        "--predictions",
        str(VIDEO_ROOT / "baseline"),
        "--name",
        BASELINE_NAME,
        "--skip-context",
        str(SETTINGS["history_length"]),
        "--output-root",
        str(batches_root / "baseline"),
        "--output",
        str(baseline_out),
    ], log_name="worldbench_eval_baseline.log")
    run_cmd([
        sys.executable,
        "-m",
        "worldbench.cli",
        "eval-batch",
        "--ground-truth",
        str(VIDEO_ROOT / "ground_truth"),
        "--predictions",
        str(VIDEO_ROOT / "candidate"),
        "--name",
        CANDIDATE_NAME,
        "--skip-context",
        str(SETTINGS["history_length"]),
        "--output-root",
        str(batches_root / "candidate"),
        "--output",
        str(candidate_out),
    ], log_name="worldbench_eval_candidate.log")
    gates_root = RUN_ROOT / "worldbench_gates"
    strict_proc = run_cmd([
        sys.executable,
        "-m",
        "worldbench.cli",
        "gate",
        "--baseline",
        str(baseline_out),
        "--candidate",
        str(candidate_out),
        "--output-root",
        str(gates_root / "strict"),
    ], allow_codes=(0, 1), log_name="worldbench_gate_strict.log")
    shutil.copy2(gates_root / "strict/latest/gate.json", COMPACT / "strict_gate_result.json")
    engineering_proc = run_cmd([
        sys.executable,
        "-m",
        "worldbench.cli",
        "gate",
        "--baseline",
        str(baseline_out),
        "--candidate",
        str(candidate_out),
        "--max-overall-drop",
        "2",
        "--max-metric-drop",
        "5",
        "--max-horizon-drop",
        "5",
        "--output-root",
        str(gates_root / "engineering"),
    ], allow_codes=(0, 1), log_name="worldbench_gate_engineering.log")
    shutil.copy2(gates_root / "engineering/latest/gate.json", COMPACT / "engineering_gate_result.json")
    return {
        "baseline_batch_result": str(baseline_out),
        "candidate_batch_result": str(candidate_out),
        "strict_gate_result": str(COMPACT / "strict_gate_result.json"),
        "engineering_gate_result": str(COMPACT / "engineering_gate_result.json"),
        "strict_exit_code": strict_proc.returncode,
        "engineering_exit_code": engineering_proc.returncode,
    }


def summarize(env: dict[str, object], checkpoints: dict[str, dict[str, object]], baseline_runtime: list[dict[str, object]], candidate_runtime: list[dict[str, object]], wb_paths: dict[str, object]) -> dict[str, object]:
    baseline = read_json(COMPACT / "baseline_batch_result.json")
    candidate = read_json(COMPACT / "candidate_batch_result.json")
    strict_gate = read_json(COMPACT / "strict_gate_result.json")
    engineering_gate = read_json(COMPACT / "engineering_gate_result.json")
    overall_delta = candidate["aggregate"]["overall"]["mean"] - baseline["aggregate"]["overall"]["mean"]
    episodes = strict_gate.get("episodes", {})
    summary = {
        "question": "Did the NanoWM 300k checkpoint improve over the NanoWM 50k checkpoint on the same RT-1 episodes?",
        "answer": "Candidate improved overall on this fixed 10-episode validation slice." if overall_delta > 0.01 else "Candidate regressed overall on this fixed 10-episode validation slice." if overall_delta < -0.01 else "Candidate was effectively unchanged overall on this fixed 10-episode validation slice.",
        "baseline_checkpoint": BASELINE_REPO,
        "candidate_checkpoint": CANDIDATE_REPO,
        "baseline_revision": checkpoints["baseline"].get("revision"),
        "candidate_revision": checkpoints["candidate"].get("revision"),
        "episodes_evaluated": EPISODES,
        "episode_count": len(EPISODES),
        "settings": SETTINGS,
        "baseline_overall": baseline["aggregate"]["overall"]["mean"],
        "candidate_overall": candidate["aggregate"]["overall"]["mean"],
        "overall_delta": overall_delta,
        "metric_deltas": strict_gate.get("metrics", []),
        "horizon_deltas": strict_gate.get("horizon", []),
        "episodes_improved": episodes.get("improved_count"),
        "episodes_regressed": episodes.get("regressed_count"),
        "episodes_unchanged": episodes.get("unchanged_count"),
        "worst_regressions": episodes.get("worst_regressions", [])[:3],
        "best_improvements": episodes.get("best_improvements", [])[:3],
        "strict_gate_status": strict_gate.get("status"),
        "engineering_gate_status": engineering_gate.get("status"),
        "strict_gate_failure_reasons": strict_gate.get("failure_reasons", []),
        "engineering_gate_failure_reasons": engineering_gate.get("failure_reasons", []),
        "worldbench_paths": wb_paths,
        "inference_environment": env.get("gpu"),
        "nanowm_commit": env.get("nano_commit"),
        "data_root_stats_final": folder_stats(DATA_ROOT),
        "hf_home_stats_final": folder_stats(Path(os.environ["HF_HOME"])),
        "runtime": {
            "started_at": STARTED_AT,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - START_MONO, 2),
            "baseline_total_runtime_seconds": round(sum(float(r["runtime_seconds"]) for r in baseline_runtime), 3),
            "candidate_total_runtime_seconds": round(sum(float(r["runtime_seconds"]) for r in candidate_runtime), 3),
        },
        "limitations": [
            "Ten RT-1 / Fractal episodes only; not a standardized leaderboard result.",
            "One generated sample per checkpoint per episode.",
            "Only metrics available from RGB video pairs are scored; unsupported metrics remain N/A.",
            "Determinism depends on NanoWM/PyTorch/CUDA kernels; fixed seeds are used where supported.",
        ],
    }
    write_json(COMPACT / "comparison_summary.json", summary)
    provenance = {
        "created_at": STARTED_AT,
        "completed_at": summary["runtime"]["finished_at"],
        "model_family": MODEL_FAMILY,
        "baseline_checkpoint": BASELINE_REPO,
        "candidate_checkpoint": CANDIDATE_REPO,
        "baseline_revision": checkpoints["baseline"].get("revision"),
        "candidate_revision": checkpoints["candidate"].get("revision"),
        "dataset": "RT-1 / Fractal via LeRobot",
        "dataset_repo": DATASET_REPO,
        "episode_ids": EPISODES,
        "episode_selection_rule": "fixed consecutive RT-1 / Fractal episode ids 0 through 9, chosen before inference",
        "settings": SETTINGS,
        "worldbench_commit": WORLDBENCH_COMMIT,
        "worldbench_version": "0.3.0.dev0",
        "inference_environment": env.get("gpu"),
        "nanowm_commit": env.get("nano_commit"),
        "actual_data_root_stats": summary["data_root_stats_final"],
        "actual_hf_home_stats": summary["hf_home_stats_final"],
        "evaluation_command_baseline": "worldbench eval-batch --ground-truth checkpoint_validation/videos/ground_truth --predictions checkpoint_validation/videos/baseline --name nanowm-b2-rt1-50k --skip-context 4",
        "evaluation_command_candidate": "worldbench eval-batch --ground-truth checkpoint_validation/videos/ground_truth --predictions checkpoint_validation/videos/candidate --name nanowm-b2-rt1-300k --skip-context 4",
        "gate_command_strict": "worldbench gate --baseline baseline_batch_result.json --candidate candidate_batch_result.json",
        "gate_command_engineering": "worldbench gate --baseline baseline_batch_result.json --candidate candidate_batch_result.json --max-overall-drop 2 --max-metric-drop 5 --max-horizon-drop 5",
        "limitations": summary["limitations"],
    }
    write_json(PROVENANCE_PATH, provenance)
    return summary


def emit_bundle() -> None:
    names = [
        "baseline_batch_result.json",
        "candidate_batch_result.json",
        "strict_gate_result.json",
        "engineering_gate_result.json",
        "comparison_summary.json",
        "provenance.json",
        "checkpoint_metadata.json",
        "config_compatibility.json",
        "baseline_inference_runtime.json",
        "candidate_inference_runtime.json",
        "lerobot_backend.json",
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            path = COMPACT / name
            if path.exists():
                zf.write(path, arcname=name)
        if STATUS_PATH.exists():
            zf.write(STATUS_PATH, arcname="status.json")
    print("WORLDBENCH_RESULTS_B64_BEGIN", flush=True)
    print(base64.b64encode(buf.getvalue()).decode("ascii"), flush=True)
    print("WORLDBENCH_RESULTS_B64_END", flush=True)


def main() -> None:
    write_json(
        PROVENANCE_PATH,
        {
            "status": "plan_frozen_before_results",
            "created_at": STARTED_AT,
            "model_family": MODEL_FAMILY,
            "baseline_checkpoint": BASELINE_REPO,
            "candidate_checkpoint": CANDIDATE_REPO,
            "dataset_repo": DATASET_REPO,
            "episode_ids": EPISODES,
            "settings": SETTINGS,
        },
    )
    mark("plan_frozen", episodes=EPISODES, settings=SETTINGS)
    env = bootstrap_code()
    checkpoints = download_checkpoints()
    nano_dir = Path(env["nano_dir"])
    patch_lerobot_backend(nano_dir)
    runtime = load_runtime(nano_dir)
    baseline_cfg = prepare_cfg(runtime, str(checkpoints["baseline"]["config_path"]))
    candidate_cfg = prepare_cfg(runtime, str(checkpoints["candidate"]["config_path"]))
    check_config_compatibility(baseline_cfg, candidate_cfg)
    baseline_runtime = run_checkpoint(runtime, "baseline", BASELINE_NAME, baseline_cfg, str(checkpoints["baseline"]["weights_path"]), save_gt=True)
    candidate_runtime = run_checkpoint(runtime, "candidate", CANDIDATE_NAME, candidate_cfg, str(checkpoints["candidate"]["weights_path"]), save_gt=False)
    wb_paths = run_worldbench_eval()
    summary = summarize(env, checkpoints, baseline_runtime, candidate_runtime, wb_paths)
    mark("completed", strict_gate=summary["strict_gate_status"], engineering_gate=summary["engineering_gate_status"], overall_delta=summary["overall_delta"])
    emit_bundle()
    print(
        "WORLDBENCH_VALIDATION_DONE",
        json.dumps(
            {
                "baseline_overall": summary["baseline_overall"],
                "candidate_overall": summary["candidate_overall"],
                "overall_delta": summary["overall_delta"],
                "strict_gate": summary["strict_gate_status"],
                "engineering_gate": summary["engineering_gate_status"],
            },
            sort_keys=True,
        ),
        flush=True,
    )


try:
    main()
except Exception as exc:  # noqa: BLE001
    write_json(
        STATUS_PATH,
        {
            "stage": "failed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - START_MONO, 2),
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        },
    )
    print("WORLDBENCH_VALIDATION_FAILED", json.dumps({"error": repr(exc)}, sort_keys=True), flush=True)
    traceback.print_exc()
    try:
        emit_bundle()
    except Exception:
        pass
    raise
