"""Tools the agents call to read and write the client's store.

Each factory binds the tools to one client's Store, so an agent working for
Greta can never write into Psyler's database.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import beta_tool
from pydantic import BaseModel, Field

from .config import ClientConfig, Funnel, save_client
from .store import ACCOUNT_STATUSES, Store


def account_tools(store: Store, funnels: list[str]) -> list[Any]:
    funnel_list = ", ".join(funnels) or "default"

    @beta_tool
    def save_account(company: str, domain: str, funnel: str, fit_score: int, why_fit: str,
                     signals: str = "", source_url: str = "") -> str:
        """Save a target company that fits the ICP. Duplicate domains are ignored.

        Args:
            company: Company name.
            domain: Company website domain, e.g. acme.com.
            funnel: Which funnel this account belongs to (must be one of the client's funnel names).
            fit_score: 1-10 fit against the funnel criteria. 8+ means every key criterion is confirmed with evidence.
            why_fit: One or two sentences on why they fit, citing the concrete evidence you found.
            signals: Recent buying signals (funding, launches, hiring, pricing changes, public pain), with dates.
            source_url: The URL where you confirmed the key evidence.
        """
        if funnels and funnel not in funnels:
            return f"Error: funnel must be one of: {funnel_list}"
        try:
            acct_id, created = store.add_account(company, domain, funnel, fit_score, why_fit, signals, source_url)
        except ValueError as e:
            return f"Error: {e}"
        return f"saved account #{acct_id}" if created else f"already known (account #{acct_id}); skip it"

    @beta_tool
    def save_contact(domain: str, name: str, role: str, linkedin_url: str = "", email: str = "",
                     source_url: str = "") -> str:
        """Save a decision-maker at a saved account. Only use people and emails you found published publicly.

        Args:
            domain: The account's domain (the account must already be saved).
            name: Full name.
            role: Their current title.
            linkedin_url: Public profile URL if found.
            email: Only a work email that is publicly published. Never guess or construct an email pattern.
            source_url: Where you found this person.
        """
        try:
            cid, created = store.add_contact(domain, name, role, linkedin_url, email, source_url)
        except ValueError as e:
            return f"Error: {e}"
        return f"saved contact #{cid}" if created else f"contact already saved (#{cid})"

    return [save_account, save_contact]


def outbound_tools(store: Store) -> list[Any]:
    @beta_tool
    def save_draft(domain: str, channel: str, body: str, subject: str = "", personalization: str = "",
                   contact_name: str = "") -> str:
        """Save an outreach draft to the human review queue. Nothing is ever sent automatically.

        Args:
            domain: The account's domain.
            channel: email or linkedin.
            body: The message body, ready to send after review. Plain text.
            subject: Email subject line (email only). Lowercase, under 6 words, no clickbait.
            personalization: The specific fact this message is built on, with its source URL, so the reviewer can verify it.
            contact_name: The saved contact this is for, if any.
        """
        if channel not in ("email", "linkedin"):
            return "Error: channel must be email or linkedin"
        try:
            did = store.add_draft(domain, channel, body, subject, personalization, contact_name)
        except ValueError as e:
            return f"Error: {e}"
        return f"saved draft #{did} for review"

    @beta_tool
    def save_contact(domain: str, name: str, role: str, linkedin_url: str = "", email: str = "",
                     source_url: str = "") -> str:
        """Save a decision-maker at a saved account. Only use people and emails you found published publicly.

        Args:
            domain: The account's domain.
            name: Full name.
            role: Their current title.
            linkedin_url: Public profile URL if found.
            email: Only a work email that is publicly published. Never guess or construct an email pattern.
            source_url: Where you found this person.
        """
        try:
            cid, created = store.add_contact(domain, name, role, linkedin_url, email, source_url)
        except ValueError as e:
            return f"Error: {e}"
        return f"saved contact #{cid}" if created else f"contact already saved (#{cid})"

    @beta_tool
    def set_account_status(domain: str, status: str) -> str:
        """Update an account's pipeline status.

        Args:
            domain: The account's domain.
            status: One of new, drafted, contacted, replied, meeting, won, lost, disqualified.
        """
        if status not in ACCOUNT_STATUSES:
            return f"Error: status must be one of {', '.join(ACCOUNT_STATUSES)}"
        return "updated" if store.set_account_status(domain, status) else "Error: unknown domain"

    return [save_draft, save_contact, set_account_status]


def content_tools(store: Store, channels: list[str]) -> list[Any]:
    @beta_tool
    def save_content(kind: str, channel: str, title: str, body: str, hook: str = "") -> str:
        """Save a finished content piece for review.

        Args:
            kind: post, thread, reddit_post, blog_outline, blog_post, directory_listing, or ad_copy.
            channel: Where it will be published, e.g. linkedin, x, reddit, blog, directory_listing.
            title: Short internal title.
            body: The full, ready-to-publish text.
            hook: The one-line hook or angle it is built on.
        """
        if channels and channel not in channels:
            return f"Error: channel must be one of {', '.join(channels)}"
        cid = store.add_content(kind, channel, title, body, hook)
        return f"saved content #{cid}"

    return [save_content]


def brief_tools(store: Store) -> list[Any]:
    @beta_tool
    def save_brief(kind: str, body: str) -> str:
        """Save a research brief in Markdown. Call once with the complete brief.

        Args:
            kind: market (for the weekly market and positioning brief).
            body: The full brief in Markdown, with source URLs inline.
        """
        bid = store.add_brief(kind, body)
        return f"saved brief #{bid}"

    return [save_brief]


class FunnelIn(BaseModel):
    name: str = Field(description="Short snake_case name, e.g. startup_quick_adopters")
    description: str
    criteria: list[str]
    target_accounts: int = 100


def profile_tools(cfg: ClientConfig) -> list[Any]:
    """Used by `gtm-mesh new` to fill in a client profile from public research."""

    @beta_tool
    def save_profile(one_liner: str, product: str, pricing: str, differentiators: list[str],
                     competitors: list[str], proof_points: list[str], funnels: list[FunnelIn],
                     exclude: list[str], weekly_hooks: list[str], notes: str) -> str:
        """Save the researched client profile. Call exactly once, at the end.

        Args:
            one_liner: What the company does, in one plain sentence a buyer would understand.
            product: What the product does, who uses it, and how it is bought (self-serve, sales-led, API).
            pricing: Public pricing if found, otherwise 'not public'.
            differentiators: 3-5 concrete reasons a buyer picks them over alternatives.
            competitors: Direct competitors and the main status-quo alternative.
            proof_points: Public customers, metrics, funding, press. Only facts you found, with sources.
            funnels: 2-3 target segments, from fastest-to-close to biggest-prize.
            exclude: Company types the mesh should not target.
            weekly_hooks: 5 content hooks or angles that would resonate with the funnels.
            notes: Open questions and anything the founder must confirm before outreach starts.
        """
        cfg.one_liner = one_liner
        cfg.product = product
        cfg.pricing = pricing
        cfg.differentiators = differentiators
        cfg.competitors = competitors
        cfg.proof_points = proof_points
        cfg.funnels = [Funnel(**f.model_dump()) for f in funnels]
        cfg.exclude = exclude
        cfg.weekly_hooks = weekly_hooks
        cfg.notes = (cfg.notes + "\n\n" + notes).strip() if cfg.notes else notes
        path = save_client(cfg)
        return f"profile saved to {path.name}"

    return [save_profile]


def as_json(rows: list[dict[str, Any]], keys: list[str]) -> str:
    return json.dumps([{k: r.get(k) for k in keys} for r in rows], indent=2, default=str)
