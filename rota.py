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


def to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def team_text(shift, week_total):
    """Who else is on the bar that day, split into openers and closers."""
    open_from, open_to = (to_min(t) for t in CONFIG.get("opening_start_range", ["08:00", "10:30"]))
    close_from = to_min(CONFIG.get("closing_start_from", "14:00"))
    openers, closers, mids = [], [], []
    for p in sorted(shift.get("team", []), key=lambda p: p["start"]):
        line = f"• {p['name']} {p['start']}–{p['end']}" + (f" ({p['note']})" if p.get("note") else "")
        start = to_min(p["start"])
        if open_from <= start <= open_to:
            openers.append(line)
        elif start >= close_from:
            closers.append(line)
        else:
            mids.append(line)
    out = [f"You: {shift['start']}–{shift['end']} ({hm(shift['paid'])}) · week total {hm(week_total)}"]
    if shift.get("dm"):
        dms = sorted(shift["dm"], key=lambda d: d["start"])
        out += ["", "DM: " + " → ".join(f"{d['name']} {d['start']}–{d['end']}" for d in dms)]
    if openers:
        out += ["", f"OPENING bar (start {CONFIG.get('opening_start_range', ['08:00', '10:30'])[0]}–{CONFIG.get('opening_start_range', ['08:00', '10:30'])[1]})"] + openers
    if mids:
        out += ["", "MID"] + mids
    if closers:
        out += ["", f"CLOSING bar (start {CONFIG.get('closing_start_from', '14:00')} or later)"] + closers
    out += ["", "Added by rota-calendar."]
    return "\n".join(out)


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


def ics(shifts, week_total):
    def esc(t):
        return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

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
            f"DESCRIPTION:{esc(team_text(s, week_total))}",
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
    week_total = sum(s["paid"] for s in shifts)
    md = table(week, shifts)
    events = [
        {
            "summary": CONFIG.get("event_title", "Work shift") + (f" – {s['role']}" if s.get("role") else ""),
            "start": f"{s['start_dt']:%Y-%m-%dT%H:%M:%S}",
            "end": f"{s['end_dt']:%Y-%m-%dT%H:%M:%S}",
            "colorId": CONFIG.get("google_color_id", "3"),
            "location": CONFIG.get("location", ""),
            "description": team_text(s, week_total),
        }
        for s in shifts
    ]
    path.with_suffix(".md").write_text(md)
    path.with_suffix(".ics").write_text(ics(shifts, week_total))
    path.with_suffix(".events.json").write_text(json.dumps(events, indent=2, ensure_ascii=False))
    print(md)
    for e in events:
        print(f"--- {e['start'][:10]} ---\n{e['description']}\n")
    print(f"Wrote {path.with_suffix('.md')} and {path.with_suffix('.ics')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 rota.py weeks/YYYY-MM-DD.json")
    main(sys.argv[1])
