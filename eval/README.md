# eval/

Benchmark harness, scoring scripts, and versioned results.

- `scripts/` — WER/DER scoring and reporting (TK-010, TK-012, TK-053).
  `score_wer.py` is a stub; real normalization + `jiwer` scoring lands later.
- `results/<version>/` — JSON + Markdown reports per benchmarked version.
- `data/` — **git-ignored**. Test clips, reference transcripts, consent forms
  live here or in private storage, never in git (TK-011).

Audio/data files must never be committed (see root `.gitignore`).
