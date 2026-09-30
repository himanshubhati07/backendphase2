-- Upgrade installations created before the membership lifecycle contract was corrected.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'memberships'
          AND column_name = 'membership_plan_id'
    ) THEN
        ALTER TABLE memberships RENAME COLUMN membership_plan_id TO plan_id;
    END IF;

    ALTER TABLE memberships DROP COLUMN IF EXISTS cancellation_reason;
END $$;
