# Observability and Useful Signals

## API signals

The API availability objective is 99.9% per rolling 30-day window. For successful `POST /v2/jobs` requests, the latency objective is p95 below 250 ms; this measures request acceptance, not completion of the asynchronous job.

Page the API on-call when p95 is above 500 ms for five consecutive minutes and traffic is above the minimum floor. During a deployment, p95 above 2x the pre-deployment baseline is a rollback signal. A 5-minute error-rate increase greater than 1.0 percentage point over baseline is also a rollback signal.

## Queue signals

Monitor dispatch queue depth, oldest-message age, worker saturation, and dead-letter volume. Investigate if the oldest dispatch message is above 180 seconds for five minutes or `DLQ-17` exceeds 25 occurrences in ten minutes. If API latency is normal but queue age rises, inspect worker capacity and downstream dependencies.

## Incident evidence

A useful incident bundle contains: UTC time range, request IDs, route, response codes, workspace (or a safely anonymized workspace reference), p95 latency, 5xx rate, oldest queue age, worker saturation, and database connection wait. Never attach credentials or unredacted request payloads.

## Related incident

During `INC-204` on 2026-06-12, the database connection pool max was 10. A schema migration created additional work, request waits pushed p95 beyond 500 ms, and 504s followed. Raising the pool max to 40 restored p95 below 250 ms. The follow-up added concurrent migration-plus-API load testing.
