# Changelog: 2026 Q3

## 2026-09-22 - Delivery diagnostics

Webhook delivery logs now expose the event ID, delivery attempt, response class, and a request correlation value. Signing secrets and raw payload bodies remain redacted. The change does not alter the six-attempt delivery policy or five-minute signature timestamp tolerance.

## 2026-09-10 - Export manifest checksums

Exports larger than 5 GB are split into numbered parts. The manifest now lists a checksum per part. Consumers should download every part and verify checksums before reassembly. Failed export retries create a new export job ID.

## 2026-08-28 - Queue age dashboard

The operations dashboard adds oldest dispatch-message age and DLQ-17 counts. The documented investigation thresholds remain 180 seconds for five minutes and more than 25 DLQ-17 events in ten minutes.

## 2026-08-06 - Sandbox fault profiles

Local development adds `flaky-3` and `dead-letter-9` profiles. They help test retry logic and dead-letter alerting; they are not configured in the hosted service.

## Policy precedence

Operational limits and current behavior are defined in the API Operations Handbook, Security and Access Policy, Reliability SLO and Alerts policy, and Data Retention and Exports standard. This changelog records changes; do not treat an old release entry as the latest policy source.
