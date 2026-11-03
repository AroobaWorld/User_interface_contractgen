"""Research agent: weekly market, competitor and positioning brief."""

from __future__ import annotations

from ..llm import WEB_FETCH, WEB_SEARCH, AgentResult, run_agent
from ..tools import brief_tools
from .common import MeshContext, system_prompt

ROLE = (
    "Market research and positioning analyst. You find out what changed in the client's market this week "
    "and turn it into a brief the lead-finding, outreach and content agents will work from."
)


def run(ctx: MeshContext) -> AgentResult:
    cfg = ctx.cfg
    previous = ctx.store.latest_brief("market")
    prev_text = previous["body"] if previous else "(none - this is the first brief)"
    funnels = ", ".join(f.name for f in cfg.funnels) or "(none defined yet)"

    prompt = f"""Today is {ctx.today}. Write this week's market brief for {cfg.name} ({cfg.website or 'website not set'}).

Last week's brief, for continuity (say what changed rather than repeating it):
<previous_brief>
{prev_text}
</previous_brief>

Cover these sections, in Markdown:
1. Positioning check - how {cfg.name} describes itself on its site versus the words buyers in the funnels use. \
Is it clear within five seconds what it does and who it is for? Suggest sharper wording if not.
2. Competitor moves in the last 30 days - launches, pricing changes, funding, notable hires, messaging shifts.
3. Discoverability - search the queries a buyer would type. Note where {cfg.name} does and does not show up, \
including relevant directories and marketplaces (for example G2, Product Hunt, AI-agent directories, \
app marketplaces relevant to their stack), and the quickest gaps to close.
4. Buyer pain in public - where people in the funnels ({funnels}) are talking about this problem \
(Reddit, Hacker News, LinkedIn, X, community forums) and what they are saying, with links.
5. Five hooks for this week - each one tied to a piece of evidence above.
6. Focus for the lead-finding agent - which funnel to push this week and which specific buying signals \
to search for (for example recent funding, a pricing-page change, a job post, a launch).

When the brief is complete, save it with save_brief(kind="market"), then give your summary."""

    return run_agent(
        client=ctx.client, cfg=cfg, store=ctx.store, agent="research",
        system=system_prompt(cfg, ROLE), prompt=prompt,
        tools=[WEB_SEARCH, WEB_FETCH, *brief_tools(ctx.store)],
    )
