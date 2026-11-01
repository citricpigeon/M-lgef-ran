# Changelog

Every request made while building Mālgefēran is logged here as an **update**, with a type, what was asked, and what changed in how the system works.

Updates that changed how the system works get a post on Searu (code `mg`). Questions that changed nothing are logged here only.

**Types**
- **Design:** decides how the system should work
- **Research:** answers a question; no change to the system
- **Build:** code or infrastructure
- **Feature:** a new thing the system can do
- **Data:** reads or reports on rotas without changing the system
- **Docs:** documentation and publishing

---

## U01 · Design · 1 Nov 2026, 13:22
**Asked:** Upload a photo of the paper rota, have AI pull out one person's shifts, hours per shift and weekly total, put them in a table and import them into Google or any calendar. Run when a photo arrives, then go dormant.
**Changed:** First design. Telegram bot as the upload button, Google Apps Script to host, Claude API to read the image, code to do the maths, Google Calendar plus `.ics` as output. Rules set from the start: confirm before writing, no duplicates, shifts past midnight end the next day, ask for the week's date if it's missing.
**Searu:** mg-01

## U02 · Research · 13:25
**Asked:** Apart from the Claude subscription, is everything else free?
**Changed:** Nothing. Found that Telegram, Apps Script and Google Calendar are free, but the Claude API is billed separately from the subscription (about 1p a photo).
**Searu:** none (folded into mg-02)

## U03 · Design · 13:33
**Asked:** Build it so I upload the image to Claude, it runs the program, saves to a new repo and exports to calendars.
**Changed:** Moved from a hosted bot to running inside Claude on the subscription: a Claude Project as the front door, a script in a GitHub repo, and calendar connectors. No API key, bot or server.
**Searu:** mg-02

## U04 · Build · 13:44
**Asked:** Here's the repo: `citricpigeon/M-lgef-ran`.
**Changed:** Repo attached. `rota.py` v1 turns a week's shifts into a table, hours per shift, a weekly total and an `.ics` file. It handles overnight shifts, has optional unpaid-break rules, and gives each event a stable ID so re-imports update instead of duplicating. `config.json` added. Push was blocked until the Claude GitHub App was installed. Commit `6d1b264`.
**Searu:** mg-03

## U05 · Build · 13:48
**Asked:** Do you have access now?
**Changed:** First push to `main` succeeded. No change to how it works.
**Searu:** none (folded into mg-03)

## U06 · Feature · 13:51
**Asked:** Can you see my Drive folder "Photos of rotas for claude"?
**Changed:** Google Drive became the input. Read 5 rotas and learned the layout: Friday-to-Thursday weeks, department sections, time printed above the name. Found the name on the rota is "William", that dates are often missing, that names have typos, and that the rota uses codes (SR, DC, BL, +, &). Three dated weeks ran through `rota.py`.
**Searu:** mg-04

## U07 · Feature · 14:04
**Asked:** Show me how you'd analyse the 28 Aug – 3 Sep rota, and the data.
**Changed:** Set the reading method: transcribe the whole sheet (89 cells, 84 shifts, 19 names), then match the name in code with fuzzy matching ("Wiliam" matches, "Will" alone doesn't) and list every odd cell. Reading the full sheet catches errors and is what makes the bar-team feature possible later.
**Searu:** mg-05

## U08 · Data · 14:06
**Asked:** Show me all the data for William.
**Changed:** Nothing. Reported 23 shifts across 5 rotas (182h 30m, 36h 30m a week on average, 12:00 the most common start) and saved them to `history/william_all_shifts.csv`.
**Searu:** none

## U09 · Feature · 14:08
**Asked:** Look at the whole Drive folder and find the newest.
**Changed:** It can now pick out new photos by upload time, read camera RAW (DNG) files through their built-in preview, and work out a missing month from the staff on the sheet and the week before. The newest upload was 4–10 Sep: 41h.
**Searu:** mg-06

## U10 · Feature · 14:14
**Asked:** I uploaded this week's rota. What day is it, and when is my next shift?
**Changed:** It can now answer "what's today, and what's next" from the current rota. It coped with a sheet whose Wednesday and Thursday headers said "OPEN AT 9.30" and whose footer printed Thursday as "THU 29". The week of 30 Oct: 44h 30m, with the next shift Mon 2 Nov 12:00–20:30.
**Searu:** mg-07

## U11 · Feature · 14:15
**Asked:** Can you put that into my Google Calendar now?
**Changed:** First live write to Google Calendar: Mon, Tue and Wed shifts. It checked for existing events and clashes first. When the first attempt only created one event, it re-checked before adding the rest, so nothing was duplicated.
**Searu:** mg-08

## U12 · Feature · 14:19
**Asked:** Make them purple, show who I'm working with on the bar, and split openers (start 8–10:30am) from closers (start 2pm or later).
**Changed:** Events set to Google colour 3 (Grape). The description now lists the bar team under OPENING, MID and CLOSING. This is built into `rota.py` with the cut-offs in `config.json`, and it also writes `.events.json`. Commit `675d9ea`.
**Searu:** mg-09

## U13 · Feature · 17:49
**Asked:** The repo is private. Grape is right, 10:30 is right, and add the duty manager.
**Changed:** A DM line was added to every event (for example "Jack 08:30–16:30 → George 16:00–22:30"). Settings confirmed. Processed weeks and history pushed, now that the repo is confirmed private. Commit `7afff70`.
**Searu:** mg-10

## U14 · Docs · 17:52
**Asked:** Create a project folder in `C:\Projects`, write a README covering the whole flow from a Drive upload to the calendar, log every prompt as an update, and post each change to Searu.
**Changed:** Added `README.md`, `CHANGELOG.md`, `RUNBOOK.md`, `CLAUDE.md` and `processed.json`. Created `C:\Projects\Mālgefēran`. Two ways to start a run: a scheduled check of the Drive folder at 08:37 and 17:37 UK time (it only writes to the calendar when every shift was read clearly), and a "do my rota" skill that confirms before writing. Searu project page `malgeferan`, draft posts mg-01 to mg-11 plus the mg-99 overview, and two new skill names: Automation and Document extraction. Commit `60ec920`.
**Searu:** mg-11
