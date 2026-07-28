# Second-Model Validation Plan

WorldBench currently has a committed NanoWM RT-1 validation artifact. A second unrelated model must be evaluated before claiming broader model-family readiness.

## Candidate Target

Primary candidate: iVideoGPT on BAIR robot pushing, if a compatible open checkpoint and inference path remain available under a usable license.

Fallback target: another public robotics video world model that can emit saved RGB future videos for deterministic episodes without paid compute.

## Requirements

- Source repository and paper link.
- License for code, checkpoint, and dataset.
- Exact checkpoint identifier.
- Exact dataset split and deterministic episode IDs.
- Fixed context length and prediction horizon.
- CPU or Apple Silicon feasible inference path, or a documented resource estimate below the project budget.
- No automatic model or dataset downloads during normal WorldBench package use.

## Run Protocol

1. Create a separate research workspace under `worldbench-research/worldbench-hardening`.
2. Fetch only the required public artifacts.
3. Record source URLs, licenses, checksums, and commands.
4. Generate baseline and candidate predictions only if two comparable checkpoints exist.
5. Run `eval-batch`, `gate`, and `verify-run`.
6. Commit only small JSON, Markdown, and chart artifacts.

## Success Criteria

- Inference succeeds on a deterministic episode subset.
- WorldBench pairs the same episodes across baseline and candidate outputs.
- Metric coverage is reported honestly.
- Any failure modes are documented without claiming benchmark superiority.

## Limitations

This plan does not prove scientific validity, external adoption, or real-robot task success. It is a repository-readiness step for testing WorldBench against a second model family.
