# Cloudflare Email Sending

Cloudflare support is opt-in. Set these environment variables on the actual runtime:

- `CLOUDFLARE_ACCOUNT_ID`: account containing the sending domain and destinations.
- `CLOUDFLARE_EMAIL_API_TOKEN`: dedicated token with Email Sending Edit permission. Store as a secret.
- `CLOUDFLARE_EMAIL_FROM`: sender address under an onboarded sending domain.
- `CLOUDFLARE_EMAIL_RECIPIENTS`: comma-separated, individually verified destination addresses.

Non-debug sends use Cloudflare only when every recipient is in the configured verified list and all credentials exist. Otherwise the existing provider is preserved. This avoids breaking mail to other users on Workers Free. Mixed recipient batches stay on the original provider. Addresses are never redirected. Cloudflare failures are not retried through another provider in the same attempt, to avoid duplicate delivery.

A response is successful only when Cloudflare reports success and every recipient is delivered or queued, with no permanent bounces. Admin Studio leaves failures pending for its existing retry workflow.

Do not remove existing provider credentials. Roll back by removing the Cloudflare token from the runtime. Do not enable Workers Paid without approval. Tests must mock all network sends.

Official setup: https://developers.cloudflare.com/email-service/get-started/send-emails/
