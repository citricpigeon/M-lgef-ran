#!/usr/bin/env python3
"""Turn one week of shifts (JSON read off a rota photo) into a table, totals and an .ics file.

Usage:  python3 rota.py weeks/2026-11-09.json
Writes: weeks/2026-11-09.md (table) and weeks/2026-11-09.ics (calendar import)

The AI only reads the photo into JSON. All the hour sums happen here, so they are always exact.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())


def parse_shift(s):
    start = datetime.strptime(f"{s['date']} {s['start']}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{s['date']} {s['end']}", "%Y-%m-%d %H:%M")
    if end <= start:  # late close, e.g. 18:00-00:30 finishes the next day
        end += timedelta(days=1)
    length = (end - start).total_seconds() / 3600
    unpaid = 0
    for rule in sorted(CONFIG.get("unpaid_break_rules", []), key=lambda r: r["min_shift_hours"]):
        if length >= rule["min_shift_hours"]:
            unpaid = rule["unpaid_minutes"]
    paid = length - unpaid / 60
    return {**s, "start_dt": start, "end_dt": end, "length": length, "unpaid_break_min": unpaid, "paid": paid}


def hm(hours):
    mins = round(hours * 60)
    return f"{mins // 60}h {mins % 60:02d}m"


def table(week, shifts):
    rows = [
        f"## Shifts for {CONFIG['name']} - w/c {week['week_commencing']}",
        "",
        "| Day | Date | Start | End | Role | Length | Unpaid break | Paid hours |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in shifts:
        end_label = s["end"] + (" (+1)" if s["end_dt"].date() > s["start_dt"].date() else "")
        rows.append(
            f"| {s['start_dt']:%a} | {s['start_dt']:%d %b} | {s['start']} | {end_label} | {s.get('role', '')} "
            f"| {hm(s['length'])} | {s['unpaid_break_min']}m | {hm(s['paid'])} |"
        )
    total_len = sum(s["length"] for s in shifts)
    total_paid = sum(s["paid"] for s in shifts)
    rows += ["", f"**{len(shifts)} shifts - {hm(total_len)} on site - {hm(total_paid)} paid**"]
    return "\n".join(rows) + "\n"


def ics(shifts):
    def esc(t):
        return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

    tz = CONFIG.get("timezone", "Europe/London")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//rota-calendar//EN", "CALSCALE:GREGORIAN"]
    for s in shifts:
        title = CONFIG.get("event_title", "Work shift") + (f" - {s['role']}" if s.get("role") else "")
        lines += [
            "BEGIN:VEVENT",
            # Stable UID: re-importing the same shift updates it instead of duplicating it
            f"UID:{s['start_dt']:%Y%m%dT%H%M}-rota-calendar@{CONFIG['name'].lower().replace(' ', '-')}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID={tz}:{s['start_dt']:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={tz}:{s['end_dt']:%Y%m%dT%H%M%S}",
            f"SUMMARY:{esc(title)}",
            f"DESCRIPTION:{esc('Paid ' + hm(s['paid']) + '. Added by rota-calendar.')}",
        ]
        if CONFIG.get("location"):
            lines.append(f"LOCATION:{esc(CONFIG['location'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main(path):
    path = Path(path)
    week = json.loads(path.read_text())
    shifts = sorted((parse_shift(s) for s in week["shifts"]), key=lambda s: s["start_dt"])
    md = table(week, shifts)
    path.with_suffix(".md").write_text(md)
    path.with_suffix(".ics").write_text(ics(shifts))
    print(md)
    print(f"Wrote {path.with_suffix('.md')} and {path.with_suffix('.ics')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 rota.py weeks/YYYY-MM-DD.json")
    main(sys.argv[1])
