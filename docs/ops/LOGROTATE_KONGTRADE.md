# Log-Rotation — KongTrade

## Status
Installiert unter `/etc/logrotate.d/kongtrade` (2026-04-24).

## Konfiguration
```
/home/claudeuser/KongTradeBot/bot.log
/home/claudeuser/KongTradeBot/dashboard.log
{
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0664 claudeuser claudeuser
    copytruncate
}
```

## Manuelle Ausführung
```bash
sudo logrotate -f /etc/logrotate.d/kongtrade
```

## service-bot.log (systemd journal)
`logs/service-bot.log` (44MB) wird via systemd-append nicht automatisch rotiert.
Manuell rotieren:
```bash
sudo truncate -s 0 /home/claudeuser/KongTradeBot/logs/service-bot.log
sudo truncate -s 0 /home/claudeuser/KongTradeBot/logs/service-dashboard.log
```
