from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import anthropic

from ..config import ClientConfig
from ..store import Store

SHARED_RULES = """\
You are one agent in a go-to-market (GTM) mesh that AI-MZ runs for the client described below. \
The agents share one database and run in order: research, lead finding, outreach drafting, content, \
weekly report. A human reviews every draft and post before anything is sent or published, so your job \
is to hand them work that is accurate and ready to use.

How to work:
- Use facts you verified with web search or web fetch during this run, or facts in the client profile. \
Put the source URL next to any claim a reviewer would want to check.
- Never invent customers, metrics, quotes, people or email addresses. If you cannot verify something, \
leave it out and say so in your summary.
- Skip any company that matches the client's exclude list.
- Save results with your tools as you go rather than all at the end, so nothing is lost if the run stops early.
- End with a short plain-text summary: what you saved, what you skipped and why, and anything a human \
should check or do next."""


def system_prompt(cfg: ClientConfig, role: str) -> str:
    # Stable per client + role so the prefix caches across runs.
    return f"{SHARED_RULES}\n\nYour role: {role}\n\n<client_profile>\n{cfg.brief()}</client_profile>"


@dataclass
class MeshContext:
    cfg: ClientConfig
    store: Store
    client: anthropic.Anthropic

    @property
    def today(self) -> str:
        return date.today().isoformat()

    def market_brief(self) -> str:
        b = self.store.latest_brief("market")
        if not b:
            return "(no market brief yet)"
        return f"(saved {b['created_at']})\n{b['body']}"
