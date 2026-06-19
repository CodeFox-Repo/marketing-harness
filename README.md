# Marketing Harness Skill

[简体中文](README.zh-CN.md)

Marketing Harness is an installable agent skill for producing theme-locked
marketing assets from a product repository. It validates repo visual tokens,
prepares campaigns, renders through local producer capabilities, and records
only user-accepted assets into repo-owned visual asset state.

This repo ships one installable skill payload plus maintainer tooling:

- `skills/marketing-harness/`: the installable skill payload.
- `scripts/package_skill.py`: packages only the skill payload.

The runtime used by agents is bundled under `skills/marketing-harness/scripts/`.
There is no top-level `src/` package in the skill shape.

## What The Skill Does

Marketing Harness keeps style, campaign content, production, and accepted state
separate:

```text
repo visual state -> production plan -> candidates -> user acceptance -> accepted state -> next production
```

The skill helps an agent:

- read a YAML/JSON metadata file that declares repo paths and policy.
- read organization, repo, related-repo, and directory asset state before planning.
- validate `theme.md` frontmatter and campaign files.
- run dry-run renders without spending API credits.
- call local producer capabilities for live assets.
- require human asset review before state updates.
- copy accepted files into approved assets and update `accepted.yaml`.

Downstream apps consume accepted files and manifests. They do not run
generation, and scratch candidates are not visual memory.

## Use

Open a product repo, then mention the skill in the task:

```text
$marketing-harness bootstrap this repo for a new product visual system
$marketing-harness validate the CodeFox example campaign
$marketing-harness create a campaign for a launch poster, dry-run first
$marketing-harness render this campaign with the current theme, then wait for review
$marketing-harness record the accepted launch banner into visual asset state
```

The installed skill contains a launcher:

```bash
python3 "$SKILL_ROOT/scripts/harness.py" ...
```

The launcher keeps paths rooted in the current product repo and runs the bundled
scripts in the installed skill. It does not call `uvx` or discover a parent
runtime checkout.

## Repo Shape

The product repo owns its asset hierarchy. Paths should come from metadata, not
a hard-coded root layout. One common shape is:

```text
assets/marketing/
  theme.md
  campaigns/
  references/
  proposals/
  plans/
  asset-state.yaml
  accepted.yaml
public/marketing/
  <channel-or-format>/
    asset-state.yaml
  <approved assets and manifests>
.harness/marketing/out/
```

- `project.marketingRoot` is editable source input: theme notes, campaign YAML,
  proposals, references, and accepted-work notes.
- `artifacts.scratch` is the local render buffer.
- `artifacts.approved` is the reviewed asset path, asset repo, or submodule target.
- `state.assetIndex` is the repo-level visual asset memory.
- `state.accepted` is the durable accepted corpus used by future planning.
- `state.directoryStateFile` is the per-directory memory filename, usually
  `asset-state.yaml`.
- `sources.relatedRepos` points at same-org repos whose accepted state should
  inform this repo's production.

Before producing banners, landscape visuals, slide/PPT backgrounds, logo-theme
variants, X/XHS cards, or social images, run the read-only state preflight and
use that output in the production plan:

```bash
python3 "$SKILL_ROOT/scripts/harness.py" --metadata path/to/marketing.harness.yaml state
```

## Theme Contract

`theme.md` is the single source of truth for a repo's visual direction. YAML
frontmatter stores machine-readable style tokens and provider config; the
Markdown body explains the design direction for humans and agents.

Campaign files can only choose a locked style alias and provide current content:
headline, subject, and deliverable sizes. They must not inline prompts,
palettes, negative prompts, reference images, model names, or provider params.

## Producer Capabilities

Third-party producer skills are managed as local capabilities declared in
metadata, not dependencies bundled by Marketing Harness. `producers.image`,
`producers.slide`, `producers.logo`, and `producers.social` can name preferred
local skills or commands. The agent must not auto-install or silently switch
producers.

## Human Review

Live render approval and asset approval are different. The skill should dry-run
first, ask before spending API credits, render live only after approval, then
show generated files for review. Accepted state should change only after the
user or reviewer explicitly accepts exact files or asset ids.

## Verification

```bash
uv run ruff check .
uv run pytest
cd skills/marketing-harness/examples/codefox
python3 ../../scripts/harness.py --metadata marketing.harness.yaml validate
```

Only the installable skill payload is packaged by default; examples, tests,
root maintainer files, and scratch outputs are excluded.
