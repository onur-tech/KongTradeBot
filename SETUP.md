# KongTradeBot – Setup

## Claude Code auf Server

| Einstellung | Wert |
|---|---|
| User | `claudeuser` (nicht root) |
| Login | `ssh claudeuser@89.167.29.183` |
| Start | `cd /root/KongTradeBot && claude` |
| Alias | `claude` läuft mit `--dangerously-skip-permissions` |
| Token | 1 Jahr gültig (Anthropic setup-token) |
| `.claude.json` | Onboarding-Bypass (kein interaktiver Erststart) |
| Git safe.directory | `/root/KongTradeBot` global gesetzt |

> **Hinweis:** Der Bot-Code liegt unter `/root/KongTradeBot` und gehört `root`.
> `claudeuser` greift via `git config --global --add safe.directory /root/KongTradeBot` darauf zu.
