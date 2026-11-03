"""Client profiles for the GTM mesh.

Each client (e.g. Greta, Psyler) is one YAML file in ``clients/``. The file
describes who they sell to, how they sound, and how hard the mesh should run
each week. Everything an agent knows about a client comes from this file plus
what earlier runs saved in the client's database.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

MESH_HOME = Path(os.environ.get("GTM_MESH_HOME", Path(__file__).resolve().parent.parent))
CLIENTS_DIR = MESH_HOME / "clients"
OUTPUT_DIR = Path(os.environ.get("GTM_MESH_OUTPUT", MESH_HOME / "output"))

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Funnel(BaseModel):
    """One target segment, e.g. 'startup quick adopters' or 'enterprise moonshots'."""

    name: str
    description: str
    criteria: list[str] = Field(default_factory=list)
    target_accounts: int = 100


class Voice(BaseModel):
    sender_name: str = ""
    sender_title: str = ""
    tone: str = "warm, direct, specific, zero hype"
    call_to_action: str = "a 15-minute call this week"
    banned_phrases: list[str] = Field(
        default_factory=lambda: [
            "I hope this email finds you well",
            "synergy",
            "game-changer",
            "revolutionize",
            "quick question",
        ]
    )
    signature: str = ""


class Cadence(BaseModel):
    accounts_per_run: int = 20
    drafts_per_run: int = 10
    content_pieces_per_run: int = 6
    min_fit_score_for_outreach: int = 6
    research_refresh_days: int = 7


class ModelSettings(BaseModel):
    model: str = "claude-opus-5-5"
    effort: Effort = "high"
    max_usd_per_agent_run: float = 8.0


class ClientConfig(BaseModel):
    slug: str
    name: str
    website: str = ""
    one_liner: str = ""
    product: str = ""
    pricing: str = ""
    differentiators: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    funnels: list[Funnel] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=lambda: ["email", "linkedin"])
    content_channels: list[str] = Field(
        default_factory=lambda: ["linkedin", "x", "reddit", "blog", "directory_listing"]
    )
    weekly_hooks: list[str] = Field(default_factory=list)
    voice: Voice = Field(default_factory=Voice)
    cadence: Cadence = Field(default_factory=Cadence)
    models: ModelSettings = Field(default_factory=ModelSettings)
    notes: str = ""

    @property
    def is_bootstrapped(self) -> bool:
        """True once the profile has enough detail for leads and outreach."""
        return bool(self.product.strip() and self.funnels)

    @property
    def output_dir(self) -> Path:
        path = OUTPUT_DIR / self.slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def brief(self) -> str:
        """Stable text description of the client, used in every agent's system prompt.

        Deterministic on purpose (fixed key order, no timestamps) so the prompt
        prefix stays byte-identical across calls and gets cached.
        """
        data = self.model_dump(exclude={"models", "cadence", "slug"})
        return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, width=100)


def client_path(slug: str) -> Path:
    return CLIENTS_DIR / f"{slug}.yaml"


def load_client(slug: str) -> ClientConfig:
    path = client_path(slug)
    if not path.exists():
        raise FileNotFoundError(
            f"No client profile at {path}. Create one with: gtm-mesh new {slug} --website <url>"
        )
    raw = yaml.safe_load(path.read_text()) or {}
    raw.setdefault("slug", slug)
    return ClientConfig.model_validate(raw)


def save_client(cfg: ClientConfig) -> Path:
    path = client_path(cfg.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump()
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))
    return path


def list_clients() -> list[str]:
    if not CLIENTS_DIR.exists():
        return []
    return sorted(p.stem for p in CLIENTS_DIR.glob("*.yaml") if not p.stem.startswith("_"))
