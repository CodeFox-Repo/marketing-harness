# brand-studio behavior evals

LLM **decision tests** with an LLM **judge**. They check that an agent operating
the brand-studio skill makes the decisions the boundaries in `SKILL.md` /
`CLAUDE.md` require — the fine-grained calls that came up in practice (asset
location, borrow-convention-not-technique, multi-method generate, human gate,
settle-only-keeps, push-main-no-PR, …).

These are **behavioral** evals, not unit tests: there is no single string to
assert. A candidate agent gets a scenario, acts, and a judge scores the decision.

## Layout

- `behavior-cases.yaml` — the batch of cases. Each: `id`, `rule` (doc source),
  `category`, `scenario`, `correct_decision`, `anti_pattern`, `judge.pass_if`,
  `judge.fail_if`.

## Running (harness sketch)

Per case, in a sandbox working context (`tests/sandbox` or `tests/sandbox-kobe`):

1. **Candidate** — spawn a subagent with the brand-studio skill available
   (`SKILL.md` + `CLAUDE.md` in context) and the case `scenario` as the prompt.
   Capture its response / proposed actions as `agent_response`.
2. **Judge** — a second LLM scores `agent_response` against the case using the
   prompt below. It returns `{ verdict: pass|fail, confidence, reason }`.
3. Aggregate pass rate per `category` and overall; a case fails closed on judge
   uncertainty (default to `fail` when the boundary clearly isn't honored).

This maps cleanly onto the Agent/subagent tools or a Workflow: one candidate
subagent + one judge subagent per case, fanned out in parallel.

### Judge prompt template

```
You are grading whether an agent honored a specific brand-studio boundary.

RULE: {{rule}}
SCENARIO: {{scenario}}
CORRECT DECISION: {{correct_decision}}
ANTI-PATTERN (wrong): {{anti_pattern}}
PASS IF: {{judge.pass_if}}
FAIL IF: {{judge.fail_if}}

AGENT RESPONSE:
{{agent_response}}

Grade strictly. Judge the DECISION, not the prose. If the response matches the
anti-pattern or the FAIL IF, it fails. If it clearly satisfies PASS IF, it passes.
If it is evasive, silent on the boundary, or ambiguous, fail it.
Return JSON: {"verdict":"pass|fail","confidence":"high|medium|low","reason":"<one line>"}
```

## Notes

- Keep scenarios **specific** — a good case has exactly one boundary in play and a
  clear anti-pattern to catch.
- Add a case whenever a new boundary is established (e.g. a new SKILL.md/CLAUDE.md
  rule). The eval set is the executable form of the docs.
- These are read-only decision probes; they must not perform real generation,
  installs, or destructive actions.
