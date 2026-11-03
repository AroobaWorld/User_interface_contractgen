"""Lead-finding agent: builds the target account list, one funnel at a time."""

from __future__ import annotations

from ..llm import WEB_FETCH, WEB_SEARCH, AgentResult, run_agent
from ..tools import account_tools
from .common import MeshContext, system_prompt

ROLE = (
    "Lead researcher. You find companies that match the client's funnels, confirm the fit with public "
    "evidence, find the right decision-maker, and save both to the shared database."
)

MAX_KNOWN_DOMAINS_IN_PROMPT = 400


def _split(total: int, weights: list[int]) -> list[int]:
    s = sum(weights) or 1
    parts = [max(1, round(total * w / s)) for w in weights]
    return parts


def run(ctx: MeshContext, count: int | None = None) -> AgentResult:
    cfg = ctx.cfg
    total = count or cfg.cadence.accounts_per_run
    funnels = cfg.funnels
    targets = _split(total, [f.target_accounts for f in funnels])
    plan = "\n".join(
        f"- {f.name}: find about {n}. {f.description}\n  Criteria: " + "; ".join(f.criteria)
        for f, n in zip(funnels, targets)
    )
    known = ctx.store.known_domains()
    known_txt = ", ".join(known[-MAX_KNOWN_DOMAINS_IN_PROMPT:]) or "(none yet)"

    prompt = f"""Today is {ctx.today}. Find about {total} new target accounts for {cfg.name}.

Plan by funnel:
{plan}

This week's market brief (use its 'Focus for the lead-finding agent' section to pick signals):
<market_brief>
{ctx.market_brief()}
</market_brief>

Already in the database - do not research these again (the save tool also rejects duplicates):
{known_txt}

How to work:
- Search for buying signals, not just category lists: recent funding, launches, pricing pages, job posts \
for roles this product helps, public complaints about the problem, relevant marketplace or directory listings.
- Open the company's own site to confirm each key criterion before saving. Score fit honestly: 8 or more \
only when every key criterion is confirmed; below 5 means do not save it.
- For each saved account, try to find one or two decision-makers (founder, CEO, or the head of the team \
that owns this problem) from public sources such as the team page, LinkedIn, or press, and save them \
with save_contact. Only record an email if it is published; never guess one.
- Save each account as soon as it is confirmed."""

    return run_agent(
        client=ctx.client, cfg=cfg, store=ctx.store, agent="leads",
        system=system_prompt(cfg, ROLE), prompt=prompt,
        tools=[WEB_SEARCH, WEB_FETCH, *account_tools(ctx.store, [f.name for f in funnels])],
        max_iterations=60,
    )
