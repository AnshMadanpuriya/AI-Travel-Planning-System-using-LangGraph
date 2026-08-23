import { tripDays } from "@/lib/fallback-plan";
import { normalizeRequest, PlannerInputError } from "@/lib/workflow";
import type { AgentStep, TravelPlan } from "@/lib/types";

export class PlanSnapshotError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PlanSnapshotError";
  }
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new PlanSnapshotError(`${label} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, label: string, max: number) {
  if (typeof value !== "string" || !value.trim() || value.length > max) {
    throw new PlanSnapshotError(`${label} is invalid.`);
  }
  return value;
}

function stringList(value: unknown, label: string, maxItems: number, maxLength: number) {
  if (!Array.isArray(value) || value.length > maxItems) {
    throw new PlanSnapshotError(`${label} is invalid.`);
  }
  return value.map((item, index) => text(item, `${label} item ${index + 1}`, maxLength));
}

export function validatePlanSnapshot(input: unknown): TravelPlan {
  const plan = record(input, "Plan");
  const encoded = new TextEncoder().encode(JSON.stringify(plan));
  if (encoded.byteLength > 180_000) throw new PlanSnapshotError("The plan is too large to save.");

  const id = text(plan.id, "Plan id", 64);
  if (!/^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(id)) throw new PlanSnapshotError("Plan id is invalid.");
  const generatedAt = text(plan.generatedAt, "Generation timestamp", 40);
  if (!Number.isFinite(Date.parse(generatedAt))) throw new PlanSnapshotError("Generation timestamp is invalid.");
  if (plan.mode !== "live" && plan.mode !== "preview") throw new PlanSnapshotError("Plan mode is invalid.");

  let request;
  try {
    request = normalizeRequest(plan.request);
  } catch (error) {
    if (error instanceof PlannerInputError) throw new PlanSnapshotError(error.message);
    throw error;
  }

  text(plan.overview, "Overview", 1_000);
  stringList(plan.assumptions, "Assumptions", 12, 500);
  stringList(plan.warnings, "Warnings", 20, 600);

  if (!Array.isArray(plan.agents) || plan.agents.length !== 6) {
    throw new PlanSnapshotError("All six agent results are required before approval.");
  }
  const requiredAgents = new Set<AgentStep["id"]>(["supervisor", "flight", "stay", "weather", "budget", "itinerary"]);
  for (const item of plan.agents) {
    const agent = record(item, "Agent result");
    if (!requiredAgents.delete(agent.id as AgentStep["id"])) throw new PlanSnapshotError("Agent results are duplicated or invalid.");
    if (agent.status !== "complete" && agent.status !== "skipped") throw new PlanSnapshotError("Agent status is invalid.");
    text(agent.label, "Agent label", 80);
    text(agent.detail, "Agent detail", 500);
  }
  if (requiredAgents.size) throw new PlanSnapshotError("An agent result is missing.");

  const budget = record(plan.budget, "Budget");
  if (Number(budget.total) !== request.budget || budget.currency !== request.currency) {
    throw new PlanSnapshotError("Budget totals do not match the validated request.");
  }
  if (!Array.isArray(budget.items) || budget.items.length < 1 || budget.items.length > 12) {
    throw new PlanSnapshotError("Budget allocation is invalid.");
  }
  let allocationTotal = 0;
  for (const value of budget.items) {
    const item = record(value, "Budget item");
    text(item.label, "Budget label", 100);
    const amount = Number(item.amount);
    if (!Number.isFinite(amount) || amount < 0 || amount > request.budget) throw new PlanSnapshotError("Budget amount is invalid.");
    allocationTotal += amount;
  }
  if (Math.abs(allocationTotal - request.budget) > budget.items.length) {
    throw new PlanSnapshotError("Budget allocation must reconcile with the total budget.");
  }

  if (!Array.isArray(plan.itinerary) || plan.itinerary.length !== tripDays(request)) {
    throw new PlanSnapshotError("The itinerary must contain one validated entry per planned day.");
  }
  plan.itinerary.forEach((value, index) => {
    const day = record(value, `Day ${index + 1}`);
    if (Number(day.day) !== index + 1) throw new PlanSnapshotError("Itinerary day numbers are invalid.");
    text(day.title, "Day title", 120);
    text(day.morning, "Morning plan", 600);
    text(day.afternoon, "Afternoon plan", 600);
    text(day.evening, "Evening plan", 600);
    const estimatedCost = Number(day.estimatedCost);
    if (!Number.isFinite(estimatedCost) || estimatedCost < 0 || estimatedCost > request.budget) {
      throw new PlanSnapshotError("An itinerary cost is invalid.");
    }
  });

  record(plan.flight, "Flight guidance");
  record(plan.stay, "Stay guidance");
  record(plan.weather, "Weather guidance");
  if (!Array.isArray(plan.sources) || plan.sources.length > 20) throw new PlanSnapshotError("Research sources are invalid.");
  for (const value of plan.sources) {
    const source = record(value, "Research source");
    text(source.label, "Source label", 160);
    const url = text(source.url, "Source URL", 500);
    if (!/^https:\/\//i.test(url)) throw new PlanSnapshotError("Only secure research source URLs can be saved.");
  }

  return { ...plan, id, generatedAt, request } as TravelPlan;
}
