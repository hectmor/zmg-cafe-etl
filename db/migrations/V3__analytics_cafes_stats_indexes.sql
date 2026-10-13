-- Supports the GROUP BY aggregates used by AnalyticsStore.stats() (api/db.py):
-- grouping analytics.cafes by object_type and by geometry_method.
-- Verified with EXPLAIN ANALYZE against ~40k synthetic benchmark rows (M8.2,
-- issue #41): without these indexes both GROUP BY queries run a Seq Scan +
-- HashAggregate; with them, the planner switches to an Index Only Scan +
-- GroupAggregate, cutting execution time roughly in half at that volume.
CREATE INDEX analytics_cafes_object_type_idx
    ON analytics.cafes (object_type);

CREATE INDEX analytics_cafes_geometry_method_idx
    ON analytics.cafes (geometry_method);
