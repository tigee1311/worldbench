# Compatibility Matrix

WorldBench evaluates saved predicted visual futures. It does not run policies, execute real robots, or infer task success from video similarity.

| Model or output type | Status | Adapter required | Reason |
| --- | --- | --- | --- |
| Action-conditioned RGB video predictors | Directly compatible when predictions are saved as aligned frames or videos | Optional action adapter for action metrics | Core input is ground-truth RGB future plus predicted RGB future for the same episode. |
| Image-to-video robot models | Directly compatible for video-only metrics | Optional metadata adapter | Visual and temporal metrics can score aligned future videos; action metrics remain N/A without action semantics. |
| Latent models with RGB decoders | Compatible after decoding | Prediction-format adapter may be needed | WorldBench scores decoded RGB futures, not latent tensors. |
| Latent-only models | Unsupported for production scoring | Required, but only if a deterministic RGB decoder exists | No production metric consumes latent-only outputs. |
| State-trajectory models | Adapter required | Dataset or prediction adapter | State trajectories must be rendered or converted into an evaluated visual future; do not call the resulting score task success. |
| Action-only VLAs | Unsupported | Not sufficient | WorldBench requires predicted future observations. Action-only policies are outside scope. |
| 3D outputs | Adapter required | Prediction adapter | 3D predictions must be rendered to aligned RGB futures under a documented camera protocol. |
| Point clouds | Adapter required | Prediction adapter | Point clouds need deterministic rendering before video metrics can apply. |
| Occupancy grids | Adapter required | Prediction adapter | Occupancy predictions need deterministic rendering and documented alignment. |
| Simulator-rendered futures | Compatible when exported as videos | Dataset or prediction adapter may be needed | Saved simulator renders can be evaluated if they match fixed ground-truth episode horizons. |
| Real-robot closed-loop policies | Unsupported as a direct target | Not sufficient | Closed-loop task execution is a different evaluation problem. WorldBench may inspect saved prediction videos from such systems, not execute them. |
