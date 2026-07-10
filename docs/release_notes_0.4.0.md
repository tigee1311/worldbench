# WorldBench 0.4.0 Release Notes (Draft)

WorldBench 0.4.0 sharpens the product around regression testing for robot world-model checkpoints.

The release introduces schema-v2 Composite Score transparency, project configuration in `worldbench.yml`, configuration and dataset identities, coverage-safe gates, Markdown batch/gate evidence, and a complete CI example. Legacy schema-v1 evaluation and batch artifacts remain loadable, but old comparisons cannot provide complete configuration-compatibility guarantees. The former synthetic demo and benchmark commands are hidden and deprecated rather than removed abruptly.

The public proof remains the unchanged NanoWM-B/2 comparison on the same 10 RT-1 episodes: 50k baseline 85.67, 300k candidate 87.28, `+1.61`, 9 improved, 1 regressed, PASS. Only Visual Similarity and Temporal Stability were supported.

See [migration guidance](MIGRATION_V0_4.md) for field compatibility and stricter gate behavior.
