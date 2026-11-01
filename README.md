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
- **Codes** after times or names: SR, DC, BL, ST, "+", "&". These are kept as notes until their meanings are confirmed.
- **Camera RAW (DNG) files** can be read through their built-in preview, but JPG or HEIC is better.

## Settings (`config.json`)

| Setting | Value |
|---|---|
| Name on rota | William |
| Event colour | Google colour 3 (Grape) |
| Openers | Start 08:00–10:30 |
| Closers | Start 14:00 or later |
| Unpaid breaks | None yet (clock-on to clock-off), still to confirm |

## Status

Working end to end since 1 Nov 2026. The week of 30 Oct is in my calendar.

Still open:
- Unpaid breaks: deduct, or count clock-on to clock-off?
- What SR, DC, BL and "+" mean
- Whether staff meetings go in the calendar as separate events

## Searu

This project is published on [Searu](https://searu.vercel.app). Every change to how it works gets its own post.

## Author

Will ([@citricpigeon](https://github.com/citricpigeon))
