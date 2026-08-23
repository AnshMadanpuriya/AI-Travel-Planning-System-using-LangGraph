import { sql } from "drizzle-orm";
import { check, index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const travelPlans = sqliteTable(
  "travel_plans",
  {
    id: text("id").primaryKey(),
    ownerKey: text("owner_key").notNull(),
    origin: text("origin").notNull(),
    destination: text("destination").notNull(),
    startDate: text("start_date").notNull(),
    endDate: text("end_date").notNull(),
    travelers: integer("travelers").notNull(),
    budget: integer("budget").notNull(),
    currency: text("currency").notNull(),
    mode: text("mode").notNull(),
    revisionCount: integer("revision_count").notNull().default(0),
    planJson: text("plan_json").notNull(),
    approvedAt: text("approved_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    index("travel_plans_owner_updated_idx").on(table.ownerKey, table.updatedAt),
    index("travel_plans_owner_destination_idx").on(table.ownerKey, table.destination),
    check("travel_plans_travelers_check", sql`${table.travelers} BETWEEN 1 AND 20`),
    check("travel_plans_budget_check", sql`${table.budget} BETWEEN 100 AND 1000000000`),
    check("travel_plans_currency_check", sql`${table.currency} IN ('INR', 'USD', 'EUR', 'GBP')`),
    check("travel_plans_mode_check", sql`${table.mode} IN ('live', 'preview')`),
    check("travel_plans_revision_count_check", sql`${table.revisionCount} >= 0`),
  ],
);
