# LeRobot Import

Install optional dependencies:

```bash
pip install "worldbench[lerobot,video]"
```

Import a public Hugging Face LeRobot dataset:

```bash
worldbench import-lerobot \
  --repo-id chocolat-nya/yaskawa-untangle-dataset \
  --episodes 0:1 \
  --camera observation.images.fixed_cam1 \
  --timeline video \
  --out datasets/yaskawa
```

The default `video` timeline exports unique camera frames, aligns the latest action at or before each video timestamp, and aligns the nearest state timestamp. The `control` timeline exports every control row and may repeat camera frames. Source indices, timestamps, FPS, camera key, episode index, and alignment strategy are recorded in metadata.

Raw numeric actions are imported without pretending their semantics are known. Action Consistency remains `N/A` until a compatible adapter is supplied. The legacy local LeRobot-style converter remains supported; `import-lerobot --demo` is deprecated and exists only for deterministic development fixtures.

Validation methodology for the public Yaskawa import is documented in [real data validation](real_data_validation.md).
