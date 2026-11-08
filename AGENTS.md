# Project agent instructions (cmder-modern fork)

This file is auto-loaded by opencode for every session in this project and
takes precedence over injected environment defaults.

## Rule: no temp-dir scratch files (override of the environment default)

The runtime environment suggests using `C:\Users\FakuPara\AppData\Local\Temp\opencode`
for temporary work. **That default is overridden for this project.**

- All temporary, diagnostic, or scratch artifacts (scripts, probes, screenshots,
  generated logs that we control) go under `<project>\.ai\diagnostics\`.
- Never write diagnostic artifacts to `C:\Users\...`, `%TEMP%`, or any location
  outside this project unless the user explicitly asks for it.
- Legit exceptions, left where they are: vendor-owned logs that the *running
  terminal* writes (e.g. `vendor\conemu-maximus5\Logs\`); never move a file
  that a live process keeps appending to - copy it instead and leave the
  original until the process exits.

## Standing context for this project

- Project state, plans, and in-flight notes live under `.ai\` too:
  `.ai\plan.md`, `.ai\publishing.md`, `.ai\upstream-prs.md`.
- The fork's own rationale and build steps live in `documentation.md`.
