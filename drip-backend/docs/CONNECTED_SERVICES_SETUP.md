# Connected services setup and verification

## Google sign-in

Create a Google OAuth web client and configure both `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET`. Register this exact authorized redirect URI:

`https://YOUR_API_HOST/api/v1/auth/google/callback`

Set `API_BASE_URL` to the public backend origin and `FRONTEND_URL` to the public site.
The backend uses state, nonce, PKCE, a one-use Redis record, signed-ID-token validation,
and an HttpOnly refresh cookie. Complete one real new-account login, one returning login,
one cancelled login, and one replay attempt before launch.

## Supabase Storage

Create the configured `products`, `avatars`, and `brands` buckets (or change their
environment names), then add `SUPABASE_URL` and the server-only service-role key. Run:

```powershell
.venv/Scripts/python.exe scripts/verify_connected_services.py --storage-write
```

The opt-in check uploads, lists, and deletes a unique marker in each image bucket.
Orphan cleanup is disabled by default. After the smoke check and a database backup,
set `SUPABASE_ORPHAN_CLEANUP_ENABLED=true`. Cleanup skips recent, referenced,
malformed, or timestamp-less objects and does not scan the invoice bucket.

## Resend

Verify the sending domain in Resend, then set `RESEND_API_KEY`, `FROM_EMAIL`, and
`FROM_NAME`. `FROM_EMAIL` cannot remain on `example.com` in production. Send one real
test message to an address you control:

```powershell
.venv/Scripts/python.exe scripts/verify_connected_services.py --email-to you@example.net
```

The synchronous SDK call runs off the event loop. Email tasks retry failed provider
calls, and notification tasks retry database failures instead of silently succeeding.

## Worker

Run Redis and start the worker with:

```powershell
.venv/Scripts/python.exe -m arq app.tasks.worker.WorkerSettings
```

Check startup logs, enqueue a verification email, and observe success plus the nightly
cleanup schedule. Broadcast jobs use deterministic notification IDs, so retrying the
same task does not duplicate recipients.

The verification script never prints secrets and performs no external write unless an
explicit write/email flag is supplied. Real account checks still require credentials
and must be run in a controlled staging environment.
