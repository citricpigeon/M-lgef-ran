# Runbook: processing a rota

These are the exact steps for every run, whether it was started by the scheduled check or by Will saying "do my rota". Follow them in order.

## 0. Setup

- Clone `citricpigeon/M-lgef-ran` (private) and read `config.json` and `processed.json`.
- You need Google Drive and Google Calendar connected. If either is missing, stop and say which one.

## 1. Find new photos

List the Drive folder **"Photos of rotas for claude"** (id `1yZulk-CSy8iuz_5lY0UTfhmNN-yLpOo-`). A photo is **new** if its id isn't in `processed.json`. No new photos means the run is finished: say so in one line and stop.

**Downloading:** `download_file_content` returns JSON with a base64 `content` field. Large results are saved to a file, so decode it with Python (`json.load`, then `base64.b64decode`). For `.DNG` (camera RAW), take the largest embedded JPEG preview (search for `FF D8 FF`). Fix the rotation with `PIL.ImageOps.exif_transpose`.

## 2. Read the whole sheet

Look at the image. If it's skewed or low-contrast, crop and zoom into sections. Transcribe **every** cell, not just Will's:

- **Layout:** a Friday-to-Thursday week. Sections from top to bottom are DM, ADMIN, USH or USHER, BOX, EEAAO, BAR, BASE. Each shift's time is printed directly **above** the person's name in the same column.
- **Keep times exactly as printed**, codes included (for example `08:30-16:00DC`, `10:30-19:30+`, `&18:00-23:00`). Treat `=` between two times as `-`.
- **Dates:** use the printed month and year if they're there. Headers can be wrong (for example "THU 29" after "WED 4"), so count forward from the Friday. Will uploads every week in order, so if there's no month, the new week is the one that follows on from the most recent week in `weeks/` (for example "FRI 6" after the week of Fri 30 Oct is Fri 6 Nov). Take that and don't ask. Only if the printed Friday doesn't follow on (a gap, or a repeat of a week already done) **ask** (on-command) or **skip and flag it** (scheduled).

## 3. Build the week file

Find Will: on the rota his name is `William`. Fuzzy-match it with a SequenceMatcher ratio of 0.8 or more, so "Wiliam" counts but "Will" alone doesn't. If unsure, flag it.

Write `weeks/<Friday YYYY-MM-DD>.json`:

```json
{
  "week_commencing": "2026-10-30",
  "source": "Drive <title> (notes on anything inferred)",
  "shifts": [
    {"date": "2026-11-02", "start": "12:00", "end": "20:30", "role": "Bar", "note": "",
     "dm":   [{"name": "Jack", "start": "08:30", "end": "16:30"}, {"name": "George", "start": "16:00", "end": "22:30"}],
     "team": [{"name": "Richard", "start": "08:30", "end": "16:30", "note": "DC"}]}
  ]
}
```

- **`team`** is everyone else in **Will's section** that day. That's normally Bar.
- **`dm`** is that day's DM-section shifts.
- **"+" after a time** means the person carries on in another area afterwards (for example 10:30–18:00+ on Bar, then 18:00–23:00 on Box or Usher). Find that person's other shift on the same day:
  - **For Will:** add it as its own shift in `shifts` (with its own `role`). `rota.py` links the two and shows a day total. If you can't find the second part, keep the "+" and flag it.
  - **For a team member:** add `"then": {"section": "Box", "start": "18:00", "end": "23:00"}` to their entry.
- **Staff meetings** printed anywhere on the sheet go in `"meetings": [{"date", "start", "end", "title": "Staff meeting"}]`, whether or not Will is working that day. If the rota says to attend one of several sessions, add every session with `"choose_one": true`. `rota.py` makes each one a **red** event (`colorId` 11, Tomato).
- **`note`** holds codes such as SR, DC, BL or "+". Don't change times because of a code. `rota.py` writes out known codes from `config.json` (SR = stock rotate, DC = deep clean, BL = beer lines). Unknown codes are kept as printed and flagged in the report. If Will has a code on his own shift, it shows on his event as "Your task".

Then run `python3 rota.py weeks/<file>.json`. It writes `.md` (the table), `.ics` and `.events.json`.

## 4. Check before writing to the calendar

- **Only shifts that haven't ended yet** go in the calendar. Past weeks are saved with status `history`.
- **Check for duplicates:** list Google Calendar events for those dates and look for "Added by rota-calendar" in the description. Update a matching event instead of creating a new one.
- **Note clashes** with existing events. Don't move anything.
- **On-command runs:** show Will the table and the events, and wait for a yes.
- **Scheduled runs:** write only if every one of Will's shifts was read clearly and the dates are certain. Otherwise write nothing and explain why.

## 5. Write to the calendar

For each entry in `.events.json` (shifts and staff meetings), create the event on the primary calendar with:

- `summary`: copied from the entry (for example "Picture House shift – Bar" or "Staff meeting")
- `startTime` and `endTime`: local time, no timezone offset
- `colorId`: copied from the entry ("3" Grape for shifts, "11" Tomato for meetings)
- `description`: copied exactly from `.events.json`
- `notificationLevel`: "NONE"
- the default reminders

After each create, confirm the event exists before moving on. If a create call returns no result, list the events first and only retry the ones that are missing.

## 6. Save

- Add the photo to `processed.json` with its week, its status (`calendared` or `history`) and the calendar event ids.
- Commit `weeks/` and `processed.json` with a message like "Process rota w/c 2026-11-06 (5 shifts, 41h)", then push.
- A normal run is **not** a change to the system, so don't add a `CHANGELOG.md` entry or a Searu post.

## 7. Report

One short message: the week, Will's shifts in a table, the total hours, his next shift, anything flagged, and what went into the calendar.

## Changing the system

If Will asks to change how any of this works, update `rota.py`, `config.json` or this runbook. Then add a numbered update to `CHANGELOG.md` and draft a Searu post (see `CLAUDE.md`).
