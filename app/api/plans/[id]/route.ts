import { deleteApprovedPlan, ownerKeyFromHeaders, readApprovedPlan } from "@/db";
import { PlanSnapshotError, validatePlanSnapshot } from "@/lib/plan-validation";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ id: string }> };

async function validatedId(context: RouteContext) {
  const { id } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(id)) throw new PlanSnapshotError("Saved plan id is invalid.");
  return id;
}

export async function GET(request: Request, context: RouteContext) {
  try {
    const id = await validatedId(context);
    const ownerKey = await ownerKeyFromHeaders(request.headers);
    const snapshot = await readApprovedPlan(ownerKey, id);
    if (!snapshot) return Response.json({ error: "Saved plan not found." }, { status: 404 });
    const plan = validatePlanSnapshot(snapshot);
    return Response.json({ plan }, { headers: { "cache-control": "no-store" } });
  } catch (error) {
    const invalid = error instanceof PlanSnapshotError;
    return Response.json(
      { error: invalid ? error.message : "The saved plan could not be loaded." },
      { status: invalid ? 400 : 503, headers: { "cache-control": "no-store" } },
    );
  }
}

export async function DELETE(request: Request, context: RouteContext) {
  try {
    const id = await validatedId(context);
    const ownerKey = await ownerKeyFromHeaders(request.headers);
    const deleted = await deleteApprovedPlan(ownerKey, id);
    if (!deleted) return Response.json({ error: "Saved plan not found." }, { status: 404 });
    return new Response(null, { status: 204 });
  } catch (error) {
    const invalid = error instanceof PlanSnapshotError;
    return Response.json(
      { error: invalid ? error.message : "The saved plan could not be deleted." },
      { status: invalid ? 400 : 503, headers: { "cache-control": "no-store" } },
    );
  }
}
