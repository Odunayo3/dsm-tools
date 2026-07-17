# Contributing to dsm-tools

Thank you for helping improve the DSM skills. The toolkit's value depends on the
judgment it encodes being correct and current, so contributions are held to a
methodological standard, not just a code one.

## Principles

1. **Cite the method.** Any change to a skill's decision logic, default, or
   caveat must reference a published source (add it to `docs/references.md`).
   PRs that change judgment without a citation will be asked for one.
2. **No auto-ingested findings.** `dsm-lit-watch` proposes updates; a human
   maintainer vets and merges them, recording the change in `docs/changelog.md`.
3. **Tested code only.** New or changed code templates must run. The CI runs the
   Python templates (and the tested R subset) on every push; they must exit 0.
   Add your template to `.github/workflows/ci.yml`.
4. **Honesty labels stay.** Code that could not be live-tested (e.g. external-API
   connectors) must keep its "verify on first live run" note. Do not remove it.
5. **Leakage discipline.** Any modeling code must keep preprocessing, feature
   selection, and tuning inside the training fold. PRs that leak will be rejected.

## How to contribute

- Open an issue describing the change and its literature basis.
- Fork, branch, and submit a PR. Keep skills' `SKILL.md` in the house style:
  direct academic voice, no em-dashes, trigger conditions + judgment + failure
  modes + output conventions.
- For a new skill, follow the structure of `dsm-model-fit` (the reference).

## Governance

The maintainer(s) vet literature-based changes. Regional best-practice updates
proposed by `dsm-lit-watch` require maintainer sign-off before merge.
