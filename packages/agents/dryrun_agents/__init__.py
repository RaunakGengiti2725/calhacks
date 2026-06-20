"""dryrun_agents — thin orchestration over core + providers.

IMPORTANT: this package's top level must stay import-light. The reusable
in-process cascade (`dryrun_agents.shared.cascade`) and the CLI import only core
+ providers, never `uagents`, so the mock demo runs without the agent framework.
The uAgent runner modules (Phase 4) import `uagents` and are only loaded when the
`agents` extra is installed.
"""
