"""Offline tests: a fake Claude client stands in for the API, so no key or network is needed."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
import yaml


@pytest.fixture()
def mesh(tmp_path, monkeypatch):
    """Point the mesh at a temp home with one bootstrapped client, then reload modules."""
    clients = tmp_path / "clients"
    clients.mkdir()
    profile = {
        "slug": "greta",
        "name": "Greta",
        "website": "https://greta.example",
        "product": "Retention API for self-serve SaaS.",
        "funnels": [
            {"name": "quick_adopters", "description": "Self-serve startups", "criteria": ["public pricing"],
             "target_accounts": 100},
            {"name": "design_partners", "description": "Flagship brands", "criteria": ["big brand"],
             "target_accounts": 10},
        ],
        "voice": {"sender_name": "Aroob Manzoor"},
    }
    (clients / "greta.yaml").write_text(yaml.safe_dump(profile))
    (clients / "psyler.yaml").write_text(yaml.safe_dump({"slug": "psyler", "name": "Psyler"}))
    monkeypatch.setenv("GTM_MESH_HOME", str(tmp_path))
    monkeypatch.setenv("GTM_MESH_OUTPUT", str(tmp_path / "output"))
    import gtm_mesh.config as config
    importlib.reload(config)
    import gtm_mesh.tools, gtm_mesh.llm, gtm_mesh.agents.common, gtm_mesh.review, gtm_mesh.orchestrator, gtm_mesh.cli
    for m in ("tools", "llm", "review"):
        importlib.reload(getattr(gtm_mesh, m))
    import gtm_mesh.agents as agents
    for m in ("common", "research", "leads", "outbound", "content", "report", "profile"):
        importlib.reload(getattr(agents, m))
    importlib.reload(agents)
    importlib.reload(gtm_mesh.orchestrator)
    importlib.reload(gtm_mesh.cli)
    return SimpleNamespace(home=tmp_path, config=config)


def usage(inp=1000, out=500, searches=0):
    return SimpleNamespace(
        input_tokens=inp, output_tokens=out, cache_read_input_tokens=0, cache_creation_input_tokens=0,
        server_tool_use=SimpleNamespace(web_search_requests=searches),
    )


def msg(text="", stop="end_turn", u=None):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop,
                           usage=u or usage(), stop_details=None)


class FakeClient:
    """Mimics client.beta.messages.tool_runner / create. `script` maps agent name -> list of tool calls."""

    def __init__(self, script=None, per_turn_usage=None):
        self.script = script or {}
        self.calls = []
        self.per_turn_usage = per_turn_usage
        self.beta = SimpleNamespace(messages=SimpleNamespace(tool_runner=self._runner, create=self._create))

    def _runner(self, **kw):
        self.calls.append(kw)
        tools = {getattr(t, "name", None): t for t in kw["tools"] if hasattr(t, "call")}
        role_line = kw["system"].split("Your role: ")[1].split(".")[0]
        steps = next((v for k, v in self.script.items() if k in role_line), [])

        def gen():
            for name, args in steps:
                tools[name].call(args)
                yield msg(stop="tool_use", u=self.per_turn_usage() if self.per_turn_usage else usage(searches=1))
            yield msg("done: summary")
        return gen()

    def _create(self, **kw):
        self.calls.append(kw)
        return msg("# Weekly update\nAll good.")


def test_profiles_load(mesh):
    assert mesh.config.list_clients() == ["greta", "psyler"]
    assert mesh.config.load_client("greta").is_bootstrapped
    assert not mesh.config.load_client("psyler").is_bootstrapped


def test_brief_is_deterministic(mesh):
    c = mesh.config.load_client("greta")
    assert c.brief() == mesh.config.load_client("greta").brief()


def test_store_dedupes_and_normalizes(tmp_path):
    from gtm_mesh.store import Store
    s = Store(":memory:")
    a, created = s.add_account("Acme", "https://www.Acme.com/pricing", "quick_adopters", 12, "why")
    assert created and s.get_account("acme.com")["fit_score"] == 10
    _, created2 = s.add_account("Acme", "acme.com", "quick_adopters", 7, "why")
    assert not created2
    s.add_contact("acme.com", "Jo Doe", "CEO")
    d = s.add_draft("acme.com", "email", "hi", subject="s", contact_name="Jo Doe")
    assert s.drafts()[0]["contact_name"] == "Jo Doe"
    assert s.set_draft_status([d], "approved") == 1
    assert s.drafts() == []


def test_cost_math():
    from gtm_mesh.llm import Usage
    u = Usage(model="claude-opus-5-5")
    u.add(usage(inp=1_000_000, out=100_000, searches=10))
    assert u.cost_usd == pytest.approx(4.0 + 2.0 + 0.10)


def test_full_weekly_cycle_writes_everything(mesh):
    from gtm_mesh.orchestrator import run_cycle
    from gtm_mesh.store import Store

    script = {
        "Market research": [("save_brief", {"kind": "market", "body": "# Brief\nhooks"})],
        "Lead researcher": [
            ("save_account", {"company": "Acme", "domain": "acme.com", "funnel": "quick_adopters",
                              "fit_score": 8, "why_fit": "public $49 plan", "source_url": "https://acme.com/pricing"}),
            ("save_contact", {"domain": "acme.com", "name": "Jo Doe", "role": "CEO"}),
            ("save_account", {"company": "Bad", "domain": "bad.com", "funnel": "not_a_funnel",
                              "fit_score": 9, "why_fit": "x"}),
        ],
        "Outbound copywriter": [
            ("save_draft", {"domain": "acme.com", "channel": "email", "subject": "your $49 plan",
                            "body": "Hi Jo...", "personalization": "pricing page", "contact_name": "Jo Doe"}),
            ("set_account_status", {"domain": "acme.com", "status": "drafted"}),
        ],
        "Content strategist": [("save_content", {"kind": "post", "channel": "linkedin", "title": "t",
                                                 "body": "b", "hook": "h"})],
    }
    fake = FakeClient(script)
    logs = []
    results = run_cycle("greta", "weekly", log=logs.append, client=fake)

    assert [r.agent for r in results] == ["research", "leads", "outbound", "content", "report"]
    assert all(r.status == "ok" for r in results)
    cfg = mesh.config.load_client("greta")
    s = Store(cfg.output_dir / "mesh.db")
    assert s.known_domains() == ["acme.com"]  # bad funnel rejected
    assert s.get_account("acme.com")["status"] == "drafted"
    assert len(s.drafts()) == 1 and len(s.content()) == 1
    assert s.latest_brief("weekly_report")
    assert list((cfg.output_dir / "review").glob("*-review.md"))
    assert list((cfg.output_dir / "reports").glob("*-weekly.md"))

    first = fake.calls[0]
    assert first["model"] == "claude-opus-5-5"
    assert first["fallbacks"] == "default"
    assert first["thinking"] == {"type": "adaptive"}
    assert "tool_choice" not in first
    assert any(t.get("type") == "web_search_20260209" for t in first["tools"] if isinstance(t, dict))

    # second weekly run within 7 days skips research
    run_cycle("greta", "weekly", log=logs.append, client=FakeClient(script))
    assert any("brief is fresh" in line for line in logs)


def test_budget_cap_stops_agent(mesh):
    from gtm_mesh.agents import MeshContext, leads
    from gtm_mesh.store import Store

    cfg = mesh.config.load_client("greta")
    cfg.models.max_usd_per_agent_run = 0.5
    steps = [("save_account", {"company": f"C{i}", "domain": f"c{i}.com", "funnel": "quick_adopters",
                               "fit_score": 7, "why_fit": "x"}) for i in range(10)]
    fake = FakeClient({"Lead researcher": steps}, per_turn_usage=lambda: usage(inp=100_000, out=0))
    ctx = MeshContext(cfg=cfg, store=Store(":memory:"), client=fake)
    r = leads.run(ctx)
    assert r.status == "budget_stopped"
    assert len(ctx.store.known_domains()) < 10


def test_unbootstrapped_client_is_refused(mesh):
    from gtm_mesh.orchestrator import run_cycle
    with pytest.raises(RuntimeError, match="profile is missing"):
        run_cycle("psyler", "weekly", log=lambda _: None, client=FakeClient())


def test_profile_agent_fills_yaml(mesh):
    from gtm_mesh.agents import MeshContext, profile
    from gtm_mesh.store import Store

    cfg = mesh.config.load_client("psyler")
    fake = FakeClient({"GTM strategist": [("save_profile", {
        "one_liner": "Psyler does X.", "product": "API", "pricing": "not public",
        "differentiators": ["fast"], "competitors": ["Y"], "proof_points": [],
        "funnels": [{"name": "quick_adopters", "description": "d", "criteria": ["c"]}],
        "exclude": [], "weekly_hooks": ["h"], "notes": "confirm pricing",
    })]})
    profile.run(MeshContext(cfg=cfg, store=Store(":memory:"), client=fake))
    reloaded = mesh.config.load_client("psyler")
    assert reloaded.is_bootstrapped and reloaded.funnels[0].name == "quick_adopters"


def test_cli_status_and_approve(mesh, capsys):
    from gtm_mesh.cli import main
    from gtm_mesh.store import Store
    cfg = mesh.config.load_client("greta")
    s = Store(cfg.output_dir / "mesh.db")
    s.add_account("Acme", "acme.com", "quick_adopters", 8, "why")
    did = s.add_draft("acme.com", "email", "hi")
    assert main(["status", "greta"]) == 0
    assert main(["approve", "greta", str(did)]) == 0
    assert main(["mark", "greta", "acme.com", "replied"]) == 0
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "1 draft(s) marked approved" in out and "greta" in out and "psyler" in out
