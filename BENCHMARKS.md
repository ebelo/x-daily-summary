# Community Benchmarks

Benchmark results from the community — which local model runs well on what hardware. Submit your own via a pull request.

> **How to contribute:** Add a row to the table below with your hardware and results, then open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions.

---

## 🖥️ Benchmark Results

| Machine | CPU | RAM | GPU / VRAM | OS | Model | Posts | Time | Notes |
|---|---|---|---|---|---|---|---|---|
| Lenovo ThinkPad P14s (20VX0068MZ) | Intel i7-1165G7 @ 2.80GHz | 16 GB | NVIDIA T500 — 4GB VRAM | Windows 11 | `llama3.2:latest` (3B) | 839 | ~25 min | Full VRAM fit, no RAM spill |
| Lenovo ThinkPad P14s (20VX0068MZ) | Intel i7-1165G7 @ 2.80GHz | 16 GB | NVIDIA T500 — 4GB VRAM | Windows 11 | `mistral:latest` (7B) | 839 | Significantly longer | Partial RAM spill (model > VRAM) |

---

## 📋 Submission Template

Copy and fill in the row below, then open a PR against `main`:

```markdown
| <Machine name/model> | <CPU> | <RAM> | <GPU + VRAM, or "CPU only"> | <OS> | `<model:tag>` | <post count> | <time> | <notes> |
```

**Tips:**
- Run `nvidia-smi` (NVIDIA) or `rocm-smi` (AMD) to confirm GPU utilisation during inference.
- Note whether the model fits entirely in VRAM or spills to RAM — this is the single biggest performance factor.
- If running CPU-only, note the number of threads Ollama used (check `ollama ps`).
