import type { TravelPlan } from "@/lib/types";
import { PlannerInputError, revisePlan } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json() as { plan?: TravelPlan; feedback?: string };
    if (!body.plan || typeof body.feedback !== "string" || body.feedback.trim().length < 3) {
      throw new PlannerInputError("Add specific revision feedback before resubmitting the plan.");
    }
    const plan = await revisePlan(body.plan, body.feedback);
    return Response.json({ plan }, { headers: { "cache-control": "no-store" } });
  } catch (error) {
    const isInputError = error instanceof PlannerInputError || error instanceof SyntaxError;
    return Response.json(
      { error: isInputError && error instanceof Error ? error.message : "The revision could not be completed. Please try again." },
      { status: isInputError ? 400 : 502, headers: { "cache-control": "no-store" } },
    );
  }
}
