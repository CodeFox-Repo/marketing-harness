# Harness Contracts

## Brand Lock

`brand.lock.yaml` is the style single source of truth. It must be versioned and validated before render.

Required top-level fields:

```yaml
portfolio:
  id: "codefox"
  name: "CodeFox"
  version: "1.0.0"
brand:
  id: "codefox"
  name: "CodeFox"
version: "1.1.0"
provider:
  gateway: "gpt-image-skill"
  # Optional: model: "<image-cli-model-name>"
  params: {}
global: {}
alias: {}
```

Token rules:

- Every token is a mapping with `$value` and `$type`.
- `global` contains raw visual decisions with no usage intent.
- `alias.style.*` contains semantic style composites.
- Alias references may only use `{global.path.to-token}`.
- Use kebab-case token and group names.
- Changing provider params or visual tokens requires a version bump and dry-run review.
- `provider.model` is optional. The marketing harness only passes it through when present.

`portfolio` is optional for legacy locks but required for new product brands. Treat
`portfolio.version` and `brand.lock version` separately:

- `portfolio.version` changes when the parent brand metadata or element system changes.
- `brand.lock version` changes when this product's locked visual tokens or provider config changes.
- Generating a campaign does not bump either version.

## Metadata, Elements, And Accepted Corpus

Product repos may keep optional sidecars next to the metadata-declared
`brand.lock.yaml` and portfolio directory. A common package-local shape is:

```text
packages/branding/marketing/portfolios/<portfolio-id>/portfolio.meta.yaml
packages/branding/marketing/portfolios/<portfolio-id>/elements.yaml
packages/branding/marketing/portfolios/<portfolio-id>/accepted.yaml
packages/branding/marketing/brand.meta.yaml
packages/branding/marketing/elements.yaml
packages/branding/marketing/accepted.yaml
packages/branding/marketing/plans/
```

These files are loaded, validated, and snapshotted for traceability. They do not
implicitly change render prompts. A human or style producer must distill them
into a reviewed `brand.lock` proposal before they affect generation.

## Campaign

Campaigns describe content only:

```yaml
name: "feature-x-launch"
brief: "What this campaign says"
style: "launch-hero"
content:
  headline: "Visible copy"
  subject: "Scene or subject"
deliverables:
  - id: "web-banner"
    size: [1920, 600]
```

Campaigns must not include style prompt fragments, palette, negative prompts, references, or provider params.

## Production Plan

Plans are source state written before rendering:

```yaml
schema_version: "1.0"
id: "feature-x-launch"
created_at: "2026-06-19T00:00:00Z"
objective: "Generate launch assets for feature X."
inputs:
  brand_lock: "packages/branding/marketing/brand.lock.yaml"
  campaign: "packages/branding/marketing/campaigns/feature-x-launch.campaign.yaml"
  accepted_corpus: "packages/branding/marketing/accepted.yaml"
  references:
    - "packages/branding/marketing/references/main_visual.png"
sources:
  portfolio:
    id: "codefox"
    version: "1.0.0"
  related_products: []
deliverables:
  - id: "web-banner"
    size: [1920, 600]
acceptance_criteria:
  - "Matches locked brand style."
  - "Visible text is legible."
  - "Can influence future launch assets if accepted."
status: "planned"
```

Plans may reference remote registry or related-product sources, but generated
runs should pin the resolved commit in the plan or review notes.

## Run Lock

`<metadata artifacts.scratch>/<campaign>/run.lock.json` stores reproducibility metadata:

- full brand lock snapshot
- portfolio/product metadata sidecar snapshots, when present
- full campaign snapshot
- resolved style
- prompt per asset
- seed and provider params
- sanitized provider metadata

It must never contain API keys, authorization headers, or raw image base64 payloads.

## Manifest

`<metadata artifacts.scratch>/<campaign>/manifest.json` is the consumer contract:

```json
{
  "schema_version": "1.0",
  "campaign": "feature-x-launch",
  "portfolio": {
    "id": "codefox",
    "name": "CodeFox",
    "version": "1.0.0"
  },
  "brand": {
    "id": "codefox",
    "name": "CodeFox",
    "version": "1.1.0"
  },
  "brand_lock_version": "1.1.0",
  "provider": {
    "gateway": "gpt-image-skill",
    "model": null
  },
  "assets": [
    {
      "id": "web-banner",
      "file": "web-banner.png",
      "path": "web-banner.png",
      "url": null,
      "size": [1920, 600],
      "mime_type": "image/png",
      "checksum_sha256": "...",
      "seed": 12345
    }
  ]
}
```

## Accepted State

Accepted state is the durable memory used by future planning. It is updated
only after the user accepts exact candidate files:

```yaml
schema_version: "1.0"
owner:
  kind: "brand"
  portfolio_id: "codefox"
  id: "kobe"
revision: 3
accepted:
  - id: "feature-x-launch-web-banner-2026-06-19"
    kind: "artifact"
    campaign: "feature-x-launch"
    asset_id: "web-banner"
    path: "packages/branding/public/marketing/products/codefox/kobe/1.1.0/artifacts/feature-x-launch/web-banner.png"
    manifest: "packages/branding/public/marketing/products/codefox/kobe/1.1.0/artifacts/feature-x-launch/manifest.json"
    run_lock: "packages/branding/.harness/out/feature-x-launch/run.lock.json"
    checksum_sha256: "..."
    tags: ["launch", "web-banner"]
    notes: "Accepted by the user after review."
```

The metadata-declared approved asset directory may be a package directory,
asset repository, or git submodule:

```text
<approved>/portfolios/<portfolio-id>/<portfolio-version>/
<approved>/products/<portfolio-id>/<brand-id>/<brand-lock-version>/artifacts/<campaign>/
```

Do not use scratch output as accepted state. Do not add assets to this corpus
without user acceptance.
