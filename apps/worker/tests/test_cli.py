from worker.cli import build_parser, doctor_report


def test_doctor_report_ok():
    assert doctor_report()["status"] == "ok"


def test_parser_has_doctor():
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"
