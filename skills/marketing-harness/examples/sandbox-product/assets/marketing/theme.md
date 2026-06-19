---
repo:
  id: sandbox-product
  name: Sandbox Product
version: 1.0.0
producer:
  params:
    seed_strategy: fixed
    seed: 101
    output_format: png
global:
  style-fragment:
    base:
      $value: precise product launch visual with clean geometry
      $type: text
  color:
    primary:
      $value: "#174A5A"
      $type: color
alias:
  style:
    launch-hero:
      $value:
        prompt: "{global.style-fragment.base}"
        palette:
          - "{global.color.primary}"
        negative: ""
        references: []
      $type: composite
---

# Sandbox Product Theme

This fixture is intentionally small. It exists so maintainers can run the
harness against a fake product repo before trying path or state changes in a
real product repository.
