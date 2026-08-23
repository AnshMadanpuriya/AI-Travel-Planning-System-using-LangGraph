export const dynamic = "force-dynamic";

export async function GET() {
  const previewMode = process.env.TRAVEL_AGENT_DEMO_MODE === "true" || !process.env.GROQ_API_KEY;
  return Response.json(
    {
      status: "ok",
      mode: previewMode ? "preview" : "live",
      providers: {
        ai: Boolean(process.env.GROQ_API_KEY) && !previewMode,
        search: Boolean(process.env.TAVILY_API_KEY) && !previewMode,
        flights: Boolean(process.env.AVIATION_STACK_API_KEY || process.env.AVIATIONSTACK_API_KEY) && !previewMode,
        weather: true,
      },
    },
    { headers: { "cache-control": "no-store" } },
  );
}
