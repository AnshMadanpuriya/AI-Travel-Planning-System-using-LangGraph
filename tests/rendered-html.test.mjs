import assert from "node:assert/strict";
import test from "node:test";

async function loadWorker() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${Math.random()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker;
}

class FakePreparedStatement {
  constructor(database, sql, values = []) {
    this.database = database;
    this.sql = sql.replace(/\s+/g, " ").trim();
    this.values = values;
  }

  bind(...values) {
    return new FakePreparedStatement(this.database, this.sql, values);
  }

  async run() {
    if (this.sql.startsWith("CREATE ")) return { success: true, meta: { changes: 0 } };
    if (this.sql.startsWith("INSERT INTO travel_plans")) {
      const [id, ownerKey, origin, destination, startDate, endDate, travelers, budget, currency, mode, revisionCount, planJson] = this.values;
      const previous = this.database.rows.get(id);
      const timestamp = new Date().toISOString();
      this.database.rows.set(id, {
        id,
        owner_key: ownerKey,
        origin,
        destination,
        start_date: startDate,
        end_date: endDate,
        travelers,
        budget,
        currency,
        mode,
        revision_count: revisionCount,
        plan_json: planJson,
        approved_at: previous?.approved_at ?? timestamp,
        updated_at: timestamp,
      });
      return { success: true, meta: { changes: 1 } };
    }
    if (this.sql.startsWith("DELETE FROM travel_plans")) {
      const [id, ownerKey] = this.values;
      const row = this.database.rows.get(id);
      const deleted = Boolean(row && row.owner_key === ownerKey && this.database.rows.delete(id));
      return { success: true, meta: { changes: deleted ? 1 : 0 } };
    }
    throw new Error(`Unsupported fake D1 run: ${this.sql}`);
  }

  async first() {
    const [id, ownerKey] = this.values;
    const row = this.database.rows.get(id);
    return row?.owner_key === ownerKey ? { ...row } : null;
  }

  async all() {
    const [ownerKey, limit] = this.values;
    const results = [...this.database.rows.values()]
      .filter((row) => row.owner_key === ownerKey)
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .slice(0, limit)
      .map((row) => ({ ...row }));
    return { success: true, results, meta: {} };
  }
}

class FakeD1Database {
  rows = new Map();

  prepare(sql) {
    return new FakePreparedStatement(this, sql);
  }

  async batch(statements) {
    return Promise.all(statements.map((statement) => statement.run()));
  }
}

const database = new FakeD1Database();
globalThis.__TRAVEL_AGENT_TEST_DB__ = database;

const bindings = {
  ASSETS: {
    fetch: async () => new Response("Not found", { status: 404 }),
  },
  DB: database,
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
  assert.equal(payload.persistence.database, true);
  assert.equal(payload.persistence.approvalStorage, "hosted-sql");
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

test("validates, persists, restores, and deletes approved plans in D1", async () => {
  const worker = await loadWorker();
  const headers = {
    "content-type": "application/json",
    "oai-authenticated-user-email": "owner@example.test",
  };
  const planResponse = await worker.fetch(
    new Request("http://localhost/api/plan", {
      method: "POST",
      headers,
      body: JSON.stringify({
        origin: "Indore",
        destination: "Kyoto",
        startDate: "2026-11-02",
        endDate: "2026-11-05",
        travelers: 2,
        budget: 140000,
        currency: "INR",
        travelStyle: "Balanced",
        interests: ["Culture", "Food"],
        notes: "Prefer rail travel",
      }),
    }),
    { ...bindings, TRAVEL_AGENT_DEMO_MODE: "true" },
    context,
  );
  assert.equal(planResponse.status, 200);
  const { plan } = await planResponse.json();
  assert.equal(plan.agents.length, 6);

  const invalidResponse = await worker.fetch(
    new Request("http://localhost/api/plans", {
      method: "POST",
      headers,
      body: JSON.stringify({ plan: { ...plan, budget: { ...plan.budget, total: plan.budget.total + 1 } } }),
    }),
    bindings,
    context,
  );
  assert.equal(invalidResponse.status, 400);

  const saveResponse = await worker.fetch(
    new Request("http://localhost/api/plans", {
      method: "POST",
      headers,
      body: JSON.stringify({ plan }),
    }),
    bindings,
    context,
  );
  assert.equal(saveResponse.status, 201);
  const { saved } = await saveResponse.json();
  assert.equal(saved.destination, "Kyoto");

  const listResponse = await worker.fetch(
    new Request("http://localhost/api/plans?limit=8", { headers }),
    bindings,
    context,
  );
  assert.equal(listResponse.status, 200);
  const listed = await listResponse.json();
  assert.equal(listed.plans.length, 1);
  assert.equal(listed.plans[0].id, plan.id);

  const readResponse = await worker.fetch(
    new Request(`http://localhost/api/plans/${plan.id}`, { headers }),
    bindings,
    context,
  );
  assert.equal(readResponse.status, 200);
  const restored = await readResponse.json();
  assert.equal(restored.plan.destination, undefined);
  assert.equal(restored.plan.request.destination, "Kyoto");

  const deleteResponse = await worker.fetch(
    new Request(`http://localhost/api/plans/${plan.id}`, { method: "DELETE", headers }),
    bindings,
    context,
  );
  assert.equal(deleteResponse.status, 204);
  assert.equal(database.rows.size, 0);
});
