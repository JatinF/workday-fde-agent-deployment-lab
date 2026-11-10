"""Command line for preflight, the troubleshooting suite, and the local API."""

from __future__ import annotations

import argparse
import json

from fde_lab.gates import all_gates
from fde_lab.load import load_package
from fde_lab.log import configure_logging
from fde_lab.models import InvokeRequest
from fde_lab.paths import repo_root
from fde_lab.preflight import preflight
from fde_lab.runtime import Runtime
from fde_lab.story import format_story, run_story
from fde_lab.suite import format_report, run_suite


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="fde-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("run-suite")
    sub.add_parser("run-story")
    sub.add_parser("gates")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    invoke = sub.add_parser("invoke")
    invoke.add_argument("--actor", required=True)
    invoke.add_argument("--skill", required=True)
    invoke.add_argument("--worker", required=True)
    invoke.add_argument("--hours", type=int)
    invoke.add_argument("--request-id")
    args = parser.parse_args(argv)
    if args.command == "preflight":
        findings = preflight(load_package())
        for finding in findings:
            print(finding.severity + " " + finding.code + " " + finding.message)
        errors = [item for item in findings if item.severity == "error"]
        print("findings=" + str(len(findings)) + " errors=" + str(len(errors)))
        return 1 if errors else 0
    if args.command == "gates":
        print(json.dumps([gate.model_dump() for gate in all_gates()], indent=2))
        return 0
    if args.command == "run-suite":
        report = run_suite()
        destination = repo_root() / "reports"
        destination.mkdir(exist_ok=True)
        (destination / "suite_results.json").write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (destination / "suite_results.md").write_text(format_report(report), encoding="utf-8")
        print(
            "cases="
            + str(report.case_count)
            + " passed="
            + str(report.passed)
            + " failed="
            + str(report.failed)
            + " leaks="
            + str(report.token_leak_count)
            + " duration_ms="
            + str(report.suite_duration_ms)
        )
        return 1 if report.failed or report.token_leak_count else 0
    if args.command == "run-story":
        story = run_story()
        destination = repo_root() / "reports"
        destination.mkdir(exist_ok=True)
        (destination / "field_story.json").write_text(
            story.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (destination / "field_story.md").write_text(format_story(story), encoding="utf-8")
        print(
            "checks="
            + str(story.passed + story.failed)
            + " passed="
            + str(story.passed)
            + " failed="
            + str(story.failed)
            + " duration_ms="
            + str(story.duration_ms)
        )
        return 1 if story.failed else 0
    if args.command == "invoke":
        arguments: dict[str, str | int] = {"worker_id": args.worker}
        if args.skill == "request-coverage":
            if args.hours is None or not args.request_id:
                print("request-coverage requires --hours and --request-id")
                return 2
            arguments["hours"] = args.hours
            arguments["time_off_type_wid"] = "fde00000000000000000000000000031"
            arguments["client_request_id"] = args.request_id
        trace = Runtime.load().invoke(
            InvokeRequest(actor_id=args.actor, skill=args.skill, arguments=arguments)
        )
        print(trace.model_dump_json())
        return 0 if trace.failure_class.value == "ok" else 1
    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "fde_lab.api:create_app",
            factory=True,
            host=args.host,
            port=args.port,
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
