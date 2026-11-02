"""WER scoring stub (TK-012). Real normalization + jiwer scoring later."""


def normalize(text: str) -> str:
    """Lowercase + strip (placeholder for PRD 3.4.3 normalization)."""
    return text.lower().strip()


if __name__ == "__main__":
    print("TODO(TK-012): score benchmark outputs -> report.md + report.json")
