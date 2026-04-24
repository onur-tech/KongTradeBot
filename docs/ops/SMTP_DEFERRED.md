# SMTP Alerts — DEFERRED bis Phase 10

## Aktueller Status
Bot nutzt Telegram als primären Alert-Kanal. SMTP-Config fehlt bewusst.

## Warum deferred
- Telegram funktioniert zuverlässig (Token + Chat-ID konfiguriert)
- E-Mail wäre Redundanz, aber nicht kritisch für Paper-Phase
- Setup erfordert SMTP-Server-Credentials (MailGun/Sendgrid/eigener Server)
- Health-Monitor sendet Alerts via Telegram wenn SMTP fehlt

## Implementation wenn gewünscht
1. SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TO in .env
2. `core/alerts.py` um `send_email()` erweitern
3. Alert-Policy: Critical → Telegram + E-Mail, Warning → nur Telegram
