# Northstar Relay Platform Architecture

## System overview

Northstar Relay is a fictional service for accepting asynchronous jobs and reporting lifecycle events. The REST API validates a request, applies workspace limits, persists a job record, and publishes work to the `dispatch` queue. Workers process jobs and write terminal metadata to `archive`. The `notify` queue feeds the webhook delivery service.

## Main components

- **API service:** authentication, request validation, idempotency, rate limiting, and job creation.
- **Dispatch workers:** execute jobs and report attempt outcomes.
- **Archive store:** keeps job status and result metadata for retrieval.
- **Notification service:** signs lifecycle event deliveries and retries failed webhooks.
- **Operations control plane:** dashboards, audit events, dead-letter inspection, and operator-only redrive tools.

## Request path

1. Client sends `POST /v2/jobs` with `X-Northstar-Key` and an `Idempotency-Key`.
2. The API validates identity and workspace permissions.
3. The rate limiter enforces 120 requests per minute per workspace, with a burst allowance of 20.
4. The API persists or reuses the idempotent result and publishes accepted work to `dispatch`.
5. A worker processes the job and writes status metadata to `archive`.
6. The notification service emits a signed event through `notify`.

## Failure boundaries

An API timeout does not prove that a job was not accepted. Clients should retry with the same idempotency key and same request body. A worker failure is separate from API acceptance: after more than eight processing attempts, the job is moved to the DLQ and labeled `DLQ-17`. See `retry-and-idempotency.md` and the HTML Job Queue Runbook before implementing retries or redrives.

## Source of truth

The API Operations Handbook and the Reliability SLO and Alerts policy define the current limits and alert thresholds. A release note can describe when a feature was introduced, but it does not override those operational policies.
