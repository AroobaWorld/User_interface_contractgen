"""Thin wrapper around the Anthropic SDK tool runner.

Every agent goes through ``run_agent`` so that cost tracking, the per-run
spend cap, refusal handling and run logging live in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import anthropic

from .config import ClientConfig
from .store import Store

# Estimated USD per 1M tokens. Cache writes are billed at 1.25x the input price.
# These are estimates for the spend cap and reports; your Anthropic invoice is the source of truth.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache_read": 0.01},
    "claude-fable-5-1": {"in": 10.00, "out": 50.00, "cache_read": 0.25},
}
WEB_SEARCH_USD_PER_1K = 10.00

WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 25}
WEB_FETCH = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 25}

# Server-side refusal fallback: if a safety classifier declines, the API reroutes
# to a suitable model inside the same call instead of returning nothing.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MAX_TOKENS = 16000  # non-streaming ceiling that stays under SDK HTTP timeouts


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    web_searches: int = 0

    def add(self, usage: Any) -> None:
        if usage is None:
            return
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        stu = getattr(usage, "server_tool_use", None)
        if stu is not None:
            self.web_searches += getattr(stu, "web_search_requests", 0) or 0

    @property
    def cost_usd(self) -> float:
        p = PRICES.get(self.model, PRICES["claude-opus-5-5"])
        cost = (
            self.input_tokens * p["in"]
            + self.output_tokens * p["out"]
            + self.cache_read_tokens * p["cache_read"]
            + self.cache_write_tokens * p["in"] * 1.25
        ) / 1_000_000
        cost += self.web_searches * WEB_SEARCH_USD_PER_1K / 1000
        return round(cost, 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "web_searches": self.web_searches,
            "cost_usd": self.cost_usd,
        }


@dataclass
class AgentResult:
    agent: str
    status: str  # ok | budget_stopped | refused | max_tokens | error
    text: str
    usage: Usage
    turns: int = 0
    notes: list[str] = field(default_factory=list)


def make_client() -> anthropic.Anthropic:
    # Credentials come from ANTHROPIC_API_KEY (or an `ant auth login` profile).
    return anthropic.Anthropic(max_retries=4)


def _text_of(message: Any) -> str:
    return "\n".join(b.text for b in getattr(message, "content", []) if getattr(b, "type", "") == "text").strip()


def run_agent(
    *,
    client: anthropic.Anthropic,
    cfg: ClientConfig,
    store: Store,
    agent: str,
    system: str,
    prompt: str,
    tools: Iterable[Any],
    max_iterations: int = 40,
    effort: str | None = None,
) -> AgentResult:
    """Run one agent to completion with the SDK tool runner, under a USD cap."""
    model = cfg.models.model
    usage = Usage(model=model)
    cap = cfg.models.max_usd_per_agent_run
    run_id = store.start_run(agent)
    status, text, turns, notes = "ok", "", 0, []
    last = None

    try:
        runner = client.beta.messages.tool_runner(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=list(tools),
            thinking={"type": "adaptive"},
            output_config={"effort": effort or cfg.models.effort},
            cache_control={"type": "ephemeral"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
            max_iterations=max_iterations,
        )
        for message in runner:
            last = message
            turns += 1
            usage.add(getattr(message, "usage", None))
            if message.stop_reason == "refusal":
                status = "refused"
                details = getattr(message, "stop_details", None)
                notes.append(f"refused: {getattr(details, 'category', None)}")
                break
            if usage.cost_usd >= cap:
                status = "budget_stopped"
                notes.append(f"stopped at ${usage.cost_usd:.2f} (cap ${cap:.2f})")
                break
        if last is not None:
            text = _text_of(last)
            if last.stop_reason == "max_tokens":
                status = "max_tokens" if status == "ok" else status
            elif last.stop_reason == "pause_turn" and status == "ok":
                notes.append("ended on pause_turn (hit max_iterations); partial work is saved")
    except anthropic.AuthenticationError:
        status, text = "error", "Authentication failed: set ANTHROPIC_API_KEY on this machine."
    except anthropic.RateLimitError as e:
        status, text = "error", f"Rate limited after SDK retries: {e.message}"
    except anthropic.APIStatusError as e:
        status, text = "error", f"API error {e.status_code}: {e.message}"
    except anthropic.APIConnectionError:
        status, text = "error", "Network error reaching the Claude API."
    finally:
        summary = text if not notes else f"{text}\n\n[{'; '.join(notes)}]"
        store.finish_run(run_id, status, usage.as_dict(), summary)

    return AgentResult(agent=agent, status=status, text=text, usage=usage, turns=turns, notes=notes)


def single_call(
    *, client: anthropic.Anthropic, cfg: ClientConfig, store: Store, agent: str, system: str, prompt: str,
    effort: str | None = None,
) -> AgentResult:
    """One request, no tools (used by the weekly report)."""
    usage = Usage(model=cfg.models.model)
    run_id = store.start_run(agent)
    status, text, notes = "ok", "", []
    try:
        message = client.beta.messages.create(
            model=cfg.models.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort or cfg.models.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        usage.add(message.usage)
        text = _text_of(message)
        if message.stop_reason == "refusal":
            status = "refused"
        elif message.stop_reason == "max_tokens":
            status = "max_tokens"
    except anthropic.AuthenticationError:
        status, text = "error", "Authentication failed: set ANTHROPIC_API_KEY on this machine."
    except anthropic.APIStatusError as e:
        status, text = "error", f"API error {e.status_code}: {e.message}"
    except anthropic.APIConnectionError:
        status, text = "error", "Network error reaching the Claude API."
    finally:
        store.finish_run(run_id, status, usage.as_dict(), text)
    return AgentResult(agent=agent, status=status, text=text, usage=usage, turns=1, notes=notes)
