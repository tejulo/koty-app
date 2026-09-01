/**
 * DEV-32 — Limits and constants enforced by the outbox layer.
 *
 * `OUTBOX_MAX_PAYLOAD_BYTES` is the maximum serialized size (UTF-8 bytes
 * of the canonical JSON) of the `payload` field. The service rejects any
 * payload larger than this with `OutboxPayloadTooLargeException`
 * (HTTP 400 / `OUTBOX_PAYLOAD_TOO_LARGE`) **before** touching the
 * database, so a misbehaving caller cannot fill the table.
 *
 * `MIN_SEMANTIC_KEY_LENGTH` and `MAX_SEMANTIC_KEY_LENGTH` bound the
 * `semanticKey` so the unique index stays usable and so the caller cannot
 * stuff arbitrary long strings into the table.
 */
export const OUTBOX_MAX_PAYLOAD_BYTES = 64 * 1024; // 64 KB
export const MIN_SEMANTIC_KEY_LENGTH = 1;
export const MAX_SEMANTIC_KEY_LENGTH = 200;
export const MIN_ORGANIZATION_ID_LENGTH = 1;
export const MAX_PAYLOAD_DEPTH = 32;

export const DEFAULT_AGGREGATE_TYPE = 'outbox-echo';
export const DEFAULT_EVENT_TYPE = 'outbox-echo.create';
