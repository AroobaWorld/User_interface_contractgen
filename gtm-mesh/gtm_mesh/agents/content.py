"""Content agent: turns the week's hooks into ready-to-post pieces."""

from __future__ import annotations

from ..llm import WEB_SEARCH, AgentResult, run_agent
from ..tools import content_tools
from .common import MeshContext, system_prompt

ROLE = (
    "Content strategist and writer. You turn this week's hooks into posts and pages that the client's "
    "buyers would actually stop and read, in the client's voice."
)

CHANNEL_GUIDE = {
    "linkedin": "LinkedIn post, 120-220 words, first line is the hook, short paragraphs, one clear takeaway, "
                "no hashtag walls (max 3). Best slots: Tuesday/Thursday 9am or 5pm Pacific.",
    "x": "X thread of 4-7 posts, each under 270 characters, first post stands alone.",
    "reddit": "Reddit post that is genuinely useful on its own (a lesson, data, or a how-to). No links to the "
              "client, no pitch; name the subreddit it fits and follow that community's rules. Never plan DMs.",
    "blog": "Blog post outline built around one search query a buyer would type: H1, meta description, "
            "H2/H3 structure, key points per section, and the target query.",
    "directory_listing": "Listing copy for a directory or marketplace: name, 60-character tagline, "
                         "150-word description, 5 tags, and which directory it is for.",
}


def run(ctx: MeshContext, count: int | None = None) -> AgentResult:
    cfg = ctx.cfg
    n = count or cfg.cadence.content_pieces_per_run
    channels = cfg.content_channels
    guide = "\n".join(f"- {c}: {CHANNEL_GUIDE.get(c, 'Use the norms of this channel.')}" for c in channels)
    hooks = "\n".join(f"- {h}" for h in cfg.weekly_hooks) or "(use the hooks in the market brief)"
    v = cfg.voice

    prompt = f"""Today is {ctx.today}. Write {n} content pieces for {cfg.name} this week, spread across these channels:
{guide}

Hooks the founder wants this week:
{hooks}

This week's market brief:
<market_brief>
{ctx.market_brief()}
</market_brief>

Rules:
- Each piece is built on one hook and one concrete detail (a number, an example, a customer situation from \
the profile or from your research). Check any timely reference with a quick search.
- Voice: {v.tone}. Write as {v.sender_name or cfg.name}. Never use: {'; '.join(v.banned_phrases) or '(none)'}.
- Save each piece with save_content as soon as it is done.
- In your summary, list the pieces with a suggested publish day for each."""

    return run_agent(
        client=ctx.client, cfg=cfg, store=ctx.store, agent="content",
        system=system_prompt(cfg, ROLE), prompt=prompt,
        tools=[{**WEB_SEARCH, "max_uses": 10}, *content_tools(ctx.store, channels)],
    )
