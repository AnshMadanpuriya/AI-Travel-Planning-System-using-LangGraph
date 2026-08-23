import { PlannerInputError, runPlanner } from "@/lib/workflow";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const contentLength = Number(request.headers.get("content-length") || 0);
    if (contentLength > 50_000) {
      return Response.json({ error: "The request is too large." }, { status: 413 });
    }
    const body = await request.json();
    const plan = await runPlanner(body);
    return Response.json({ plan }, { headers: { "cache-control": "no-store" } });
  } catch (error) {
    const isInputError = error instanceof PlannerInputError || error instanceof SyntaxError;
    return Response.json(
      { error: isInputError && error instanceof Error ? error.message : "The planner could not complete this request. Please try again." },
      { status: isInputError ? 400 : 502, headers: { "cache-control": "no-store" } },
    );
  }
}
