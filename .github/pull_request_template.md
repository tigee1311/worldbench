## Summary

## Scope

- [ ] Preserves same-episode baseline-versus-candidate regression semantics.
- [ ] Does not silently change production metric formulas or weights.
- [ ] Does not claim task success, accuracy, adoption, or external validation without evidence.
- [ ] Does not add datasets, model weights, credentials, or large generated artifacts.

## Validation

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check worldbench tests examples
python -m mypy
```

## Notes For Reviewers
