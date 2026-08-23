import type { SavedPlanSummary, TravelPlan } from "@/lib/types";

declare global {
  var __TRAVEL_AGENT_TEST_DB__: D1Database | undefined;
}

const CREATE_TABLE = `CREATE TABLE IF NOT EXISTS travel_plans (
  id TEXT PRIMARY KEY NOT NULL,
  owner_key TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  travelers INTEGER NOT NULL CHECK (travelers BETWEEN 1 AND 20),
  budget INTEGER NOT NULL CHECK (budget BETWEEN 100 AND 1000000000),
  currency TEXT NOT NULL CHECK (currency IN ('INR', 'USD', 'EUR', 'GBP')),
  mode TEXT NOT NULL CHECK (mode IN ('live', 'preview')),
  revision_count INTEGER NOT NULL DEFAULT 0 CHECK (revision_count >= 0),
  plan_json TEXT NOT NULL,
  approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

const CREATE_OWNER_UPDATED_INDEX =
  "CREATE INDEX IF NOT EXISTS travel_plans_owner_updated_idx ON travel_plans (owner_key, updated_at)";
const CREATE_OWNER_DESTINATION_INDEX =
  "CREATE INDEX IF NOT EXISTS travel_plans_owner_destination_idx ON travel_plans (owner_key, destination)";

let initialization: Promise<void> | null = null;

async function runtimeDatabase(): Promise<D1Database | undefined> {
  try {
    const runtime = await import("cloudflare:workers");
    return runtime.env.DB;
  } catch {
    return globalThis.__TRAVEL_AGENT_TEST_DB__;
  }
}

async function database(): Promise<D1Database> {
  const db = await runtimeDatabase();
  if (!db) throw new Error("The hosted plan database is unavailable.");
  return db;
}

export async function databaseConfigured() {
  return Boolean(await runtimeDatabase());
}

async function ensureDatabase() {
  if (!initialization) {
    const db = await database();
    initialization = db.batch([
      db.prepare(CREATE_TABLE),
      db.prepare(CREATE_OWNER_UPDATED_INDEX),
      db.prepare(CREATE_OWNER_DESTINATION_INDEX),
    ]).then(() => undefined).catch((error: unknown) => {
      initialization = null;
      throw error;
    });
  }
  await initialization;
}

export async function ownerKeyFromHeaders(headers: Headers) {
  const identity = (
    headers.get("oai-authenticated-user-email") ||
    headers.get("oai-authenticated-user-id") ||
    "site-owner"
  ).trim().toLowerCase().slice(0, 320);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(identity));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function rowToSummary(row: Record<string, unknown>): SavedPlanSummary {
  return {
    id: String(row.id),
    origin: String(row.origin),
    destination: String(row.destination),
    startDate: String(row.start_date),
    endDate: String(row.end_date),
    travelers: Number(row.travelers),
    budget: Number(row.budget),
    currency: String(row.currency) as SavedPlanSummary["currency"],
    mode: String(row.mode) as SavedPlanSummary["mode"],
    revisionCount: Number(row.revision_count),
    approvedAt: String(row.approved_at),
    updatedAt: String(row.updated_at),
  };
}

export async function saveApprovedPlan(ownerKey: string, plan: TravelPlan) {
  await ensureDatabase();
  const db = await database();
  await db.prepare(`INSERT INTO travel_plans (
    id, owner_key, origin, destination, start_date, end_date, travelers,
    budget, currency, mode, revision_count, plan_json
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  ON CONFLICT(id) DO UPDATE SET
    origin = excluded.origin,
    destination = excluded.destination,
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    travelers = excluded.travelers,
    budget = excluded.budget,
    currency = excluded.currency,
    mode = excluded.mode,
    revision_count = excluded.revision_count,
    plan_json = excluded.plan_json,
    updated_at = CURRENT_TIMESTAMP
  WHERE travel_plans.owner_key = excluded.owner_key`).bind(
    plan.id,
    ownerKey,
    plan.request.origin,
    plan.request.destination,
    plan.request.startDate,
    plan.request.endDate,
    plan.request.travelers,
    Math.round(plan.request.budget),
    plan.request.currency,
    plan.mode,
    plan.revisionNote ? 1 : 0,
    JSON.stringify(plan),
  ).run();

  const saved = await db.prepare(
    "SELECT id, origin, destination, start_date, end_date, travelers, budget, currency, mode, revision_count, approved_at, updated_at FROM travel_plans WHERE id = ? AND owner_key = ?",
  ).bind(plan.id, ownerKey).first<Record<string, unknown>>();
  if (!saved) throw new Error("The approved plan could not be confirmed in the database.");
  return rowToSummary(saved);
}

export async function listApprovedPlans(ownerKey: string, limit = 8) {
  await ensureDatabase();
  const db = await database();
  const result = await db.prepare(
    "SELECT id, origin, destination, start_date, end_date, travelers, budget, currency, mode, revision_count, approved_at, updated_at FROM travel_plans WHERE owner_key = ? ORDER BY updated_at DESC, approved_at DESC LIMIT ?",
  ).bind(ownerKey, Math.min(20, Math.max(1, limit))).all<Record<string, unknown>>();
  return result.results.map(rowToSummary);
}

export async function readApprovedPlan(ownerKey: string, id: string) {
  await ensureDatabase();
  const db = await database();
  const row = await db.prepare(
    "SELECT plan_json FROM travel_plans WHERE id = ? AND owner_key = ?",
  ).bind(id, ownerKey).first<{ plan_json: string }>();
  return row ? JSON.parse(row.plan_json) as unknown : null;
}

export async function deleteApprovedPlan(ownerKey: string, id: string) {
  await ensureDatabase();
  const db = await database();
  const result = await db.prepare(
    "DELETE FROM travel_plans WHERE id = ? AND owner_key = ?",
  ).bind(id, ownerKey).run();
  return Number(result.meta.changes ?? 0) > 0;
}
