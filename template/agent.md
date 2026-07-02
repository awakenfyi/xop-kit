# {{AGENT_NAME}}

One line: what this agent is for.

## Identity
Describe the role in plain language. What it does, who it serves, the tone it holds.

## Capability
- skills/ — the playbooks this agent loads when relevant
- tools/ — what it is allowed to touch

## Conduct
This agent's judgment lives in `conduct/`. Those rules decide what ships, what holds,
and what it must never do — enforced before any output leaves the loop.
Start with the rules already scaffolded there; add your own with `xop add-rule`.

The gate that governs all of them: `conduct/_gate.yaml`.
