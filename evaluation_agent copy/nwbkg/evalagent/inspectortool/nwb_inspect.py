import argparse
from datetime import datetime
from pathlib import Path

from nwbinspector import inspect_nwbfile, format_messages, save_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect an NWB file and optionally save a text report.")
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to the .nwb file. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--report-file-path",
        "-r",
        dest="report_file_path",
        default=None,
        help="Path to write the formatted report as a .txt file",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite the report file if it already exists",
    )

    args = parser.parse_args()

    nwb_path = args.path
    if not nwb_path:
        try:
            nwb_path = input("Enter path to .nwb file: ").strip()
        except EOFError:
            print("No input provided for NWB file path.")
            return

    nwb_path_obj = Path(nwb_path)
    if not nwb_path_obj.exists() or not nwb_path_obj.is_file():
        print(f"File not found: {nwb_path_obj}")
        return

    messages = list(inspect_nwbfile(nwbfile_path=str(nwb_path_obj)))
    formatted = format_messages(messages=messages)

    if args.report_file_path:
        report_path = Path(args.report_file_path)
    else:
        report_path = Path(__file__).parent / "nwb_inspector_report.txt"

    # If default path exists and overwrite not requested, create a timestamped filename
    if report_path.exists() and not args.overwrite:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_path.with_name(f"{report_path.stem}_{timestamp}{report_path.suffix}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    save_report(report_file_path=str(report_path), formatted_messages=formatted, overwrite=args.overwrite)
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()