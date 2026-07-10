from pathlib import Path

from worldbench.backends.demo import DemoBackend
from worldbench.dataset import load_dataset, validate_dataset


def test_demo_dataset_validates(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")

    report = validate_dataset(dataset_path)

    assert report.is_valid
    assert report.episode_count == 2
    assert report.frame_count > 0


def test_load_dataset_reads_episodes(tmp_path: Path) -> None:
    dataset_path = DemoBackend().create(tmp_path / "demo")

    dataset = load_dataset(dataset_path)

    assert len(dataset) == 2
    assert dataset.episodes[0].actions
    assert dataset.episodes[0].states
    assert dataset.episodes[0].frames
