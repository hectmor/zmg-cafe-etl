ALTER TABLE staging.cafe_records DROP CONSTRAINT staging_run_source_identity;

CREATE UNIQUE INDEX staging_run_accepted_identity
    ON staging.cafe_records (run_id, source_id)
    WHERE validation_status IN ('accepted', 'accepted_with_warning');
