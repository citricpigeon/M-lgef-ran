#!/usr/bin/env python3
"""Turn one week of shifts (JSON read off a rota photo) into a table, totals and calendar files.

Usage:  python3 rota.py weeks/2026-11-09.json
Writes: weeks/2026-11-09.md           table of shifts, meetings and totals
        weeks/2026-11-09.ics          calendar file for any calendar app
        weeks/2026-11-09.events.json  ready-to-create Google Calendar events

The AI only reads the photo into JSON. All the hour sums happen here, so they are always exact.

Events it makes:
  shift    purple, one per shift of Will's
  dayoff   light green 12:00-13:00 on each day Will isn't working: DM, bar team and the rest of the building
  meeting  blue, for staff meetings on a day off or before Will's shift starts.
           A meeting that starts at or after the start of Will's shift goes into that shift's event instead.

An event marked "hold" is missing something (for example where someone goes after a '+').
It is never made up: the run asks Will, or a scheduled run leaves that day out until he answers.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())
IGNORED_AREAS = set(CONFIG.get("ignore_areas", []))  # sections left off events until Will knows what they are
FOOTER = "Added by rota-calendar."


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


def has_plus(p):
    return "+" in (p.get("note") or "")


def then_text(p):
    """For a '+' shift: where the person goes next, if the rota shows it."""
    t = p.get("then")
    if t:
        return f"then {t['section']} {t['start']}–{t['end']}"
    if has_plus(p):
        return "then another area, not on the rota yet"
    return ""


def person_line(p):
    extras = [x for x in (explain(p.get("note", ""), drop_plus=has_plus(p)), then_text(p)) if x]
    times = f" {p['start']}–{p['end']}" if p.get("start") and p.get("end") else ""
    return f"• {p['name']}{times}" + (f" ({'; '.join(extras)})" if extras else "")


def missing_then(people):
    """Names of people with '+' whose second area isn't recorded. These are asked about, never guessed."""
    return [p["name"] for p in people if has_plus(p) and not p.get("then")]


def dm_lines(dm):
    if not dm:
        return []
    dms = sorted(dm, key=lambda d: d["start"])
    return ["", "DM: " + " → ".join(f"{d['name']} {d['start']}–{d['end']}" for d in dms)]


def team_lines(team, section):
    """Bar team (or whichever section) split into openers, mids and closers."""
    rng = CONFIG.get("opening_start_range", ["08:00", "10:30"])
    open_from, open_to = (to_min(t) for t in rng)
    close_at = CONFIG.get("closing_start_from", "14:00")
    openers, closers, mids = [], [], []
    for p in sorted(team or [], key=lambda p: p["start"]):
        start = to_min(p["start"])
        if open_from <= start <= open_to:
            openers.append(person_line(p))
        elif start >= to_min(close_at):
            closers.append(person_line(p))
        else:
            mids.append(person_line(p))
    out = []
    if openers:
        out += ["", f"OPENING {section} (start {rng[0]}–{rng[1]})"] + openers
    if mids:
        out += ["", "MID"] + mids
    if closers:
        out += ["", f"CLOSING {section} (start {close_at} or later)"] + closers
    return out


def uncovered_hours(start, end, shifts):
    """Hours of [start, end) not already inside one of Will's shifts, so time is never counted twice."""
    mins = 0
    t = start
    while t < end:
        if not any(s["start_dt"] <= t < s["end_dt"] for s in shifts):
            mins += 1
        t += timedelta(minutes=1)
    return mins / 60


def plan_meetings(week, shifts):
    """Decide where each staff meeting goes and how many hours it adds.

    - Day off: its own blue event, with just the meeting on it.
    - Working day, meeting starts before Will's first shift: its own blue event with the meeting's times.
    - Working day, Will is already in when it starts (or it's later in the day): written into that shift's event.
    Meeting time counts towards the week, minus any part already inside a shift.
    "Attend one" sessions count once, using the session that adds the least time."""
    planned = []
    for m in week.get("meetings", []):
        start, end = parse_times(m["date"], m["start"], m["end"])
        today = [s for s in shifts if s["date"] == m["date"]]
        extra = uncovered_hours(start, end, today) if CONFIG.get("count_meetings_in_hours", True) else 0
        if not today:
            where = "day off"
            host = None
        elif start < min(s["start_dt"] for s in today):
            where = "before shift"
            host = None
        else:
            where = "in shift"
            host = max((s for s in today if s["start_dt"] <= start), key=lambda s: s["start_dt"])
        planned.append({**m, "start_dt": start, "end_dt": end, "where": where, "host": host, "extra": extra})

    # Hours: normal meetings count in full (less overlap); attend-one groups count once
    counted = sum(p["extra"] for p in planned if not p.get("choose_one"))
    groups = {}
    for p in planned:
        if p.get("choose_one"):
            groups.setdefault(p.get("title", "Staff meeting"), []).append(p)
    for sessions in groups.values():
        cheapest = min(sessions, key=lambda p: p["extra"])
        counted += cheapest["extra"]
        for p in sessions:
            p["counted"] = p is cheapest
    for p in planned:
        p.setdefault("counted", not p.get("choose_one"))
    return planned, counted


