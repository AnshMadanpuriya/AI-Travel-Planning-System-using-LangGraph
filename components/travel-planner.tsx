"use client";

import { FormEvent, useMemo, useState } from "react";
import Image from "next/image";

import { money } from "@/lib/fallback-plan";
import type { PlannerRequest, TravelPlan } from "@/lib/types";

const INTERESTS = ["Food", "Culture", "Nature", "History", "Shopping", "Nightlife", "Wellness", "Adventure"];

function isoDate(offsetDays: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

const DEFAULT_REQUEST: PlannerRequest = {
  origin: "Indore",
  destination: "Tokyo",
  startDate: isoDate(30),
  endDate: isoDate(36),
  travelers: 2,
  budget: 200000,
  currency: "INR",
  travelStyle: "Balanced",
  interests: ["Food", "Culture", "Nature"],
  notes: "Prefer walkable areas and avoid overnight flights.",
};

function planToMarkdown(plan: TravelPlan) {
  const lines = [
    `# ${plan.request.destination} travel plan`,
    "",
    plan.overview,
    "",
    `- Route: ${plan.flight.route}`,
    `- Dates: ${plan.request.startDate} to ${plan.request.endDate}`,
    `- Travelers: ${plan.request.travelers}`,
    `- Budget: ${money(plan.budget.total, plan.budget.currency)}`,
    "",
    "## Day-by-day itinerary",
    "",
  ];
  plan.itinerary.forEach((day) => {
    lines.push(
      `### Day ${day.day}: ${day.title}`,
      "",
      `- Morning: ${day.morning}`,
      `- Afternoon: ${day.afternoon}`,
      `- Evening: ${day.evening}`,
      `- Estimated daily spend: ${money(day.estimatedCost, plan.budget.currency)}`,
      "",
    );
  });
  lines.push("## Important", "", ...plan.assumptions.map((item) => `- ${item}`));
  return lines.join("\n");
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error || "Request failed.");
  return payload;
}

function ModeBadge({ mode }: { mode: TravelPlan["mode"] }) {
  return (
    <span className={`mode-badge ${mode}`}>
      <span className="status-dot" />
      {mode === "live" ? "AI + live research" : "Safe preview mode"}
    </span>
  );
}

