"""
app/integrations/resend_client.py
──────────────────────────────────
Email delivery via Resend. All templates are inline HTML here.
In v2 move templates to a dedicated templates/ folder with Jinja2.
"""
from __future__ import annotations

import resend

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

resend.api_key = settings.RESEND_API_KEY


async def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    reply_to: str | None = None,
) -> bool:
    """
    Send a transactional email via Resend.
    Returns True on success, False on failure (non-fatal).
    Logs errors but never raises — email failure shouldn't crash the app.
    """
    recipients = [to] if isinstance(to, str) else to
    try:
        params: resend.Emails.SendParams = {
            "from":    f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>",
            "to":      recipients,
            "subject": subject,
            "html":    html,
        }
        if reply_to:
            params["reply_to"] = reply_to

        resend.Emails.send(params)
        logger.info("email.sent", to=recipients[0], subject=subject)
        return True
    except Exception as exc:
        logger.error("email.send_failed", to=recipients[0], subject=subject, error=str(exc))
        return False


# ── Email templates ────────────────────────────────────────────────────────────

def _base_template(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background: #0A0A0A; color: #F0F0F0; margin: 0; padding: 40px 20px; }}
    .container {{ max-width: 520px; margin: 0 auto; background: #161616;
                  border: 1px solid #252525; padding: 40px; }}
    .logo {{ font-size: 28px; font-weight: 900; color: #DFFF00;
             letter-spacing: -1px; margin-bottom: 32px; }}
    h1 {{ font-size: 22px; font-weight: 700; color: #FFFFFF;
          margin: 0 0 16px; }}
    p  {{ color: #888; font-size: 14px; line-height: 1.6; margin: 0 0 16px; }}
    .btn {{ display: inline-block; background: #DFFF00; color: #000;
            font-weight: 700; font-size: 13px; letter-spacing: 2px;
            text-transform: uppercase; padding: 14px 28px;
            text-decoration: none; margin: 16px 0; }}
    .code {{ background: #111; border: 1px solid #333; padding: 16px 24px;
             font-family: monospace; font-size: 18px; font-weight: 700;
             color: #DFFF00; letter-spacing: 4px; text-align: center;
             margin: 20px 0; }}
    .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #252525;
               color: #444; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">DRIP<span style="color:#555">.</span></div>
    {body}
    <div class="footer">
      <p>© 2026 DRIP Marketplace. Pakistan's online fashion mall.</p>
      <p>If you did not request this email, you can safely ignore it.</p>
    </div>
  </div>
</body>
</html>"""


async def send_verification_email(email: str, first_name: str, token: str) -> bool:
    verify_url = f"{settings.ALLOWED_ORIGINS[0]}/verify-email?token={token}"
    body = f"""
    <h1>Verify your email</h1>
    <p>Hi {first_name}, welcome to DRIP! Click the button below to verify your email address.</p>
    <a href="{verify_url}" class="btn">Verify Email</a>
    <p>This link expires in <strong>24 hours</strong>.</p>
    <p>Or copy this URL into your browser:<br>
    <small style="color:#555;word-break:break-all">{verify_url}</small></p>
    """
    return await send_email(
        to=email,
        subject="Verify your DRIP account",
        html=_base_template("Verify your email — DRIP", body),
    )


async def send_password_reset_email(email: str, first_name: str, token: str) -> bool:
    reset_url = f"{settings.ALLOWED_ORIGINS[0]}/reset-password?token={token}"
    body = f"""
    <h1>Reset your password</h1>
    <p>Hi {first_name}, we received a request to reset your DRIP password.</p>
    <a href="{reset_url}" class="btn">Reset Password</a>
    <p>This link expires in <strong>1 hour</strong>. If you didn't request this, ignore this email — your password won't change.</p>
    """
    return await send_email(
        to=email,
        subject="Reset your DRIP password",
        html=_base_template("Password reset — DRIP", body),
    )


async def send_order_confirmation_email(
    email: str,
    name: str,
    order_number: str,
    total: int,
    items: list[dict],
) -> bool:
    items_html = "".join(
        f"<p style='margin:4px 0;color:#aaa;font-size:13px;'>"
        f"{i['product_name']} × {i['quantity']} — PKR {i['subtotal']:,}</p>"
        for i in items
    )
    body = f"""
    <h1>Order confirmed!</h1>
    <p>Hi {name}, your order has been placed successfully.</p>
    <div class="code">{order_number}</div>
    <p style="color:#555;font-size:13px;">Save this order number for tracking.</p>
    {items_html}
    <p style="margin-top:16px;"><strong style="color:#fff;">Total: PKR {total:,}</strong></p>
    <p>You'll receive a shipping notification when your order is on its way.</p>
    """
    return await send_email(
        to=email,
        subject=f"Order confirmed — {order_number}",
        html=_base_template(f"Order {order_number} confirmed — DRIP", body),
    )


async def send_shipping_notification_email(
    email: str,
    name: str,
    order_number: str,
    tracking_number: str,
    courier_name: str,
    brand_name: str,
) -> bool:
    body = f"""
    <h1>Your order is on its way!</h1>
    <p>Hi {name}, <strong style="color:#DFFF00">{brand_name}</strong> has shipped your order.</p>
    <p><strong style="color:#fff;">Order:</strong> {order_number}</p>
    <p><strong style="color:#fff;">Courier:</strong> {courier_name}</p>
    <p><strong style="color:#fff;">Tracking:</strong> {tracking_number}</p>
    <p>Delivery typically takes 3–5 business days within Pakistan.</p>
    """
    return await send_email(
        to=email,
        subject=f"Your DRIP order is shipped — {order_number}",
        html=_base_template("Order shipped — DRIP", body),
    )


async def send_cod_timeout_email(email: str, name: str, order_number: str) -> bool:
    body = f"""
    <h1>Order cancelled</h1>
    <p>Hi {name}, your Cash on Delivery order <strong style="color:#fff">{order_number}</strong>
    was automatically cancelled because it wasn't verified within 30 minutes.</p>
    <p>If this was a mistake, please place your order again at
    <a href="{settings.ALLOWED_ORIGINS[0]}" style="color:#DFFF00">drip.pk</a></p>
    """
    return await send_email(
        to=email,
        subject=f"Order cancelled — {order_number}",
        html=_base_template("Order cancelled — DRIP", body),
    )


async def send_seller_approved_email(email: str, brand_name: str, dashboard_url: str) -> bool:
    body = f"""
    <h1>Your brand is live!</h1>
    <p>Congratulations! <strong style="color:#DFFF00">{brand_name}</strong> has been approved on DRIP.</p>
    <p>You now have 50 product slots ready to fill. Log in to your dashboard to start listing.</p>
    <a href="{dashboard_url}" class="btn">Go to Dashboard</a>
    <p>If you have any questions, WhatsApp us at <strong style="color:#25D366">+92 300 0000000</strong></p>
    """
    return await send_email(
        to=email,
        subject="Your brand is approved on DRIP!",
        html=_base_template(f"{brand_name} is live — DRIP", body),
    )