CREATE TABLE `travel_plans` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_key` text NOT NULL,
	`origin` text NOT NULL,
	`destination` text NOT NULL,
	`start_date` text NOT NULL,
	`end_date` text NOT NULL,
	`travelers` integer NOT NULL,
	`budget` integer NOT NULL,
	`currency` text NOT NULL,
	`mode` text NOT NULL,
	`revision_count` integer DEFAULT 0 NOT NULL,
	`plan_json` text NOT NULL,
	`approved_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT "travel_plans_travelers_check" CHECK("travel_plans"."travelers" BETWEEN 1 AND 20),
	CONSTRAINT "travel_plans_budget_check" CHECK("travel_plans"."budget" BETWEEN 100 AND 1000000000),
	CONSTRAINT "travel_plans_currency_check" CHECK("travel_plans"."currency" IN ('INR', 'USD', 'EUR', 'GBP')),
	CONSTRAINT "travel_plans_mode_check" CHECK("travel_plans"."mode" IN ('live', 'preview')),
	CONSTRAINT "travel_plans_revision_count_check" CHECK("travel_plans"."revision_count" >= 0)
);
--> statement-breakpoint
CREATE INDEX `travel_plans_owner_updated_idx` ON `travel_plans` (`owner_key`,`updated_at`);--> statement-breakpoint
CREATE INDEX `travel_plans_owner_destination_idx` ON `travel_plans` (`owner_key`,`destination`);