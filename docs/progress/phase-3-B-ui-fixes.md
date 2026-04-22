# Phase 3 — Block B UI-Fixes

**Zeitpunkt:** 2026-04-22 ~17:40 UTC  
**Branch:** phase-3-plugin-refactor

## B.1 Admin-Passwort (onur)
- Status: **Kein Handlungsbedarf**
- SHA-256 Hash von `kong-admin-2026` = `840b114b...` stimmt exakt mit bestehendem `password_hash` in `data/users.json` überein.
- Dashboard nutzt SHA-256, nicht bcrypt.
- Kein Commit (keine Änderung).

## B.2 Password-Toggle-Button
- Status: **Bereits implementiert**
- `dashboard.py` enthält vollständige Implementierung: `.pw-wrap`, `.pw-toggle`, `togglePw()` mit `#00ff88`-Highlight.
- Sowohl auf Login-Page als auch im Add-User-Form vorhanden.
- Kein Commit (keine Änderung nötig).

## B.3 Schrift +2px global
- **Datei:** `dashboard.html`
- **Änderungen:**
  - `:root` Default: `--fs-base:15px → 17px`, `--fs-small:13px → 15px`, `--fs-large:17px → 19px`
  - Mobile (`< 768px`): `--fs-base:14px → 16px`
  - Ultrawide (`≥ 2560px`): `--fs-base:17px → 19px`, `--fs-large:19px → 21px`
- Commit: `a936147`

## B.4 Mobile-Responsive-Verbesserungen
- **Datei:** `dashboard.html`
- Bestehende 767px-Query hatte bereits: Sidebar-Toggle, `overflow-x:auto` auf Tabellen, `.obs-grid:1col`
- **Neu hinzugefügt:** `@media (max-width:499px)` Breakpoint:
  - `.rgrid{grid-template-columns:1fr}` (von 2 auf 1 Spalte)
  - `.obs-card{min-width:0;word-break:break-word}`
  - Reduziertes Padding (#hdr, #main)
  - Kleinere Font-Sizes für Platform- und Strategy-Tabs
- Commit: `c4c091b`

## B.5 Sidebar-Layout-Fix (Portfolio-Rows)
- **Datei:** `dashboard.html`
- **Problem:** `.albl`/`.rlbl` (Grid 1fr auto auto) — erste Spalte hatte kein `min-width:0`, Label konnte Grid-Layout bei schmalen Sidebars (200–230px) sprengen.
- **Fix:**
  - `.albl>span:first-child` + `.rlbl>span:first-child`: `min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`
  - `.albl` gap: `10px → 6px` (mehr Platz für Werte)
  - `white-space:nowrap` auf `.row-amt`, `.row-cap`, `.row-slash` (Werte nie umbrechen)
- Commit: `b38c747`
