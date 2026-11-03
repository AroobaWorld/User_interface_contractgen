"""Profile agent: researches a new client and fills in their YAML profile."""

from __future__ import annotations

from ..llm import WEB_FETCH, WEB_SEARCH, AgentResult, run_agent
from ..tools import profile_tools
from .common import MeshContext, system_prompt

ROLE = (
    "GTM strategist onboarding a new client. You research the company from public sources and draft the "
    "profile every other agent will work from: what they sell, to whom, and why buyers pick them."
)


def run(ctx: MeshContext) -> AgentResult:
    cfg = ctx.cfg
    prompt = f"""Today is {ctx.today}. Research {cfg.name} and fill in their GTM profile.

Starting points:
- Website: {cfg.website or '(not given - find the official site first, and if more than one company matches the name, stop and say so in your summary instead of guessing)'}
- Founder notes: {cfg.notes or '(none)'}

Read their site (home, pricing, docs, customers, about), then search for press, funding, reviews, \
competitors, and where their buyers talk. Then design 2-3 funnels ordered from fastest to close to \
biggest prize. A good default shape is: quick adopters who can self-serve or start fast, then larger \
companies with real budgets, then a small set of flagship design partners. Make each funnel's criteria \
specific and checkable from public information (for example "public pricing page under $X/month", \
"raised a seed or Series A in the last 12 months", "uses Shopify").

Call save_profile exactly once with everything, then summarize what you found and list the open \
questions the founder needs to answer."""

    return run_agent(
        client=ctx.client, cfg=cfg, store=ctx.store, agent="profile",
        system=system_prompt(cfg, ROLE), prompt=prompt,
        tools=[WEB_SEARCH, WEB_FETCH, *profile_tools(cfg)],
    )
