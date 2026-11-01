# Mālgefēran

Turns photos of the Picture House paper rota into Will's shifts, hours and purple Google Calendar events. See `README.md` for what it is and `RUNBOOK.md` for the steps of every run.

## Rules

- The AI reads the photo. `rota.py` does every sum. Never work out hours by hand.
- Read the whole sheet, then find Will in code (his name on the rota is "William").
- Never write to Google Calendar without checking for existing "Added by rota-calendar" events first.
- The repo is private. Rota data (colleagues' names and times) stays in this repo and nowhere public.

## Every change gets logged

When a request changes **how the system works** (code, settings, outputs, the runbook):

1. Add the next numbered update to `CHANGELOG.md` (U15, U16...), with its type (Design, Research, Build, Feature, Data, Docs), what was asked, and what changed.
2. Keep commits to one change each, with a message that says what was built and why.

Questions and routine rota runs go in the changelog only if they changed something. Routine runs never do.

## Searu

This project is published on Searu (citricpigeon/Searu, `C:\Projects\Searu Portfolio`). Its project id is `malgeferan` and its post code is `mg`.

Every change to how the system works gets a post there: `src/content/blog/YYYY-MM-DD-mg-NN-<slug>.md`, built from `docs/post-template.md`. Use skill names from `docs/skills.md`, set `project: malgeferan`, and start with `draft: true`. Will reviews each post before it's published.