function PlanResult({
  plan,
  approved,
  feedback,
  busy,
  onFeedback,
  onApprove,
  onRevise,
  onReset,
}: {
  plan: TravelPlan;
  approved: boolean;
  feedback: string;
  busy: boolean;
  onFeedback: (value: string) => void;
  onApprove: () => void;
  onRevise: () => void;
  onReset: () => void;
}) {
  const download = () => {
    const blob = new Blob([planToMarkdown(plan)], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${plan.request.destination.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-travel-plan.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="result-shell" aria-labelledby="plan-heading">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Your draft is ready</p>
          <h2 id="plan-heading">{plan.request.destination}, thoughtfully planned.</h2>
          <p>{plan.overview}</p>
        </div>
        <div className="result-actions">
          <ModeBadge mode={plan.mode} />
          <button className="quiet-button" onClick={download}>Download .md</button>
          <button className="quiet-button" onClick={onReset}>New plan</button>
        </div>
      </div>

      {plan.warnings.length > 0 && (
        <div className="warning-box" role="status">
          <strong>Before you rely on this draft</strong>
          <ul>{plan.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul>
        </div>
      )}

      <div className="agent-strip" aria-label="Agent workflow">
        {plan.agents.map((agent, index) => (
          <div className={`agent-step ${agent.status}`} key={agent.id}>
            <span className="agent-index">{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{agent.label}</strong><small>{agent.detail}</small></div>
          </div>
        ))}
      </div>

      <div className="insight-grid">
        <article className="insight-card flight-card">
          <div className="card-kicker"><span>✦</span> Flight guidance</div>
          <h3>{plan.flight.route}</h3>
          <p className="big-stat">{plan.flight.fareRange}</p>
          <p>{plan.flight.duration}</p>
          <div className="tag-row">{plan.flight.airports.slice(0, 3).map((item) => <span key={item}>{item}</span>)}</div>
          <p className="card-note">{plan.flight.advice}</p>
          <small>{plan.flight.sourceLabel}</small>
        </article>

        <article className="insight-card stay-card">
          <div className="card-kicker"><span>⌂</span> Where to stay</div>
          <h3>{plan.stay.nightlyRange} / night</h3>
          <div className="stack-list">
            {plan.stay.options.slice(0, 3).map((option) => (
              <div key={option.name}><strong>{option.name}</strong><p>{option.note}</p></div>
            ))}
          </div>
          <small>{plan.stay.sourceLabel}</small>
        </article>

        <article className="insight-card weather-card">
          <div className="card-kicker"><span>☼</span> Weather window</div>
          <p className="big-stat">{plan.weather.temperatureRange}</p>
          <p>{plan.weather.summary}</p>
          <div className="tag-row">{plan.weather.packing.map((item) => <span key={item}>{item}</span>)}</div>
          <small>{plan.weather.sourceLabel}</small>
        </article>
      </div>

      <div className="plan-grid">
        <article className="itinerary-panel">
          <div className="section-title-row">
            <div><p className="eyebrow">Itinerary agent</p><h3>Day-by-day rhythm</h3></div>
            <span>{plan.itinerary.length} days</span>
          </div>
          <div className="timeline">
            {plan.itinerary.map((day) => (
              <div className="timeline-day" key={day.day}>
                <div className="day-marker"><span>{day.day}</span></div>
                <div className="day-content">
                  <div className="day-title"><h4>{day.title}</h4><span>{money(day.estimatedCost, plan.budget.currency)}</span></div>
                  <dl>
                    <div><dt>Morning</dt><dd>{day.morning}</dd></div>
                    <div><dt>Afternoon</dt><dd>{day.afternoon}</dd></div>
                    <div><dt>Evening</dt><dd>{day.evening}</dd></div>
                  </dl>
                </div>
              </div>
            ))}
          </div>
        </article>

        <aside className="budget-panel">
          <p className="eyebrow">Budget agent</p>
          <h3>{money(plan.budget.total, plan.budget.currency)}</h3>
          <span className="budget-status">{plan.budget.status}</span>
          <div className="budget-list">
            {plan.budget.items.map((item) => (
              <div key={item.label}>
                <div><span>{item.label}</span><strong>{money(item.amount, plan.budget.currency)}</strong></div>
                <span className="budget-track"><span style={{ width: `${Math.max(4, item.amount / plan.budget.total * 100)}%` }} /></span>
              </div>
            ))}
          </div>
          <h4>Keep the budget healthy</h4>
          <ul>{plan.budget.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul>
        </aside>
      </div>

      <section className={`review-panel ${approved ? "approved" : ""}`}>
        <div className="review-copy">
          <p className="eyebrow">Human in the loop</p>
          <h3>{approved ? "Plan approved" : "Review before you act"}</h3>
          <p>{approved
            ? "Your approved draft is ready to download. Prices and availability still need a final check before payment."
            : "Nothing is booked automatically. Approve the draft or tell the itinerary agent exactly what to change."}</p>
        </div>
        {!approved && (
          <div className="review-form">
            <label htmlFor="feedback">Revision feedback</label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(event) => onFeedback(event.target.value)}
              placeholder="Example: Replace Day 3 with a quieter nature day and reduce the hotel budget."
            />
            <div className="review-actions">
              <button className="quiet-button" onClick={onRevise} disabled={busy || feedback.trim().length < 3}>
                {busy ? "Replanning…" : "Request revision"}
              </button>
              <button className="primary-button compact" onClick={onApprove}>Approve draft</button>
            </div>
          </div>
        )}
      </section>

      <details className="source-drawer">
        <summary>Sources, assumptions & safety notes</summary>
        <div className="source-content">
          <div><h4>Assumptions</h4><ul>{plan.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div>
          <div><h4>Research sources</h4>{plan.sources.length
            ? <ul>{plan.sources.map((source) => <li key={`${source.label}-${source.url}`}><a href={source.url} target="_blank" rel="noreferrer">{source.label}</a></li>)}</ul>
            : <p>No live source links were used in preview mode.</p>}</div>
        </div>
      </details>
    </section>
  );
}

export default function TravelPlanner() {
  const [request, setRequest] = useState<PlannerRequest>(DEFAULT_REQUEST);
  const [plan, setPlan] = useState<TravelPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [approved, setApproved] = useState(false);

  const duration = useMemo(() => {
    const start = Date.parse(`${request.startDate}T00:00:00Z`);
    const end = Date.parse(`${request.endDate}T00:00:00Z`);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return 0;
    return Math.round((end - start) / 86_400_000) + 1;
  }, [request.startDate, request.endDate]);

  const setField = <K extends keyof PlannerRequest>(key: K, value: PlannerRequest[K]) => {
    setRequest((current) => ({ ...current, [key]: value }));
  };

  const toggleInterest = (interest: string) => {
    setField("interests", request.interests.includes(interest)
      ? request.interests.filter((item) => item !== interest)
      : [...request.interests, interest]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setApproved(false);
    try {
      const payload = await postJson<{ plan: TravelPlan }>("/api/plan", request);
      setPlan(payload.plan);
      setTimeout(() => document.getElementById("plan-heading")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The planner could not start.");
    } finally {
      setBusy(false);
    }
  };

  const revise = async () => {
    if (!plan) return;
    setBusy(true);
    setError("");
    try {
      const payload = await postJson<{ plan: TravelPlan }>("/api/revise", { plan, feedback });
      setPlan(payload.plan);
      setFeedback("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The revision could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  const approve = () => {
    if (!plan) return;
    setApproved(true);
    try { window.localStorage.setItem("approved-travel-plan", JSON.stringify(plan)); } catch { /* storage is optional */ }
  };

  const reset = () => {
    setPlan(null);
    setApproved(false);
    setFeedback("");
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="AI Travel Agent home">
          <span className="brand-mark">A</span>
          <span>Atlas<span className="brand-accent">AI</span></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#planner">Planner</a>
          <a href="#workflow">How it works</a>
          <a href="https://github.com/AnshMadanpuriya/AI-Travel-Planning-System-using-LangGraph" target="_blank" rel="noreferrer">GitHub ↗</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero" id="planner">
          <div className="hero-copy">
            <div className="eyebrow-row"><span className="eyebrow">Multi-agent trip planning</span><span className="mini-pill">Review before action</span></div>
            <h1>A travel plan that <em>shows its work.</em></h1>
            <p className="hero-lede">Six specialist agents research, budget, and shape your trip. You inspect the draft, request changes, and approve the final plan—nothing gets booked behind your back.</p>

            <form className="planner-form" onSubmit={submit}>
              <div className="route-row">
                <label><span>From</span><input value={request.origin} onChange={(event) => setField("origin", event.target.value)} placeholder="Indore" required /></label>
                <span className="route-arrow" aria-hidden="true">→</span>
                <label><span>To</span><input value={request.destination} onChange={(event) => setField("destination", event.target.value)} placeholder="Tokyo" required /></label>
              </div>

              <div className="form-grid four">
                <label><span>Start date</span><input type="date" value={request.startDate} onChange={(event) => setField("startDate", event.target.value)} required /></label>
                <label><span>End date</span><input type="date" min={request.startDate} value={request.endDate} onChange={(event) => setField("endDate", event.target.value)} required /></label>
                <label><span>Travelers</span><input type="number" min="1" max="20" value={request.travelers} onChange={(event) => setField("travelers", Number(event.target.value))} required /></label>
                <label><span>Trip length</span><div className="read-only-field">{duration || "—"} days</div></label>
              </div>

              <div className="form-grid three">
                <label className="budget-field"><span>Total budget</span><div className="input-pair"><select aria-label="Currency" value={request.currency} onChange={(event) => setField("currency", event.target.value as PlannerRequest["currency"])}><option>INR</option><option>USD</option><option>EUR</option><option>GBP</option></select><input type="number" min="100" value={request.budget} onChange={(event) => setField("budget", Number(event.target.value))} required /></div></label>
                <label><span>Travel style</span><select value={request.travelStyle} onChange={(event) => setField("travelStyle", event.target.value as PlannerRequest["travelStyle"])}><option>Budget</option><option>Balanced</option><option>Premium</option></select></label>
                <label><span>Preferences</span><input value={request.notes} onChange={(event) => setField("notes", event.target.value)} placeholder="No overnight flights" /></label>
              </div>

              <fieldset className="interest-fieldset">
                <legend>What should the plan prioritize?</legend>
                <div className="interest-row">{INTERESTS.map((interest) => <button type="button" aria-pressed={request.interests.includes(interest)} className={request.interests.includes(interest) ? "selected" : ""} key={interest} onClick={() => toggleInterest(interest)}>{interest}</button>)}</div>
              </fieldset>

              <div className="submit-row">
                <div><strong>Ready in one draft</strong><span>Live providers are used only when server-side keys are configured.</span></div>
                <button className="primary-button" type="submit" disabled={busy}>{busy ? <><span className="spinner" /> Agents are planning…</> : <>Build my trip <span>↗</span></>}</button>
              </div>
              {error && <p className="form-error" role="alert">{error}</p>}
            </form>
          </div>

          <aside className="hero-visual" aria-label="Example destination">
            <Image
              src="https://images.unsplash.com/photo-1686931265920-bc6c061da8a2?auto=format&fit=crop&w=1200&q=82"
              alt="Chureito Pagoda with Mount Fuji in the background"
              fill
              priority
              sizes="(max-width: 1120px) 100vw, 38vw"
              unoptimized
            />
            <div className="image-shade" />
            <div className="destination-card">
              <span>Example destination</span>
              <strong>Tokyo + Fuji</strong>
              <p>Culture, food, nature · 7 days</p>
            </div>
            <div className="floating-stat"><span>6</span><div><strong>specialist agents</strong><small>one reviewed plan</small></div></div>
            <a className="photo-credit" href="https://unsplash.com/photos/a-pagoda-with-a-mountain-in-the-background-AeYjrcT5Jhc" target="_blank" rel="noreferrer">Photo: wei / Unsplash</a>
          </aside>
        </section>

        <section className="workflow-section" id="workflow">
          <div><p className="eyebrow">One request, coordinated expertise</p><h2>The supervisor sends each detail to the right agent.</h2></div>
          <div className="workflow-list">
            {["Guardrail & routing", "Flights & stays", "Weather & budget", "Itinerary & approval"].map((label, index) => <div key={label}><span>{String(index + 1).padStart(2, "0")}</span><strong>{label}</strong></div>)}
          </div>
        </section>

        {plan && (
          <PlanResult
            plan={plan}
            approved={approved}
            feedback={feedback}
            busy={busy}
            onFeedback={setFeedback}
            onApprove={approve}
            onRevise={revise}
            onReset={reset}
          />
        )}
      </main>

      <footer>
        <div><strong>AtlasAI</strong><span>Built from five LangGraph travel-planning projects.</span></div>
        <p>Planning guidance only. Verify prices, entry rules, safety information, and availability with official providers.</p>
      </footer>
    </>
  );
}
