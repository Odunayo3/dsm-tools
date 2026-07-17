---
name: dsm-lit-watch
description: >
  On request, scan recent DSM literature (Geoderma, EJSS, SOIL, Remote Sensing
  of Environment, arXiv) and flag candidate updates to the other skills - new
  methods, benchmarks, deprecated practices, shifting regional best practice.
  Also invoked by dsm-site-assessment when a location's best practice is unclear.
  Trigger for "check recent DSM literature", "any new methods for X", "update the
  skills from the literature", or /lit-watch. A human vets and merges; never
  auto-edits skills.
version: 0.2.0
---

# dsm-lit-watch

Keep the toolkit current without letting bad methodology creep in.

## 1. When to trigger
Explicit request to check literature or propose skill updates; or a handoff from
dsm-site-assessment when regional best practice is uncertain.

## 2. Core behavior
- Search recent, reputable sources; prioritize the last 12-18 months and
  method-focused venues. Favor peer-reviewed and preprints from known groups
  over aggregators.
- For each candidate finding, name: which skill it touches, what it would change
  (a rule, a default, a caveat), and the citation.
- Output a proposed-changes list. Do NOT edit other SKILL.md files. A human vets
  and merges - auto-ingesting findings is how bad methodology enters the toolkit.
- Do not claim the toolkit is "always current". Promise curation and a changelog.

## 3. Output conventions
A dated review note: finding, affected skill, proposed change, citation,
confidence. Append to docs/changelog.md on merge (human step).

## 4. Reference implementation
Procedure skill using web search / the user's reference manager. No code
template.
