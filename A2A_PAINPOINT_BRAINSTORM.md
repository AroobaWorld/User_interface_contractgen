# Why would anyone want A2A? Cotal pain-point brainstorm (4 Nov 2026)

Inputs: Cotal README, Nov 3 investor notes, Oct 26 Sven notes, design-partner pipeline,
AIMZ gtm-mesh code, four parallel brainstorm agents (skeptic, SWP persona, 2-3yr thesis, enterprise).

## The one-line answer
- Nobody wants "agent-to-agent". People want to stop being the copy-paste bus between agents,
  stop paying twice for the same work, and be able to answer "which agent did that, on whose say-so".
- Pain only exists at a BOUNDARY: another machine, another harness, another team, another company.
  Inside one harness on one laptop there is no pain. Hermes / Claude Code Agent Teams win there.

## Three pain primitives that survive every kill test
1. Handoff loss across machines: agent A finishes, agent B (asleep laptop, other harness) never hears.
   Noticed as "ticket done but nothing happened". Metric: % handoffs needing a human nudge.
2. Duplicate claims: two agents take the same ticket. One preprint measured 78% of multi-agent work
   redoing a teammate's task before adding claim leases. Metric: duplicate PRs per 100 tickets.
3. No record of who told which agent what. Noticed at the first post-mortem or InfoSec review.
   Metric: minutes to reconstruct an agent action chain (vs "can't").

## Kill list vs survivors (Hermes-alone test)
- KILL: board governance advisor (single user), event startup (cron), Genesis Robotics (wrong layer,
  needs ROS/MQTT), YC fintech (one agent + API), Immersive Commons (Slack bot does 90%),
  Swiss co (until multi-agent proven).
- SURVIVE: Brazilian e-com (GTM agent -> dev agent on sleeping machine), IT services 400 eng
  (permissions + audit across teams), telco 2,000 eng (isolation across accounts + follow-the-sun),
  investor's China co ONLY if agents at 20 client firms must talk to a central agent while isolated,
  SWP/Alpha (checkpointed workflows resumed across machines, already spending).

## Dogfood check (our own code)
- AIMZ gtm-mesh: 6 agents, fixed order, one SQLite file, one human, one machine. Zero messaging.
  It does not need Cotal, and that is the honest proof of the thesis: no boundary, no pain.
- It WOULD need Cotal the day a client's own agent (e.g. their dev agent on Codex) has to consume
  our leads agent's output, or two Mac Minis run the same client.

## SWP (Steven Wolfe Pereira, Alpha, AI governance ratings)
- Why he burned $10k: probable fleet of per-framework agents (NIST, EU AI Act, ISO 42001), evidence
  extractors, scorer, drafter, skeptic reviewer, across Claude Code + Codex on a 32GB Mac + rented boxes.
  Agents redid each other's work, died when laptop slept, every agent saw every client's data,
  and he could not show which agent produced which score from which document.
- His product is defensibility. A rater who cannot show why a score was given is finished.
- Pain in his words (ranked):
  1. "I can't put a rating in front of a board if I can't show which agent produced which conclusion."
  2. "I spent ten grand and most of it was agents redoing each other's work or dying mid-task."
  3. "Every engagement's data has to stay walled off; right now every agent sees everything."
  4. "I need to be the checkpoint, not the babysitter."
- Angle: the man who rates AI governance was running an ungoverned fleet. Cotal = governance
  substrate (addressed, permissioned, retained, replayable). Caveat: Cotal has retention + ACLs,
  not cryptographic signing. Do not overclaim non-repudiation.
- Order: lead pilot with productivity, close with governance as the reason it is safe to scale.
- 2-week pilot: one anonymised re-rating, hosted space, 5-7 agents, two human checkpoints.
  Metrics: analyst hours -40%; compute per engagement <$1k vs $10k; 100% of scored criteria
  traceable to agent + message + source doc in <60s.
- He gets: hosted instance, white-glove setup, audit-log artifact as template for his own standard.
  Cotal gets: named case study, 3 board/CEO intros, stage quote, Institute note citing Cotal.
- Equity: advisor 0.25-0.5% vesting tied to intros + standards work, separate from a nominal paid
  pilot licence. No equity for usage alone.

## Enterprise (IT services 400 / telco 2,000)
- Failure modes, who feels first, cost: duplicate claims (dev, 2-5% output thrown away);
  reviewer agent never notified (lead, +1-2 days per handoff); no follow-the-sun (telco core pain,
  8-16 idle hours per task); laptop secrets inherited by any agent (security, audit finding to breach);
  no attributable record (blocks SOC2/ISO/telco regs entirely); duplicated token spend (10-20%,
  $50-150/eng/month); platform team cannot see the fleet at all.
