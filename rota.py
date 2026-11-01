#!/usr/bin/env python3
"""Turn one week of shifts (JSON read off a rota photo) into a table, totals and calendar files.

Usage:  python3 rota.py weeks/2026-11-09.json
Writes: weeks/2026-11-09.md           table of shifts, meetings and totals
        weeks/2026-11-09.ics          calendar file for any calendar app
        weeks/2026-11-09.events.json  ready-to-create Google Calendar events

The AI only reads the photo into JSON. All the hour sums happen here, so they are always exact.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())


def parse_times(date, start, end):
    s = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
    e = datetime.strptime(f"{date} {end}", "%Y-%m-%d %H:%M")
    if e <= s:  # late close, e.g. 18:00-00:30 finishes the next day
        e += timedelta(days=1)
    return s, e


def parse_shift(s):
    start, end = parse_times(s["date"], s["start"], s["end"])
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


def hm(hours):
    mins = round(hours * 60)
    return f"{mins // 60}h {mins % 60:02d}m"


def explain(note, drop_plus=False):
    """Turn rota codes into words, e.g. 'DC' -> 'DC – deep clean'.
    Codes listed under unknown_codes are marked as not known yet; anything else is kept as printed.
    drop_plus leaves out '+' when the next shift is already shown separately."""
    if not note:
        return ""
    codes = {k.upper(): v for k, v in CONFIG.get("codes", {}).items()}
    unknown = {k.upper() for k in CONFIG.get("unknown_codes", {})}
    words = []
    for part in note.replace(",", " ").split():
        key = part.upper()
        if key == "+" and drop_plus:
            continue
        if key in codes:
            words.append(f"{key} – {codes[key]}")
        elif key in unknown:
            words.append(f"{key} – meaning not known yet")
        else:
            words.append(part)
    return ", ".join(words)


def then_text(p):
    """For a '+' shift: where the person goes next, if the rota shows it."""
    t = p.get("then")
    if t:
        return f"then {t['section']} {t['start']}–{t['end']}"
    return ""


def person_line(p):
    extras = [x for x in (explain(p.get("note", ""), drop_plus=bool(p.get("then"))), then_text(p)) if x]
    return f"• {p['name']} {p['start']}–{p['end']}" + (f" ({'; '.join(extras)})" if extras else "")


def shift_description(shift, all_shifts, week_total):
    """Event text: Will's hours, anything else he's on that day, the DM, and the bar team split into openers and closers."""
    open_from, open_to = (to_min(t) for t in CONFIG.get("opening_start_range", ["08:00", "10:30"]))
    close_from = to_min(CONFIG.get("closing_start_from", "14:00"))
    openers, closers, mids = [], [], []
    for p in sorted(shift.get("team", []), key=lambda p: p["start"]):
        start = to_min(p["start"])
        if open_from <= start <= open_to:
            openers.append(person_line(p))
        elif start >= close_from:
            closers.append(person_line(p))
        else:
            mids.append(person_line(p))

    out = [f"You: {shift['start']}–{shift['end']} ({hm(shift['paid'])}) · week total {hm(week_total)}"]
    task = explain(shift.get("note", ""), drop_plus=True)
    if task:
        out.append(f"Your task: {task}")
    same_day = [s for s in all_shifts if s["date"] == shift["date"] and s is not shift]
    if same_day:
        for s in same_day:
            if s["start_dt"] >= shift["end_dt"]:
                word = "Then"
            elif s["end_dt"] <= shift["start_dt"]:
                word = "Before this"
            else:
                word = "Also today"
            out.append(f"{word}: {s.get('role', '')} {s['start']}–{s['end']}")
        day_total = shift["paid"] + sum(s["paid"] for s in same_day)
        out.append(f"Day total: {hm(day_total)}")
    elif "+" in (shift.get("note") or ""):
        out.append("Then: somewhere else after this. Not found on the rota, so check the sheet.")
    if shift.get("dm"):
        dms = sorted(shift["dm"], key=lambda d: d["start"])
        out += ["", "DM: " + " → ".join(f"{d['name']} {d['start']}–{d['end']}" for d in dms)]
    section = (shift.get("role") or "bar").lower()
    rng = CONFIG.get("opening_start_range", ["08:00", "10:30"])
    if openers:
        out += ["", f"OPENING {section} (start {rng[0]}–{rng[1]})"] + openers
    if mids:
        out += ["", "MID"] + mids
    if closers:
        out += ["", f"CLOSING {section} (start {CONFIG.get('closing_start_from', '14:00')} or later)"] + closers
    out += ["", "Added by rota-calendar."]
    return "\n".join(out)


def meeting_events(week):
    """Staff meetings printed on the rota become their own red events, whether or not Will is working that day."""
    events = []
    for m in week.get("meetings", []):
        start, end = parse_times(m["date"], m["start"], m["end"])
        title = m.get("title", "Staff meeting") + (" (attend one)" if m.get("choose_one") else "")
        desc = ["From the rota."]
        if m.get("choose_one"):
            desc.append("The rota lists more than one session. You only need to attend one.")
        if m.get("note"):
            desc.append(m["note"])
        desc += ["", "Added by rota-calendar."]
        events.append({"kind": "meeting", "summary": title, "start_dt": start, "end_dt": end,
                       "colorId": CONFIG.get("meeting_color_id", "11"), "description": "\n".join(desc)})
    return events


def table(week, shifts, meetings):
    # Hours are clock-on to clock-off. Break columns only appear if break rules are switched on in config.
    breaks = bool(CONFIG.get("unpaid_break_rules"))
    head = "| Day | Date | Start | End | Role | Hours | Task |" + (" Unpaid break | Paid hours |" if breaks else "")
    rows = [
        f"## Shifts for {CONFIG['name']} - w/c {week['week_commencing']}",
        "",
        head,
        "|" + "---|" * (head.count("|") - 1),
    ]
    for s in shifts:
        end_label = s["end"] + (" (+1)" if s["end_dt"].date() > s["start_dt"].date() else "")
        row = (
            f"| {s['start_dt']:%a} | {s['start_dt']:%d %b} | {s['start']} | {end_label} | {s.get('role', '')} "
            f"| {hm(s['length'])} | {explain(s.get('note', ''))} |"
        )
        if breaks:
            row += f" {s['unpaid_break_min']}m | {hm(s['paid'])} |"
        rows.append(row)
    total_len = sum(s["length"] for s in shifts)
    total_paid = sum(s["paid"] for s in shifts)
    total = f"**{len(shifts)} shifts - {hm(total_len)}**" if not breaks else f"**{len(shifts)} shifts - {hm(total_len)} on site - {hm(total_paid)} paid**"
    rows += ["", total]
    if meetings:
        rows += ["", "### Staff meetings", ""]
        rows += [f"- {m['start_dt']:%a %d %b} {m['start_dt']:%H:%M}–{m['end_dt']:%H:%M}: {m['summary']}" for m in meetings]
    return "\n".join(rows) + "\n"


def ics(events):
    def esc(t):
        return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    tz = CONFIG.get("timezone", "Europe/London")
    who = CONFIG["name"].lower().replace(" ", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//rota-calendar//EN", "CALSCALE:GREGORIAN"]
    for e in events:
        lines += [
            "BEGIN:VEVENT",
            # Stable UID: re-importing the same shift or meeting updates it instead of duplicating it
            f"UID:{e['start_dt']:%Y%m%dT%H%M}-{e['kind']}-rota-calendar@{who}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID={tz}:{e['start_dt']:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={tz}:{e['end_dt']:%Y%m%dT%H%M%S}",
            f"SUMMARY:{esc(e['summary'])}",
            f"DESCRIPTION:{esc(e['description'])}",
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
    shift_events = [
        {
            "kind": "shift",
            "summary": CONFIG.get("event_title", "Work shift") + (f" – {s['role']}" if s.get("role") else ""),
            "start_dt": s["start_dt"],
            "end_dt": s["end_dt"],
            "colorId": CONFIG.get("google_color_id", "3"),
            "description": shift_description(s, shifts, week_total),
        }
        for s in shifts
    ]
    meetings = meeting_events(week)
    events = sorted(shift_events + meetings, key=lambda e: e["start_dt"])

    path.with_suffix(".md").write_text(table(week, shifts, meetings))
    path.with_suffix(".ics").write_text(ics(events))
    path.with_suffix(".events.json").write_text(json.dumps([
        {"kind": e["kind"], "summary": e["summary"],
         "start": f"{e['start_dt']:%Y-%m-%dT%H:%M:%S}", "end": f"{e['end_dt']:%Y-%m-%dT%H:%M:%S}",
         "colorId": e["colorId"], "location": CONFIG.get("location", ""), "description": e["description"]}
        for e in events
    ], indent=2, ensure_ascii=False))

    print(path.with_suffix(".md").read_text())
    for e in events:
        print(f"--- {e['kind']} {e['start_dt']:%Y-%m-%d %H:%M} · colour {e['colorId']} ---\n{e['description']}\n")
    print(f"Wrote {path.with_suffix('.md')}, {path.with_suffix('.ics')} and {path.with_suffix('.events.json')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 rota.py weeks/YYYY-MM-DD.json")
    main(sys.argv[1])
