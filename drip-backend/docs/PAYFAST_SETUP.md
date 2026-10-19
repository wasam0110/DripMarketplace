# PayFast setup and verification

The backend implements PayFast Pakistan's hosted checkout: server-side access-token
creation, an uppercase checkout form, SHA-256 callback validation, replay protection,
exact local order/currency checks, retry initiation, and admin reconciliation through
`POST /api/v1/payments/{order_id}/reconcile`.

## Credentials and URLs

Keep `PAYFAST_ENABLED=false` while configuring:

```env
PAYFAST_MERCHANT_ID=
PAYFAST_SECURED_KEY=
PAYFAST_MERCHANT_NAME=WearHowZ
PAYFAST_SANDBOX=true
PAYFAST_API_BASE_URL=
PAYFAST_IPN_IPS=
PAYFAST_TRUSTED_PROXY_IPS=
```

The UAT and live hosted token/checkout URLs are built in. Only set
`PAYFAST_TOKEN_URL` or `PAYFAST_CHECKOUT_URL` if PayFast gives this merchant different
URLs. `PAYFAST_API_BASE_URL` is the merchant-specific REST base supplied by PayFast;
it is required both for successful callback verification and missed-callback
reconciliation. Enabling PayFast without it fails configuration validation. Do not
guess it from the hosted URL.

Register this public callback with PayFast:

`https://YOUR_API_HOST/api/v1/payments/callback/payfast`

If a reverse proxy supplies `X-Forwarded-For`, add only its direct IP/CIDR to
`PAYFAST_TRUSTED_PROXY_IPS`. Add PayFast's confirmed callback IP/CIDR values to
`PAYFAST_IPN_IPS`; an empty list disables source-IP filtering, not hash verification
or the authoritative success lookup.

The application now resolves trusted chains from the socket peer right-to-left.
Run Uvicorn with `--no-proxy-headers`. When the PayFast-specific proxy list is empty,
it uses `TRUSTED_PROXY_IPS` (default `[]`); never trust arbitrary internet networks.
**Checkpoint 2:** the hash does not bind the amount or transaction reference, so a
success callback cannot authorize payment on its own. The authenticated status lookup
must return matching `basket_id`, `transaction_id`, explicit `amount`/`txnamt` and
`currency`/`currency_code`. Missing, invalid or conflicting monetary aliases are
rejected without crediting payment. These supported field mappings are locally
tested, not merchant-certified: obtain the merchant's actual response contract and
verify it in UAT. Keep PayFast disabled until that acceptance passes.

## UAT checklist

1. Add sandbox merchant credentials and the provider-supplied API base URL.
2. Keep `PAYFAST_SANDBOX=true`, then set `PAYFAST_ENABLED=true` in UAT only.
3. Initiate a small test order and submit the returned form to `checkout_url`.
4. Prove success, decline/cancel, duplicate callback, delayed callback, customer retry,
   wrong basket, wrong/missing amount or currency, mismatched transaction and status
   API outage. Never accept missing provider monetary evidence using local defaults.
5. Temporarily block a callback and use the admin reconciliation endpoint. Confirm an
   unknown or mismatched response does not change payment/order state.
6. Confirm callback source ranges and the REST success codes with PayFast support.
7. Save PayFast transaction IDs and reconcile them against the merchant dashboard.

For production, use HTTPS for both `FRONTEND_URL` and `API_BASE_URL`, set
`PAYFAST_SANDBOX=false`, rotate out sandbox credentials, repeat a controlled acceptance
test, and only then enable the gateway. Never put the secured key in browser code or
commit it to Git.

These app settings are root origins (no credentials, subpaths, query or fragment);
one trailing slash is normalized. Hosted form URLs retain the existing routes:
`FRONTEND_URL/order/success/{order_id}`, `FRONTEND_URL/checkout?payment=failed`, and
`API_BASE_URL/api/v1/payments/callback/payfast`. Keep `API_PREFIX=/api/v1`.
`ALLOWED_ORIGINS` is not used to build these links. This does not modify or verify
PayFast's merchant-specific `PAYFAST_API_BASE_URL` or hosted endpoint overrides.

Local mocked tests prove protocol construction and state safety; they do not certify a
merchant account or make a real charge.