- Stopgaps and why they fail: Slack channels (dies at 3am, no claim), Jira automation (tracks tickets
  not agents), in-house bot (Claude-Code-only, breaks when team 7 adopts Codex), mandate one harness
  (devs route around it; every 500+ org already runs 3+ agents incl. shadow).
- Buyer: services firm = Head of Platform, budget dev productivity, sponsor CTO.
  Telco = AI CoE with Security as gatekeeper; budget AI CoE or compliance (easier to unlock).
- Pilot: 2 teams, 15-25 engineers, 2 regions for telco, 2-3 harnesses. One workflow:
  ticket -> implement -> review -> merge with human checkpoint at review.
  Metrics: duplicate claims -> 0; PR-ready-to-review-start latency -50%; 100% attributable actions.
- Wedge ranking: (1) presence + audit log across every harness, 2-3 days to install, best first sale;
  (2) cross-harness ticket claim, best for services firm; (3) follow-the-sun handoff, telco phase 2.
- Pricing: platform fee + per-engineer seat, usage caps. 400-eng pilot ~$60k ACV
  ($15k + ~$10/eng/mo). 2,000-eng rollout $300-400k ACV ($50k + $12-15/eng/mo, security tier).
- "We'll standardise on one harness": "Do. Cotal is what makes the standard enforceable and
  survivable when the harness changes, and it will change within 18 months."

## 2-3 year org thesis (falsifiable)
- Pattern from history: email, Slack, Kafka, PagerDuty each won when a COUNT crossed a square-law
  threshold (people x messages, systems x systems). For agents: agents x harnesses crossing ~10 x 3.
- By end-2028 a 400-eng services firm runs 1,000-2,000 agents across 4+ harnesses; agent count
  passes headcount by Q2 2027.
- 30%+ of work items touch 2+ agents on different harnesses (today <5%).
- Copy-paste bus costs 4-8 h/engineer/week, ~$3-6M/yr fully loaded at that firm.
- 10%+ of agent runs are duplicated; 1 in 20 cross-agent handoffs silently lost, median 1.5 days each.
- 70%+ of agent actions leave no attributable record; first regulatory finding citing "unlogged AI
  action" hits a listed services firm by 2027.
- Agent-held credentials outnumber human-held 3:1.
- "Agent operations" becomes a named team in >25% of 1,000+ person firms.
- Falsifiers: one harness >60% share in services firms by 2028, or multi-agent production climbs
  past 50% without any cross-harness identity/delivery layer.
- Three pilot metrics cheap to instrument in 2 weeks: copy-paste bus hours (daily 3-question poll),
  handoff-loss incidents (diff "agent completed" vs "downstream started" in Jira/Linear),
  % agent sessions with no central record (count harness logs vs central log entries).

## Who shows it first
1. IT services / consultancies 500-5,000 staff: clients dictate the harness so they cannot
   standardise, billable hours make the bus cost visible, 2-4 month cycle. WINNER.
2. Accounting/legal digital coworkers: liability not hours; stronger second wedge once audit story proven.
3. E-com ops. 4. Telcos (9-18 month cycle; keep as pilot, not lead). 5. Communities (fast, unpaid).
   Skip robotics and ratings firms as a segment; SWP is a channel, not a segment.

## Opening lines that never say "protocol"
- "Your engineers are now the most expensive messaging system in the company. How many hours a week
  do they spend carrying one AI's output to another AI?"
- "When one of your agents finishes at 2am and the next one never picks it up, who finds out, and when?"
- "If a client or regulator asked which AI did what on their engagement last Tuesday, could you show
  them, or would you be reconstructing it from screenshots?"

## Honest objections to keep in the deck
- "Agent Teams / Codex multi-agent already do this": yes, inside one harness, one machine, one trust
  domain. If you have no boundary, do not adopt Cotal.
- "NATS + a JSON schema gives me the same": true for week one. The defensible parts are the
  connectors (agents join without adapters) and the opinions (anycast, presence, deny-by-default).
- "A2A has 150 logos": logos are not traffic, and A2A has no offline-peer or ACL story.

## Next moves
- Rewrite the ICP filter as: (1) agents already running, (2) on 2+ harnesses or 2+ machines,
  (3) a handoff that crosses a team or company boundary. Three yeses or walk.
- Re-score the pipeline against that filter; move the kill list to "revisit when they hit a boundary".
- Run the SWP 2-week pilot with the three traceability/cost metrics above; draft LOI around them.
- Pitch IT services firm wedge 1 (presence + audit log) with the 2-team pilot and ~$60k ACV.
- Put the three threshold metrics into every discovery call as questions; they double as lead scoring.
