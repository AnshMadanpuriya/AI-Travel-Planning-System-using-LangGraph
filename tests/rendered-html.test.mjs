import assert from "node:assert/strict";
import test from "node:test";

async function loadWorker() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${Math.random()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker;
}

const bindings = {
  ASSETS: {
    fetch: async () => new Response("Not found", { status: 404 }),
  },
};

const context = {
  waitUntil() {},
  passThroughOnException() {},
};

test("renders the complete travel planner instead of starter content", async () => {
  const worker = await loadWorker();
  const response = await worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    bindings,
    context,
  );

  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /AI Travel Agent System/);
  assert.match(html, /A travel plan that/);
  assert.match(html, /Review before action/);
  assert.doesNotMatch(html, /Starter Project/);
});

test("exposes a healthy preview-mode API without revealing secrets", async () => {
  const worker = await loadWorker();
  const response = await worker.fetch(
    new Request("http://localhost/api/health", { headers: { accept: "application/json" } }),
    bindings,
    context,
  );

  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.status, "ok");
  assert.equal(payload.mode, "preview");
  assert.equal(Object.prototype.hasOwnProperty.call(payload, "keys"), false);
});

test("runs the LangGraph planner end to end in safe preview mode", async () => {
  const worker = await loadWorker();
  const response = await worker.fetch(
    new Request("http://localhost/api/plan", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        origin: "Indore",
        destination: "Tokyo",
        startDate: "2026-10-10",
        endDate: "2026-10-16",
        travelers: 2,
        budget: 200000,
        currency: "INR",
        travelStyle: "Balanced",
        interests: ["Food", "Culture"],
        notes: "Prefer walkable areas",
      }),
    }),
    { ...bindings, TRAVEL_AGENT_DEMO_MODE: "true" },
    context,
  );

  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.plan.mode, "preview");
  assert.equal(payload.plan.itinerary.length, 7);
  assert.equal(payload.plan.agents[0].label, "Supervisor");
  assert.equal(payload.plan.budget.items.length, 6);
});
