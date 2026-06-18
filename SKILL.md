---
name: marketing-harness
description: >-
  Use this repository as a self-contained marketing image-generation harness
  skill for Claude Code or other agents. Trigger when the user wants to create
  brand-locked marketing assets, define or promote brand.lock design tokens,
  validate campaign YAML, run regression, render via OpenAI/gpt-image/gateway
  providers, publish versioned artifacts, or bootstrap a local harness workspace.
---

# Marketing Harness

This entire repository is the skill payload. It includes the Python harness,
workspace examples, provider adapters, tests, published snapshots, and the
agent-facing workflows.

Preserve the boundary:

```text
brand memory -> brand.lock.yaml -> campaign.yaml -> render -> human asset review -> publish
```

Never put visual style prompt text in campaign files. Campaigns describe content
and deliverables only.

## Resolve Harness Root

Use this order:

1. If the current working directory contains `pyproject.toml` and `src/harness/`,
   operate there.
2. Else if `$CLAUDE_SKILL_DIR` points at this installed repo skill, use that as
   the source root.
3. If the user wants editable outputs in the current project, materialize a
   working copy:

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/bootstrap_harness.py" ./marketing-harness
cd ./marketing-harness
```

Run the initial check from the selected root:

```bash
python3 scripts/check_harness.py .
```

Use `harness_entrypoint` from the check output as the command prefix. Normally
it is `uv run harness`; when `uv` is unavailable but `.venv/bin/harness` exists,
use that fallback. If neither exists, install `uv` or run `uv sync`.

## Common Defaults

- Brand lock: `workspace/products/codefox/codefox/brand.lock.yaml`
- Example campaign: `workspace/products/codefox/codefox/campaigns/example.campaign.yaml`
- Dry-run first for new flows
- Local review publish channel: `repo`
- Do not commit automatically

For exact command sequences, read `references/workflows.md`. For schema
contracts, read `references/contracts.md`.

## Style Production

When a design skill, Claude, Codex, or a human produces style, freeze the result
as a `brand.lock.yaml` proposal before render.

Selection order for design producers:

1. If the user names a local design skill, prefer it.
2. Otherwise prefer an already-installed local brand/frontend/visual design skill.
3. If none exists, stop and ask the user to install/specify one or provide a
   reviewed brief and references.

Do not download, clone, or install a remote design skill as an implicit fallback.

Proposal flow:

```bash
uv run harness style propose \
  --base workspace/products/codefox/codefox/brand.lock.yaml \
  --brief workspace/products/codefox/codefox/brief.md \
  --source workspace/products/codefox/codefox/references/ \
  --out workspace/products/codefox/codefox/proposals/<name>.lock.yaml

uv run harness validate workspace/products/codefox/codefox/campaigns/example.campaign.yaml \
  --brand workspace/products/codefox/codefox/proposals/<name>.lock.yaml

uv run harness regression \
  --brand workspace/products/codefox/codefox/proposals/<name>.lock.yaml \
  --dry-run
```

Only after review:

```bash
uv run harness style promote \
  workspace/products/codefox/codefox/proposals/<name>.lock.yaml \
  --to workspace/products/codefox/codefox/brand.lock.yaml
```

For external producer contracts, read `references/design-producer-protocol.md`.

## Rendering And Publishing

Before live render, confirm API usage and possible cost. `OPENAI_API_KEY`
belongs in `.env`; never print, commit, or copy it into configuration files. If
`provider.gateway` is `skill-cli` or `gpt-image-skill`, ensure the local
`gpt-image` skill/CLI is installed or `HARNESS_SKILL_CLI_COMMAND` points to an
equivalent command.

Live generation:

```bash
uv run harness validate <campaign.yaml> --brand <brand.lock.yaml>
uv run harness render <campaign.yaml> --brand <brand.lock.yaml>
```

After live render, inspect generated files, dimensions, text quality,
`manifest.json`, and `run.lock.json`. Show output paths and ask for explicit
human asset acceptance before any command with `--publish`, unless the user
explicitly pre-approved auto-publish.

After acceptance:

```bash
uv run harness publish <campaign-name> --channel repo --publish
```

Safe smoke test:

```bash
uv run harness render <campaign.yaml> --brand <brand.lock.yaml> --dry-run
uv run harness publish <campaign-name> --channel repo
```

## Verification

After code or workflow changes:

```bash
uv run ruff check .
uv run pytest
uv run harness validate workspace/products/codefox/codefox/campaigns/example.campaign.yaml
uv run harness render workspace/products/codefox/codefox/campaigns/example.campaign.yaml --dry-run
```

Check that no API key, authorization header, machine-specific path, or raw image
base64 payload is stored in tracked files.
