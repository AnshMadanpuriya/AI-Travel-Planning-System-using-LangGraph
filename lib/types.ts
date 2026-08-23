export type Currency = "INR" | "USD" | "EUR" | "GBP";

export type PlannerRequest = {
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
  travelers: number;
  budget: number;
  currency: Currency;
  travelStyle: "Budget" | "Balanced" | "Premium";
  interests: string[];
  notes?: string;
  revisionFeedback?: string;
};

export type AgentStep = {
  id: "supervisor" | "flight" | "stay" | "weather" | "budget" | "itinerary";
  label: string;
  status: "complete" | "skipped";
  detail: string;
};

export type FlightPlan = {
  route: string;
  airports: string[];
  airlines: string[];
  duration: string;
  fareRange: string;
  advice: string;
  sourceLabel: string;
};

export type StayPlan = {
  areas: string[];
  options: Array<{ name: string; note: string }>;
  nightlyRange: string;
  sourceLabel: string;
};

export type WeatherPlan = {
  summary: string;
  temperatureRange: string;
  packing: string[];
  sourceLabel: string;
};

export type BudgetItem = {
  label: string;
  amount: number;
};

export type DayPlan = {
  day: number;
  title: string;
  morning: string;
  afternoon: string;
  evening: string;
  estimatedCost: number;
};

export type TravelPlan = {
  id: string;
  generatedAt: string;
  mode: "live" | "preview";
  request: PlannerRequest;
  overview: string;
  assumptions: string[];
  agents: AgentStep[];
  flight: FlightPlan;
  stay: StayPlan;
  weather: WeatherPlan;
  budget: {
    total: number;
    currency: Currency;
    status: "within budget" | "tight" | "over budget";
    items: BudgetItem[];
    tips: string[];
  };
  itinerary: DayPlan[];
  sources: Array<{ label: string; url: string }>;
  warnings: string[];
  revisionNote?: string;
};

export type ResearchBundle = {
  weather?: {
    summary: string;
    temperatureRange: string;
    packing: string[];
    sourceLabel: string;
  };
  airports: string[];
  airlines: string[];
  hotelResearch: Array<{ title: string; url: string; snippet: string }>;
  warnings: string[];
  sources: Array<{ label: string; url: string }>;
};
