# Savage Sales Agent

A sales coach and assistant built on the Beautiful Savage Sales Academy method, extended with clearly labeled general best practice.

This is a **CLI-only tool**: no GUI, web app or server. It runs in your terminal through Claude Code.

## Start
1. Run `savage.cmd` in this folder (or open a terminal here and run `claude`).
   To run it from anywhere, add this folder to your PATH once, then just type `savage`.
   One-shot use also works: `savage -p "/objection \"we already have a tool\""` prints the answer and exits.
2. Run `/setup`. Not selling anything yet? Choose practice mode (fictional company) to try everything.
3. Try: `/cold-script`, `/call-prep`, `/objection "we already have a tool for that"`, `/roleplay cold call to an owner`.

## Commands
| Stage | Commands |
|---|---|
| Foundation | `/setup` `/icp` `/persona` |
| Prospecting | `/cold-script` `/outreach` `/objection` `/roleplay` |
| Discovery | `/call-prep` `/discovery-plan` `/grade-call` `/recap-email` |
| Deals | `/inspect-deal` `/deal-log` `/map` `/business-case` `/negotiate` `/battlecard` |
| Planning | `/forecast` `/territory-plan` `/week-plan` |
| Personal foundation | `/foundations` (purpose, clarity, gratitude, cost of inaction) |
| Lost? | `/help` lists everything and suggests what to run next |

## Layout
- `profile.md` your business (blank until `/setup`); `profile.template.md` blank copy; `examples/profile.example.md` fictional practice profile
- `playbook/01-07` and `10` the course; `playbook/08-09` supplements (NOT the course)
- `deals/` one file per deal (agent memory); `outputs/` everything it generates
- `knowledge_raw/` text extracted from your course files; `SOURCES.md` what came from where

## Known limits
- Headless-tested 19 of 21 commands against the practice profile (rules held: no invented proof, honest scoring). `/week-plan` also tested OK; `/foundations` is interactive and untested. Expect to refine wording after real use.
- Course recordings aren't included; the "hero" step of the business case is inferred (see SOURCES.md).
- Supplement benchmarks (email length, reply rates, coverage ratios) are vendor-sourced and directional.
- It drafts; you send. It never contacts anyone.

## Privacy
`outputs/` and `deals/` (your real prospects) are git-ignored, as is `knowledge_raw/` (local extracts of the paid course files, not published). Unofficial: not affiliated with or endorsed by Justin Jay Johnson or the Beautiful Savage Sales Academy; the playbooks are the author's own notes, plus labeled general best practice.