def meeting_label(m):
    return m.get("title", "Staff meeting") + (" (attend one)" if m.get("choose_one") else "")


def meeting_in_shift_line(m, shift):
    if m["start_dt"] >= shift["end_dt"]:
        when = "after this shift"
    elif m["end_dt"] <= shift["end_dt"]:
        when = "during this shift"
    else:
        when = "starts during this shift"
    return f"{meeting_label(m)}: {m['start']}–{m['end']} ({when})"


def shift_description(shift, all_shifts, week_total, meetings):
    """Event text: Will's hours, anything else he's on that day, meetings, the DM and the bar team."""
    out = [f"You: {shift['start']}–{shift['end']} ({hm(shift['paid'])}) · week total {hm(week_total)}"]
    task = explain(shift.get("note", ""), drop_plus=True)
    if task:
        out.append(f"Your task: {task}")
    same_day = [s for s in all_shifts if s["date"] == shift["date"] and s is not shift]
    mine = [m for m in meetings if m["host"] is shift]
    out += [meeting_in_shift_line(m, shift) for m in mine]
    for s in same_day:
        if s["start_dt"] >= shift["end_dt"]:
            word = "Then"
        elif s["end_dt"] <= shift["start_dt"]:
            word = "Before this"
        else:
            word = "Also today"
        out.append(f"{word}: {s.get('role', '')} {s['start']}–{s['end']}")
    if not same_day and has_plus(shift):
        out.append("Then: another area after this. It isn't on the rota yet, so this day is waiting on you.")
    day_meetings = [m for m in meetings if m["date"] == shift["date"] and m["counted"]]
    if same_day or any(m["extra"] for m in day_meetings):
        day_total = shift["paid"] + sum(s["paid"] for s in same_day) + sum(m["extra"] for m in day_meetings)
        out.append(f"Day total: {hm(day_total)}")
    out += dm_lines(shift.get("dm"))
    out += team_lines(shift.get("team"), (shift.get("role") or "bar").lower())
    out += ["", FOOTER]
    return "\n".join(out)


def dayoff_description(day, meetings):
    """Day-off event text: who's DM, the bar team, and everyone else in the building with their times."""
    out = ["Day off. This isn't a shift and isn't counted in your hours."]
    for m in meetings:
        if m["date"] == day["date"]:
            out.append(f"{meeting_label(m)}: {m['start']}–{m['end']} (see the blue event)")
    out += dm_lines(day.get("dm"))
    out += team_lines(day.get("team"), CONFIG.get("day_off_event", {}).get("section", "bar"))
    areas = {k: v for k, v in (day.get("areas") or {}).items() if v and k not in IGNORED_AREAS}
    if areas:
        out += ["", "ELSEWHERE IN THE BUILDING"]
        for area, people in areas.items():
            out.append(area)
            out += [person_line(p) for p in sorted(people, key=lambda p: p.get("start") or "")]
    out += ["", FOOTER]
    return "\n".join(out)


