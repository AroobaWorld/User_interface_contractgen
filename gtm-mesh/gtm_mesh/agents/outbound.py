"""Outbound agent: writes personalized email + LinkedIn drafts into the review queue."""

from __future__ import annotations

from ..llm import WEB_FETCH, WEB_SEARCH, AgentResult, run_agent
from ..tools import as_json, outbound_tools
from .common import MeshContext, system_prompt

ROLE = (
    "Outbound copywriter and researcher. For each account you find one specific, current reason to reach "
    "out, then write short messages in the client's voice. Drafts go to a human review queue; you never send."
)


def pick_accounts(ctx: MeshContext, limit: int | None = None) -> list[dict]:
    cad = ctx.cfg.cadence
    return ctx.store.accounts(status="new", min_fit=cad.min_fit_score_for_outreach, limit=limit or cad.drafts_per_run)


def run(ctx: MeshContext, limit: int | None = None) -> AgentResult | None:
    cfg = ctx.cfg
    accounts = pick_accounts(ctx, limit)
    if not accounts:
        return None
    for a in accounts:
        a["contacts"] = [
            {k: c[k] for k in ("name", "role", "linkedin_url", "email")} for c in ctx.store.contacts_for(a["domain"])
        ]
    acct_json = as_json(accounts, ["company", "domain", "funnel", "fit_score", "why_fit", "signals", "source_url", "contacts"])
    v = cfg.voice
    banned = "; ".join(v.banned_phrases) or "(none)"
    channels = [c for c in cfg.channels if c in ("email", "linkedin")] or ["email"]

    prompt = f"""Today is {ctx.today}. Write outreach drafts for these {len(accounts)} accounts.

<accounts>
{acct_json}
</accounts>

This week's market brief and hooks:
<market_brief>
{ctx.market_brief()}
</market_brief>

For each account:
1. Spend one to three searches finding a specific, recent reason to reach out (a launch, a hire, a post, \
a pricing change, a funding round). If the account has no contact, try to find one and save it with save_contact.
2. Write drafts for these channels: {', '.join(channels)}.
   - email: under 110 words. Open with the specific reason, connect it to one problem {cfg.name} solves, \
give one proof point from the profile if it fits, close with this ask: {v.call_to_action}. \
Subject line lowercase, under 6 words.
   - linkedin: a connection note under 280 characters. No pitch, just the specific reason and a light ask.
3. Save each draft with save_draft, putting the fact you used and its URL in `personalization`.
4. Set the account status to drafted with set_account_status.
If you find the account is a poor fit after all, set it to disqualified and say why in your summary.

Voice: write as {v.sender_name or 'the sender'}{', ' + v.sender_title if v.sender_title else ''}. Tone: {v.tone}.
Never use: {banned}.
Sign emails with:
{v.signature or v.sender_name or '[sender name]'}"""

    return run_agent(
        client=ctx.client, cfg=cfg, store=ctx.store, agent="outbound",
        system=system_prompt(cfg, ROLE), prompt=prompt,
        tools=[WEB_SEARCH, WEB_FETCH, *outbound_tools(ctx.store)],
        max_iterations=60,
    )
