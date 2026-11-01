# Mālgefēran

Turns a photo of the printed Picture House rota into my shifts, my hours and purple events in Google Calendar, without typing anything in.

## What it does

Every week a paper rota goes up at work. It covers every department (DM, Admin, Usher, Box, EEAAO, Bar, Base) for a Friday-to-Thursday week, with each shift's time printed above the person's name. Copying my shifts into a calendar by hand is slow and easy to get wrong.

Mālgefēran does it for me:

1. **I take a photo** of the rota and upload it to the Google Drive folder **"Photos of rotas for claude"**.
2. **Claude finds the photo.** Either the scheduled check spots it (08:37 and 17:37 every day) and processes it on its own, or I say *"do my rota"* and it shows me the table before writing anything.
3. **Claude reads the whole sheet**, not just my row: every cell's day, section, printed time and name.
4. **The code finds me and does the maths.** `rota.py` matches my name (it allows for typos like "Wiliam"), works out each shift's length and the week's total, and handles shifts that run past midnight.
5. **It builds the outputs:**
   - a table of my shifts and the week's hours
   - a purple Google Calendar event for each shift, showing the duty manager and who's opening and closing the bar
   - an `.ics` file that works in any other calendar (Apple, Outlook)
6. **It saves the week** to this repo, so there's a running record of every rota.
7. **It goes dormant.** Nothing runs between photos.

## What a calendar event looks like

Title: **Picture House shift – Bar**, in Google's Grape (purple), with the usual 30-minute reminder.

```
You: 12:00–20:30 (8h 30m) · week total 44h 30m

DM: Jack 08:30–16:30 → George 16:00–22:30

OPENING bar (start 08:00–10:30)
• Richard 08:30–16:30 (DC)
• Giovine 10:30–15:00
• Louis 10:30–18:15

CLOSING bar (start 14:00 or later)
• Grace 15:00–22:00
• Beth 16:30–22:00

Added by rota-calendar.
```

Anyone on bar who starts between 10:31 and 13:59 goes under **MID**.

## How it's built

It runs inside Claude, on my existing subscription. There's no server, bot or API key to pay for.

| Part | Job |
|---|---|
| Google Drive folder | Where rota photos go in |
| Claude (vision) | Reads the photo into structured data |
| `rota.py` | Hours, totals, overnight shifts, bar team, DM, `.ics` and event data |
| `config.json` | Name on the rota, colour, opener and closer cut-offs, break rules |
| Google Calendar connector | Writes the events |
| This repo (private) | Code, settings and every processed week |

The AI only reads the photo. Every sum is done in code, so the hours are always exact if the times are right.

### Files

- `rota.py`: turns one week's JSON into a table (`.md`), a calendar file (`.ics`) and event data (`.events.json`)
- `config.json`: settings
- `weeks/YYYY-MM-DD.json`: one rota week, named by its Friday
- `processed.json`: which Drive photos have been handled, so nothing is done twice
- `history/`: my shifts from older rotas, plus one full-sheet transcription
- `RUNBOOK.md`: the exact steps Claude follows on each run
- `CHANGELOG.md`: every change to how the system works, one entry per request

### Run it by hand

```
python3 rota.py weeks/2026-10-30.json
```

## Things the rota throws at it

Found by testing on 18 real rotas:

- **Dates are unreliable.** Some sheets print no dates, some no month, and one printed Thursday as "THU 29" when it was 5 Nov. The run works dates out from the Friday, and asks if it can't.
- **My name varies:** "William", "Wiliam", "Will".
- **Codes** after times or names. Known codes are written out in full on events and in the table, and unknown ones are kept as printed:

  | Code | Meaning |
  |---|---|
  | SR | Stock rotate |
  | DC | Deep clean |
  | BL | Beer lines (cleaning them) |
  | `+` | Carries on in another area afterwards, for example Bar 10:30–18:00+ then Box 18:00–23:00. If it's my shift, the second part becomes its own event and I get a day total. |
  | ST | **Not known yet.** Neither of us knows; I'm finding out. Shown as "meaning not known yet". |
  | `&` | Not confirmed yet |

- **Staff meetings** printed on the rota become their own **red** events (Google's Tomato) at the time shown, whether or not I'm working that day. If the rota says "attend one", each session is added and marked "(attend one)".
- **Camera RAW (DNG) files** can be read through their built-in preview, but JPG or HEIC is better.

## Settings (`config.json`)

| Setting | Value |
|---|---|
| Name on rota | William |
| Event colour | Google colour 3 (Grape) |
| Openers | Start 08:00–10:30 |
| Closers | Start 14:00 or later |
| Hours | Clock-on to clock-off (breaks don't matter) |
| Codes | SR, DC, BL and + written out in full; ST and & not known yet |
| Staff meetings | Own event, Google colour 11 (Tomato, red) |

## Status

Working end to end since 1 Nov 2026. The week of 30 Oct is in my calendar.

Still open:
- What ST means. Neither of us knows yet; I'll find out and update it.
- What "&" means

## The name

**Mālgefēran** (say *MAHL-yeh-fay-ran*) is a modern compound of two Old English words. It isn't recorded as a single word in Old English.

- **māl** (usually spelt *mǣl*), a neuter noun: a measure, a mark, a **fixed or appointed time**, a season, an occasion, a mealtime. It's the root of modern *meal* and of German *-mal* in *einmal*.
- **ġefēran**, a weak verb (past tense *ġefērde*): **to go, travel, get to a place, reach, attain**. It comes from *fēran*, "to go", and *ġe-* often marks reaching the end of an action, so *ġefēran* is going *and arriving*.

Put together, it means roughly **"reaching the appointed times"**, which is what the tool does with a week of shifts.

*Beowulf* uses both roots in one line, when the coastguard leaves the Geats at Heorot (line 316): ***Mǣl is mē tō fēran***, "it is time for me to go."

A related noun, *ġefēra*, means "companion" or "comrade", so the name also carries a faint sense of the people you work alongside. That's the bar team on every event.

## Searu

This project is published on [Searu](https://searu.vercel.app). Every change to how it works gets its own post.

## Author

Will ([@citricpigeon](https://github.com/citricpigeon))
