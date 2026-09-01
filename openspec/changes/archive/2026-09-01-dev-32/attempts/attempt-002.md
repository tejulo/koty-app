# Attempt 2

## Status

retryable_failure

## Failure

- Type: infrastructure
- Stage: runtime

## Summary

Failed to convert text into a Pydantic model due to error: Error code: 400 - {'error': {'type': 'server_error', 'message': 'Error from provider (Console Go): Upstream request failed: [bad_request_error] invalid params, Mismatch type bool with value object "at index 10201: mismatched type with value\\n\\n\\tonalProperties\\":{\\"type\\":\\"string\\"\\n\\t................^...............\\n" (2013)'}}

## Verification

~~~json
{
  "python": "skipped",
  "lint": "skipped",
  "test": "skipped",
  "build": "skipped",
  "playwright": "skipped",
  "openspec": "skipped"
}
~~~
