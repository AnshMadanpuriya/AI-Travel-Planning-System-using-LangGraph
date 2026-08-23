import type { Metadata } from "next";
import "./globals.css";

const siteUrl = "https://ai-travel-agent-ansh.anshmadanpuriya16.chatgpt.site";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "AI Travel Agent System | AtlasAI",
  description: "A review-first multi-agent travel planner for flights, stays, weather, budgets, and day-by-day itineraries.",
  openGraph: {
    title: "AI Travel Agent System",
    description: "Plan smarter. Review every detail.",
    type: "website",
    url: siteUrl,
    images: [{ url: `${siteUrl}/og.png`, width: 1200, height: 630, alt: "AI Travel Agent System" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Travel Agent System",
    description: "Plan smarter. Review every detail.",
    images: [`${siteUrl}/og.png`],
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
