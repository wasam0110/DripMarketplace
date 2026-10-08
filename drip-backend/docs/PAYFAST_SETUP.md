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
it enables missed-callback reconciliation. Do not guess it from the hosted URL.

Register this public callback with PayFast:

`https://YOUR_API_HOST/api/v1/payments/callback/payfast`

If a reverse proxy supplies `X-Forwarded-For`, add only its direct IP/CIDR to
`PAYFAST_TRUSTED_PROXY_IPS`. Add PayFast's confirmed callback IP/CIDR values to
`PAYFAST_IPN_IPS`; an empty list relies on the cryptographic callback hash only.

## UAT checklist

1. Add sandbox merchant credentials and the provider-supplied API base URL.
2. Keep `PAYFAST_SANDBOX=true`, then set `PAYFAST_ENABLED=true` in UAT only.
3. Initiate a small test order and submit the returned form to `checkout_url`.
4. Prove success, decline/cancel, duplicate callback, delayed callback, customer retry,
   wrong basket, and wrong amount (when PayFast includes an amount).
5. Temporarily block a callback and use the admin reconciliation endpoint. Confirm an
   unknown or mismatched response does not change payment/order state.
6. Confirm callback source ranges and the REST success codes with PayFast support.
7. Save PayFast transaction IDs and reconcile them against the merchant dashboard.

For production, use HTTPS for both `FRONTEND_URL` and `API_BASE_URL`, set
`PAYFAST_SANDBOX=false`, rotate out sandbox credentials, repeat a controlled acceptance
test, and only then enable the gateway. Never put the secured key in browser code or
commit it to Git.

Local mocked tests prove protocol construction and state safety; they do not certify a
merchant account or make a real charge.
