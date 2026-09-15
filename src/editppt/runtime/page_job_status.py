#!/usr/bin/env python3
import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from deck_run_state import (
    active_pages,
    dispatch_slots_available,
    dispatchable_pages,
    load_jobs,
    load_run_state,
    max_concurrent_pages,
    run_dir_from_target,
)


def main():
    parser = argparse.ArgumentParser(description="Print page job status without modifying run state.")
    parser.add_argument("run", help="Run directory or deck_manifest.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--events", type=int, default=5, metavar="N", help="Include the N most recent event summaries (default: 5). Use 0 to omit.")
    args = parser.parse_args()

    run_dir = run_dir_from_target(args.run)
    jobs = load_jobs(run_dir)
    state = load_run_state(run_dir)
    by_status = defaultdict(list)
    for page in jobs.get("pages", []):
        by_status[page.get("status", "unknown")].append(page.get("page_id"))
    summary = {
        "run_dir": str(run_dir),
        "run_status": state.get("status"),
        "page_count": len(jobs.get("pages", [])),
        "max_concurrent_pages": max_concurrent_pages(jobs),
        "active_dispatches": [page.get("page_id") for page in active_pages(jobs)],
        "dispatch_slots_available": dispatch_slots_available(jobs),
        "dispatchable_pages": [page.get("page_id") for page in dispatchable_pages(jobs)],
        "counts": dict(Counter(page.get("status", "unknown") for page in jobs.get("pages", []))),
        "pages": dict(sorted(by_status.items())),
    }
    events_path = run_dir / ".." / "events.jsonl"
    if not events_path.is_file():
        events_path = run_dir.parent / "events.jsonl"
    events = []
    if args.events > 0 and events_path.is_file():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines()[-args.events:]:
            try:
                item = json.loads(line).get("item", {})
                event = {"type": item.get("type"), "status": item.get("status")}
                if item.get("type") == "command_execution":
                    event["command"] = item.get("command")
                    event["exit_code"] = item.get("exit_code")
                elif item.get("type") == "agent_message":
                    event["text"] = item.get("text")
                events.append(event)
            except json.JSONDecodeError:
                continue
    summary["observability"] = {
        "events_file": str(events_path) if events_path.is_file() else None,
        "latest_event": events[-1] if events else None,
        "recent_events": events,
        "run_state_age_seconds": round(max(0.0, time.time() - (run_dir / "run_state.json").stat().st_mtime), 1) if (run_dir / "run_state.json").is_file() else None,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"run_dir={summary['run_dir']}")
    print(f"run_status={summary['run_status']}")
    print(f"max_concurrent_pages={summary['max_concurrent_pages']}")
    print(f"active_dispatches={', '.join(summary['active_dispatches']) if summary['active_dispatches'] else '-'}")
    print(f"dispatch_slots_available={summary['dispatch_slots_available']}")
    print(f"dispatchable_pages={', '.join(summary['dispatchable_pages']) if summary['dispatchable_pages'] else '-'}")
    obs = summary["observability"]
    print(f"run_state_age_seconds={obs['run_state_age_seconds']}")
    if obs["latest_event"]:
        latest = obs["latest_event"]
        print(f"latest_event={latest.get('type')} status={latest.get('status') or '-'}")
        if latest.get("command"):
            print(f"latest_command={latest['command']}")
        if latest.get("text"):
            print(f"latest_message={latest['text']}")
    for status, pages in summary["pages"].items():
        print(f"{status}: {', '.join(pages) if pages else '-'}")


if __name__ == "__main__":
    main()
