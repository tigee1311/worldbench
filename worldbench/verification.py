"""Verification for saved WorldBench result artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from worldbench.provenance import sha256_file, sha256_json
from worldbench.runners.evaluator import default_metrics
from worldbench.utils import read_json_limited
from worldbench.version import RESULT_SCHEMA_VERSION, WORLD_BENCH_VERSION

MAX_VERIFY_JSON_BYTES = 50 * 1024 * 1024
SUPPORTED_RESULT_SCHEMA_VERSIONS = {"1", RESULT_SCHEMA_VERSION}


class VerificationIssue(BaseModel):
    severity: Literal["error", "warning"]
    message: str
    code: str | None = None


class VerificationResult(BaseModel):
    status: Literal[
        "verified",
        "partially_verified",
        "not_verifiable",
        "verification_failed",
    ]
    result_path: str
    result_type: str | None = None
    checked_input_files: int = 0
    issues: list[VerificationIssue]

    @property
    def exit_code(self) -> int:
        return {
            "verified": 0,
            "verification_failed": 1,
            "not_verifiable": 2,
            "partially_verified": 3,
        }[self.status]

    @property
    def errors(self) -> list[VerificationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[VerificationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def verify_result_file(path: str | Path) -> VerificationResult:
    result_path = Path(path)
    issues: list[VerificationIssue] = []
    try:
        payload = read_json_limited(result_path, max_bytes=MAX_VERIFY_JSON_BYTES)
    except Exception as exc:
        issues.append(
            VerificationIssue(
                severity="error",
                code="invalid_json",
                message=f"Could not read JSON: {exc}",
            )
        )
        return _finish(result_path, None, 0, issues)

    if not isinstance(payload, dict):
        issues.append(
            VerificationIssue(
                severity="error",
                code="invalid_structure",
                message="Result JSON must be an object.",
            )
        )
        return _finish(result_path, None, 0, issues)

    result_type = payload.get("result_type")
    if result_type not in {"evaluation", "batch_evaluation", "gate_comparison"}:
        issues.append(
            VerificationIssue(
                severity="error",
                code="unsupported_result_type",
                message=f"Unsupported or missing result_type: {result_type}",
            )
        )
        return _finish(
            result_path,
            str(result_type) if result_type is not None else None,
            0,
            issues,
        )

    if not _verify_schema_version(payload, issues):
        return _finish(
            result_path,
            str(result_type) if result_type is not None else None,
            0,
            issues,
        )

    _verify_package_version(payload, issues)
    _verify_configuration(payload, issues)
    _verify_metric_versions(payload, issues)
    checked = _verify_input_files(payload, result_path, issues)
    return _finish(
        result_path,
        str(result_type) if result_type is not None else None,
        checked,
        issues,
    )


def _finish(
    result_path: Path,
    result_type: str | None,
    checked_input_files: int,
    issues: list[VerificationIssue],
) -> VerificationResult:
    invalid_codes = {
        "invalid_json",
        "invalid_structure",
        "unsupported_result_type",
        "unsupported_schema_version",
    }
    if any(issue.code in invalid_codes for issue in issues):
        status = "not_verifiable"
    elif any(issue.severity == "error" for issue in issues):
        status = "verification_failed"
    elif issues:
        status = "partially_verified"
    else:
        status = "verified"
    return VerificationResult(
        status=status,
        result_path=str(result_path),
        result_type=result_type,
        checked_input_files=checked_input_files,
        issues=issues,
    )


def _verify_schema_version(
    payload: dict[str, Any], issues: list[VerificationIssue]
) -> bool:
    version = payload.get("schema_version")
    if version is None:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="schema_version_missing",
                message="schema_version is not recorded; treating artifact as legacy.",
            )
        )
        return True
    if str(version) not in SUPPORTED_RESULT_SCHEMA_VERSIONS:
        issues.append(
            VerificationIssue(
                severity="error",
                code="unsupported_schema_version",
                message=(
                    f"Unsupported schema_version '{version}'. This version supports "
                    f"schema versions {sorted(SUPPORTED_RESULT_SCHEMA_VERSIONS)}."
                ),
            )
        )
        return False
    return True


def _verify_package_version(
    payload: dict[str, Any], issues: list[VerificationIssue]
) -> None:
    recorded = payload.get("worldbench_version")
    if recorded is None:
        env = _provenance(payload).get("environment", {})
        if isinstance(env, dict):
            recorded = env.get("worldbench_version")
    if recorded is None:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="worldbench_version_missing",
                message="WorldBench version is not recorded.",
            )
        )
    elif str(recorded) != WORLD_BENCH_VERSION:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="worldbench_version_mismatch",
                message=(
                    f"WorldBench version mismatch: artifact {recorded}, "
                    f"installed {WORLD_BENCH_VERSION}."
                ),
            )
        )


def _verify_configuration(
    payload: dict[str, Any], issues: list[VerificationIssue]
) -> None:
    if "configuration_hash" not in payload:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="configuration_hash_missing",
                message="configuration_hash is missing.",
            )
        )
    config = payload.get("configuration")
    if config is None and payload.get("result_type") != "gate_comparison":
        issues.append(
            VerificationIssue(
                severity="error",
                code="configuration_missing",
                message="configuration is missing.",
            )
        )
    provenance = _provenance(payload)
    expected = provenance.get("report_configuration_sha256") or payload.get(
        "report_configuration_sha256"
    )
    if (
        payload.get("result_type") == "evaluation"
        and isinstance(config, dict)
        and expected
    ):
        if not _is_sha256_uri(expected):
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="configuration_hash_malformed",
                    message=f"Report configuration hash is malformed: {expected}.",
                )
            )
            return
        actual = sha256_json(config)
        if actual != expected:
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="configuration_hash_mismatch",
                    message=(
                        "Report configuration hash mismatch: "
                        f"recorded {expected}, computed {actual}."
                    ),
                )
            )
    elif payload.get("result_type") != "gate_comparison" and not expected:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="report_configuration_hash_missing",
                message="report_configuration_sha256 is not recorded.",
            )
        )


def _verify_metric_versions(
    payload: dict[str, Any], issues: list[VerificationIssue]
) -> None:
    recorded = _metric_plugins(payload)
    if not recorded:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="metric_plugin_versions_missing",
                message="Metric plugin versions are not recorded.",
            )
        )
        return
    installed = {
        metric.name: getattr(metric, "version", "unversioned")
        for metric in default_metrics()
    }
    for name, version in recorded.items():
        installed_version = installed.get(name)
        if installed_version is None:
            issues.append(
                VerificationIssue(
                    severity="warning",
                    code="metric_plugin_not_installed",
                    message=f"Metric plugin '{name}' is not a built-in installed metric.",
                )
            )
        elif str(installed_version) != str(version):
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="metric_plugin_version_mismatch",
                    message=(
                        f"Metric plugin version mismatch for {name}: "
                        f"artifact {version}, installed {installed_version}."
                    ),
                )
            )


def _verify_input_files(
    payload: dict[str, Any],
    result_path: Path,
    issues: list[VerificationIssue],
) -> int:
    checked = 0
    records = _input_files(payload)
    if not records and payload.get("result_type") in {
        "evaluation",
        "batch_evaluation",
    }:
        issues.append(
            VerificationIssue(
                severity="warning",
                code="input_file_provenance_missing",
                message="Input file provenance is not recorded.",
            )
        )
        return checked
    for record in records:
        role = str(record.get("role", "input"))
        expected_hash = record.get("sha256")
        display_path = record.get("path")
        if record.get("path_redacted"):
            issues.append(
                VerificationIssue(
                    severity="warning",
                    code="input_path_redacted",
                    message=f"{role} path was redacted; file existence and hash cannot be verified.",
                )
            )
            continue
        if not isinstance(display_path, str) or not display_path:
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="input_path_missing",
                    message=f"{role} path is missing.",
                )
            )
            continue
        candidate = _resolve_recorded_path(display_path, result_path)
        if candidate is None:
            issues.append(
                VerificationIssue(
                    severity="error",
                    code="input_file_missing",
                    message=f"{role} file does not exist: {display_path}",
                )
            )
            continue
        if isinstance(expected_hash, str):
            if not _is_sha256_uri(expected_hash):
                issues.append(
                    VerificationIssue(
                        severity="error",
                        code="input_hash_malformed",
                        message=f"{role} hash is malformed for {display_path}.",
                    )
                )
                continue
            actual_hash = sha256_file(candidate)
            checked += 1
            if actual_hash != expected_hash:
                issues.append(
                    VerificationIssue(
                        severity="error",
                        code="input_hash_mismatch",
                        message=(
                            f"{role} hash mismatch for {display_path}: "
                            f"recorded {expected_hash}, computed {actual_hash}."
                        ),
                    )
                )
        else:
            issues.append(
                VerificationIssue(
                    severity="warning",
                    code="input_hash_missing",
                    message=f"{role} hash is missing.",
                )
            )
    return checked


def _resolve_recorded_path(display_path: str, result_path: Path) -> Path | None:
    candidate = Path(display_path)
    if ".." in candidate.parts:
        return None
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.extend([Path.cwd() / candidate, result_path.parent / candidate])
    for item in candidates:
        if item.is_file():
            return item
    return None


def _provenance(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = payload.get("provenance", {})
    return provenance if isinstance(provenance, dict) else {}


def _metric_plugins(payload: dict[str, Any]) -> dict[str, str]:
    provenance = _provenance(payload)
    candidates = [provenance.get("metric_plugins"), payload.get("metric_plugins")]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return {str(name): str(version) for name, version in candidate.items()}
    return {}


def _input_files(payload: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = _provenance(payload)
    records = provenance.get("input_files")
    if isinstance(records, list):
        return [item for item in records if isinstance(item, dict)]
    if payload.get("result_type") == "batch_evaluation":
        collected: list[dict[str, Any]] = []
        for episode in payload.get("episodes", []):
            if isinstance(episode, dict) and isinstance(
                episode.get("input_files"), list
            ):
                collected.extend(
                    item for item in episode["input_files"] if isinstance(item, dict)
                )
        return collected
    return []


def _is_sha256_uri(value: object) -> bool:
    if not isinstance(value, str):
        return False
    prefix = "sha256:"
    if not value.startswith(prefix):
        return False
    digest = value[len(prefix) :]
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)
