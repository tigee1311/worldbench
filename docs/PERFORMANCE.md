# Performance

WorldBench currently prioritizes deterministic, inspectable evaluation over maximum throughput. Saved-video evaluation decodes full videos into memory before scoring. That keeps metric behavior simple and reproducible, but it can become expensive for long or high-resolution videos.

## Benchmark Harness

Run:

```bash
python -m benchmarks.performance --output artifacts/performance/latest.json
```

For a quick smoke test:

```bash
python -m benchmarks.performance --quick --output /tmp/worldbench-performance.json
```

The harness measures:

- wall-clock time
- peak `tracemalloc` memory
- frames per second
- scaling with frame count
- scaling with resolution
- batch overhead
- result serialization
- comparison image generation

No strict timing gate is enabled because normal CI runners vary significantly. The JSON output is intended as a baseline for manual regression review.

## Streaming Design Note

A streaming decoder could reduce peak memory for long videos, but it risks subtle semantic differences unless every metric receives the same aligned frame prefixes and resize behavior. The current safe path is to keep full-frame decoding in production and prototype chunked decoding separately with golden-result comparisons before enabling it.
