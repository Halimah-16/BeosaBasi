"""Worker CLI scaffold. `doctor` subcommand stub (full checks in TK-005)."""

import argparse
import platform
import sys


def doctor_report() -> dict[str, str]:
    """Collect environment facts without touching secrets or hardware."""
    return {
        "status": "ok",
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worker", description="BeosaBasi worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check worker environment (stub, TK-005)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        # TODO(TK-005): GPU/VRAM, CUDA/cuDNN, ffmpeg/ffprobe, workdir,
        # HF token presence (never print), sleep guard, battery/thermal.
        report = doctor_report()
        print(f"worker doctor: {report['status']} "
              f"(python={report['python']}, platform={report['platform']})")
        print("TODO(TK-005): full hardware checks not implemented yet")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
