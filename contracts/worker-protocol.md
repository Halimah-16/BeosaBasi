# Worker Protocol (placeholder — full contract in TK-001)

Per PRD 4.7, the laptop worker talks to the VPS over HTTPS (outbound only)
with `Authorization: Bearer <worker token>`:

| Method & path | Purpose (detail + JSON schemas in TK-001) |
|---|---|
| `POST /worker/v1/jobs/claim?wait=25` | Claim next `queued` job (long-poll ≤ 25s, 5-min lease) |
| `POST /worker/v1/jobs/{id}/heartbeat` | Every 30s; renew lease, report stage; honors `cancel: true` |
| `POST /worker/v1/jobs/{id}/result` | Segments, speakers, duration, xRT, model version, low-confidence ratio |
| `POST /worker/v1/jobs/{id}/fail` | Error code + retryable flag |
| `POST /worker/v1/ping` | Registration and version check |

Job states and processing stages: see PRD 4.5
(`uploading → queued → processing[probing, transcribing, diarizing, merging]
→ completed`, plus `failed / expired / cancelled / deleted`).

TODO(TK-001): JSON schemas for claim response, heartbeat body, result body
(segments: start/end/text/confidence/speaker; speakers; metadata), error
codes with Indonesian user-facing messages.
