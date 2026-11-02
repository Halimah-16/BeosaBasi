# Cloudflare setup notes (TK-003 fills in real values)

- `app.<domain>` -> Pages project rooted at `apps/web`.
- `api.<domain>` -> proxied to VPS Caddy.
- R2 bucket: private; browser uses presigned URLs against the S3 endpoint.
- Replace `<domain>` everywhere before use. Store API tokens and Turnstile
  secrets in the VPS environment / Cloudflare dashboard only — never in git.
