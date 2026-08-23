import type {
  AgentStep,
  DayPlan,
  PlannerRequest,
  ResearchBundle,
  TravelPlan,
} from "./types";

const DAY_THEMES = [
  ["Arrive & orient", "A relaxed arrival, hotel check-in, and a short neighborhood walk."],
  ["Landmarks", "Cover the destination's signature sights with realistic transfer buffers."],
  ["Local culture", "Explore markets, museums, craft districts, and a locally loved meal."],
  ["Nature break", "Take a slower outdoor day with a weather-aware backup option."],
  ["Hidden corners", "Visit a quieter neighborhood and independent local businesses."],
  ["Flexible day", "Keep room for a day trip, shopping, or a traveler-selected experience."],
  ["Wrap up", "Use the final hours for a relaxed breakfast, souvenirs, and departure."],
] as const;

export function tripDays(request: PlannerRequest) {
  const start = Date.parse(`${request.startDate}T00:00:00Z`);
  const end = Date.parse(`${request.endDate}T00:00:00Z`);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return 3;
  return Math.min(14, Math.max(1, Math.round((end - start) / 86_400_000) + 1));
}

export function money(amount: number, currency: PlannerRequest["currency"]) {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(Math.max(0, Math.round(amount)));
}

function buildItinerary(request: PlannerRequest): DayPlan[] {
  const days = tripDays(request);
  const dailyExperienceBudget = Math.round(request.budget * 0.18 / days);
  const interests = request.interests.length
    ? request.interests.join(", ").toLowerCase()
    : "local culture and food";

  return Array.from({ length: days }, (_, index) => {
    const theme = DAY_THEMES[Math.min(index, DAY_THEMES.length - 1)];
    const isFirst = index === 0;
    const isLast = index === days - 1 && days > 1;

    return {
      day: index + 1,
      title: isLast ? "Departure with breathing room" : theme[0],
      morning: isFirst
        ? `Travel from ${request.origin}; keep the first block flexible for arrival formalities.`
        : isLast
          ? "Check out, store luggage if needed, and keep the schedule light."
          : `Start with a well-rated ${interests} experience near your base.`,
      afternoon: isLast
        ? "Have an early meal and leave a generous airport or station transfer buffer."
        : theme[1],
      evening: isLast
        ? "Depart with documents, bookings, and local transport details rechecked."
        : "Choose a walkable dinner area and avoid stacking another long transfer.",
      estimatedCost: dailyExperienceBudget,
    };
  });
}

function agentSteps(research: ResearchBundle): AgentStep[] {
  return [
    {
      id: "supervisor",
      label: "Supervisor",
      status: "complete",
      detail: "Validated the request and routed the planning workflow.",
    },
    {
      id: "flight",
      label: "Flight agent",
      status: research.airports.length || research.airlines.length ? "complete" : "skipped",
      detail: research.airports.length
        ? "Matched route context with live airport data."
        : "Prepared route guidance; connect AviationStack for live airport data.",
    },
    {
      id: "stay",
      label: "Stay agent",
      status: research.hotelResearch.length ? "complete" : "skipped",
      detail: research.hotelResearch.length
        ? "Researched current accommodation areas and travel sources."
        : "Prepared stay guidance; connect Tavily for live hotel research.",
    },
    {
      id: "weather",
      label: "Weather agent",
      status: research.weather ? "complete" : "skipped",
      detail: research.weather
        ? "Added a live forecast from Open-Meteo."
        : "Forecast unavailable for the selected dates or destination.",
    },
    {
      id: "budget",
      label: "Budget agent",
      status: "complete",
      detail: "Allocated the budget with a contingency reserve.",
    },
    {
      id: "itinerary",
      label: "Itinerary agent",
      status: "complete",
      detail: "Built a reviewable day-by-day draft.",
    },
  ];
}

export function buildPreviewPlan(
  request: PlannerRequest,
  research: ResearchBundle,
  extraWarnings: string[] = [],
): TravelPlan {
  const days = tripDays(request);
  const allocation = [
    ["Flights & long-distance travel", 0.32],
    ["Accommodation", 0.3],
    ["Food", 0.15],
    ["Local transport", 0.08],
    ["Activities", 0.09],
    ["Contingency", 0.06],
  ] as const;
  const flightLow = request.budget * 0.25;
  const flightHigh = request.budget * 0.36;
  const hotelNightLow = request.budget * 0.24 / Math.max(1, days - 1);
  const hotelNightHigh = request.budget * 0.34 / Math.max(1, days - 1);
  const selectedAirports = research.airports.slice(0, 4);
  const selectedAirlines = research.airlines.slice(0, 5);
  const liveHotels = research.hotelResearch.slice(0, 3);

  return {
    id: crypto.randomUUID(),
    generatedAt: new Date().toISOString(),
    mode: "preview",
    request,
    overview: `${days}-day ${request.travelStyle.toLowerCase()} trip from ${request.origin} to ${request.destination} for ${request.travelers} traveler${request.travelers === 1 ? "" : "s"}. This draft protects transfer time, keeps a contingency reserve, and is ready for your review.`,
    assumptions: [
      "Prices are planning estimates, not bookable quotes.",
      "Entry rules, opening hours, and availability must be checked before payment.",
      "No booking or purchase is made by this planner.",
    ],
    agents: agentSteps(research),
    flight: {
      route: `${request.origin} → ${request.destination}`,
      airports: selectedAirports.length
        ? selectedAirports
        : ["Confirm the most convenient origin and destination airports before booking."],
      airlines: selectedAirlines.length
        ? selectedAirlines
        : ["Compare nonstop and one-stop options on your preferred booking platform."],
      duration: "Confirm against the final route and connection pattern.",
      fareRange: `${money(flightLow, request.currency)}–${money(flightHigh, request.currency)}`,
      advice: "Compare the full trip price, baggage allowance, arrival time, and change policy—not only the headline fare.",
      sourceLabel: selectedAirports.length ? "AviationStack" : "Planning estimate",
    },
    stay: {
      areas: ["A central transit-connected area", "A quieter residential district", "A value-focused area one stop outside the core"],
      options: liveHotels.length
        ? liveHotels.map((item) => ({ name: item.title, note: item.snippet }))
        : [
            { name: "Central base", note: "Best for a first visit and shorter daily transfers." },
            { name: "Neighborhood stay", note: "Better for local atmosphere and calmer evenings." },
            { name: "Transit-value stay", note: "Useful when the main district exceeds the nightly budget." },
          ],
      nightlyRange: `${money(hotelNightLow, request.currency)}–${money(hotelNightHigh, request.currency)}`,
      sourceLabel: liveHotels.length ? "Tavily web research" : "Planning estimate",
    },
    weather: research.weather ?? {
      summary: "A reliable forecast was not available for this location or date window.",
      temperatureRange: "Check again 7–10 days before departure.",
      packing: ["Comfortable walking shoes", "A light rain layer", "One adaptable warm layer"],
      sourceLabel: "Forecast pending",
    },
    budget: {
      total: request.budget,
      currency: request.currency,
      status: "within budget",
      items: allocation.map(([label, share]) => ({
        label,
        amount: Math.round(request.budget * share),
      })),
      tips: [
        "Hold the contingency amount until the last two days.",
        "Compare accommodation by total stay cost, including taxes and transport.",
        "Reprice flights in a private window before payment; do not assume the first fare is final.",
      ],
    },
    itinerary: buildItinerary(request),
    sources: research.sources,
    warnings: [...research.warnings, ...extraWarnings],
    ...(request.revisionFeedback
      ? { revisionNote: `Revision requested: ${request.revisionFeedback}` }
      : {}),
  };
}
