import { listApprovedPlans, ownerKeyFromHeaders, saveApprovedPlan } from "@/db";
import { PlanSnapshotError, validatePlanSnapshot } from "@/lib/plan-validation";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const ownerKey = await ownerKeyFromHeaders(request.headers);
    const limit = Number(new URL(request.url).searchParams.get("limit") || 8);
    const plans = await listApprovedPlans(ownerKey, Number.isFinite(limit) ? limit : 8);
    return Response.json({ plans }, { headers: { "cache-control": "no-store" } });
  } catch {
    return Response.json({ error: "Saved plans are temporarily unavailable." }, { status: 503 });
  }
}

export async function POST(request: Request) {
  try {
    const contentLength = Number(request.headers.get("content-length") || 0);
    if (contentLength > 200_000) return Response.json({ error: "The plan is too large to save." }, { status: 413 });
    const body = await request.json() as { plan?: unknown };
    const plan = validatePlanSnapshot(body.plan);
    const ownerKey = await ownerKeyFromHeaders(request.headers);
    const saved = await saveApprovedPlan(ownerKey, plan);
    return Response.json({ saved }, { status: 201, headers: { "cache-control": "no-store" } });
  } catch (error) {
    const invalid = error instanceof PlanSnapshotError || error instanceof SyntaxError;
    return Response.json(
      { error: invalid && error instanceof Error ? error.message : "The approved plan could not be saved." },
      { status: invalid ? 400 : 503, headers: { "cache-control": "no-store" } },
    );
  }
}
