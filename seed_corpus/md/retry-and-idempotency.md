# Retry and Idempotency Rules

## Idempotency key contract

For `POST /v2/jobs`, send an `Idempotency-Key` that is unique to the intended operation and scoped to the workspace. The server retains keys for **24 hours**. Replaying the same key with the same normalized body returns the original response; using the same key with a different body returns **HTTP 409 Conflict**.

A timed-out HTTP response is ambiguous: the service may have accepted the job before the connection failed. Retry with the original key and unchanged body instead of creating a new key immediately.

## Retryable HTTP responses

Usually retry with backoff: `429`, `500`, `502`, `503`, and `504`. For `429`, honor `Retry-After` before sending another request. A common schedule is 1, 2, 4, and 8 seconds, with random jitter added to avoid synchronized clients. Cap attempts and surface persistent failures to an operator.

Do not blindly retry `400`, `401`, `403`, or `409`. Correct a malformed payload, repair credentials, request appropriate permissions, or resolve the idempotency-body mismatch first. A retry loop cannot fix a deterministic client error.

## Webhook consumers

Webhook delivery is at-least-once. Use the event ID, not the attempt number, as the consumer deduplication key. Verify `X-Northstar-Signature` over the exact raw body using HMAC-SHA256 and reject timestamps outside the five-minute tolerance.

## Operator redrive

A `DLQ-17` job exceeded eight processing attempts. Inspect the attempt history and the downstream side effect before redriving. Use `relay-admin jobs redrive --job-id JOB_ID --preserve-idempotency`; the preserve flag is required for jobs with external side effects. Redrive does not repair the root cause by itself.