def week_dates(week):
    first = datetime.strptime(week["week_commencing"], "%Y-%m-%d")
    return [(first + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]


def table(week, shifts, meetings, week_total, days_off, holds):
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
    meeting_hours = sum(m["extra"] for m in meetings if m["counted"])
    total_len = sum(s["length"] for s in shifts) + meeting_hours
    total_paid = week_total
    label = f"{len(shifts)} shifts"
    if meeting_hours:
        label += f" + staff meetings ({hm(meeting_hours)})"
    total = f"**{label} - {hm(total_len)}**" if not breaks else f"**{label} - {hm(total_len)} on site - {hm(total_paid)} paid**"
    rows += ["", total]
    if meetings:
        rows += ["", "### Staff meetings", ""]
        for m in meetings:
            where = {"day off": "own blue event (day off)", "before shift": "own blue event (before your shift)",
                     "in shift": "in your shift's event"}[m["where"]]
            if not m["counted"]:
                count = "not counted (another session is)"
            elif m["extra"]:
                count = f"adds {hm(m['extra'])}"
            else:
                count = "inside your shift, no extra hours"
            rows.append(f"- {m['start_dt']:%a %d %b} {m['start']}–{m['end']}: {meeting_label(m)} · {where} · {count}")
    if days_off:
        rows += ["", "### Days off", ""]
        rows += [f"- {datetime.strptime(d, '%Y-%m-%d'):%a %d %b}" for d in days_off]
    if holds:
        rows += ["", "### Waiting on you", ""]
        rows += [f"- {datetime.strptime(d, '%Y-%m-%d'):%a %d %b}: {'; '.join(r)}" for d, r in sorted(holds.items())]
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
    meetings, meeting_hours = plan_meetings(week, shifts)
    week_total = sum(s["paid"] for s in shifts) + meeting_hours

    # Anything missing is held and asked about, never guessed
    holds = {}
    for s in shifts:
        if has_plus(s) and not any(o["date"] == s["date"] and o is not s for o in shifts):
            holds.setdefault(s["date"], []).append("where you go after your '+' shift")
        names = missing_then(s.get("team") or [])
        if names:
            holds.setdefault(s["date"], []).append("second area after '+' for " + ", ".join(names))

    worked = {s["date"] for s in shifts}
    days_off = [d for d in week_dates(week) if d not in worked]
    recorded = {d["date"]: d for d in week.get("days_off", [])}
    cfg = {"title": "Day off – who's in", "start": "12:00", "end": "13:00", "color_id": "2", **CONFIG.get("day_off_event", {})}

    events = []
    for s in shifts:
        events.append({
            "kind": "shift",
            "summary": CONFIG.get("event_title", "Work shift") + (f" – {s['role']}" if s.get("role") else ""),
            "start_dt": s["start_dt"], "end_dt": s["end_dt"],
            "colorId": CONFIG.get("google_color_id", "3"),
            "description": shift_description(s, shifts, week_total, meetings),
        })
    for d in days_off:
        day = recorded.get(d, {"date": d})
        if d not in recorded:
            holds.setdefault(d, []).append("who's in wasn't read from the rota for this day off")
        names = missing_then((day.get("team") or []) + [p for a, ps in (day.get("areas") or {}).items() if a not in IGNORED_AREAS for p in ps])
        if names:
            holds.setdefault(d, []).append("second area after '+' for " + ", ".join(names))
        start, end = parse_times(d, cfg["start"], cfg["end"])
        events.append({"kind": "dayoff", "summary": cfg["title"], "start_dt": start, "end_dt": end,
                       "colorId": cfg["color_id"], "description": dayoff_description(day, meetings)})
    for m in meetings:
        if m["where"] == "in shift":
            continue
        desc = [] if m["where"] == "day off" else [f"{m['start']}–{m['end']}, before your shift."]
        if m.get("choose_one"):
            desc.append("The rota lists more than one session. You only need to attend one.")
        if m.get("note"):
            desc.append(m["note"])
        desc += ([""] if desc else []) + [FOOTER]
        events.append({"kind": "meeting", "summary": meeting_label(m), "start_dt": m["start_dt"], "end_dt": m["end_dt"],
                       "colorId": CONFIG.get("meeting_color_id", "9"), "description": "\n".join(desc)})

    for e in events:
        held = holds.get(f"{e['start_dt']:%Y-%m-%d}") if e["kind"] != "meeting" else None
        if held:
            e["hold"] = "; ".join(held)
    events.sort(key=lambda e: e["start_dt"])

    path.with_suffix(".md").write_text(table(week, shifts, meetings, week_total, days_off, holds))
    path.with_suffix(".ics").write_text(ics([e for e in events if not e.get("hold")]))
    out = []
    for e in events:
        item = {"kind": e["kind"], "summary": e["summary"],
                "start": f"{e['start_dt']:%Y-%m-%dT%H:%M:%S}", "end": f"{e['end_dt']:%Y-%m-%dT%H:%M:%S}",
                "colorId": e["colorId"], "location": CONFIG.get("location", ""), "description": e["description"]}
        if e.get("hold"):
            item["hold"] = e["hold"]
        out.append(item)
    path.with_suffix(".events.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(path.with_suffix(".md").read_text())
    for e in events:
        flag = f" · HELD: {e['hold']}" if e.get("hold") else ""
        print(f"--- {e['kind']} {e['start_dt']:%Y-%m-%d %H:%M} · colour {e['colorId']}{flag} ---\n{e['description']}\n")
    print(f"Wrote {path.with_suffix('.md')}, {path.with_suffix('.ics')} and {path.with_suffix('.events.json')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 rota.py weeks/YYYY-MM-DD.json")
    main(sys.argv[1])
