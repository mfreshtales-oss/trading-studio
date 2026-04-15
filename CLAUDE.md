# Manny's Trading & Voice Studio — CLAUDE.md

## Project overview

Single-file web app (`index.html`, ~1400 lines) combining:
- **Live market data** via FMP (Financial Modeling Prep) REST API — DXY, Gold, VIX, US10Y, plus a custom watchlist
- **Voice intelligence** via ElevenLabs TTS, S2S (speech-to-speech), and a real-time WebSocket conversation agent
- **Trading discipline tools** — daily performance stats, discipline score/grade, session rules, market bias notes
- **Ticker bar** with animated FMP-fed price stream

No build step. No framework. No dependencies. Deploy = copy `index.html`.

## Stack

| Layer | Tech |
|-------|------|
| Language | Vanilla JS (ES2022) + HTML5 + CSS custom properties |
| Market data | FMP stable API (`/stable/quotes`, `/stable/treasury-rates`) |
| Voice | ElevenLabs v1 REST API + WebSocket conversation agent |
| Deployment | Static HTML — can host anywhere |

## Key files

| File | Purpose |
|------|---------|
| `index.html` | The entire application |

## Architecture

Everything lives in `index.html`. Sections:
- **Lines 1–580**: CSS (design tokens, layout, ticker, cards, chat, voice panels)
- **Lines 580–610**: HTML structure (ticker, header, left trading panel, right voice/studio panel)
- **Lines 585–590**: Hardcoded API keys (ElevenLabs, FMP, Agent ID) — see security note
- **Lines 611–1379**: JavaScript — clock, ticker, FMP polling, ElevenLabs TTS/S2S/conversation, market context builder

Key JS functions:
- `connectFMP()` / `fetchFMPData()` — FMP auth + 60-second polling loop
- `buildLiveContext(now)` — assembles live market context string sent to voice agent
- `toggleConversation()` / `startConversation()` — ElevenLabs WebSocket agent
- `generateTTS()` — single-shot TTS to audio playback
- `runS2S()` — audio blob → speech-to-speech conversion
- `updateMarketData()` / `buildTickerFromFMP()` / `buildWatchlistPanel()` — FMP data → DOM

## MCP tools available

This project has the following MCP servers connected:

### Trading intelligence (mcp__eae4afe6)
- `get_market_context`, `get_market_sentiment` — live market reads
- `log_trade`, `get_full_trade_journal`, `get_trade_journal_summary` — trade journal
- `run_pre_trade_checklist`, `get_pre_trade_validation_log` — pre-trade gates
- `get_discipline_snapshot`, `get_discipline_trend`, `record_weekly_discipline` — discipline tracking
- `get_session_brief`, `generate_fresh_session_brief` — session prep
- `get_latest_tradingview_alert`, `list_recent_tradingview_alerts` — TradingView webhooks
- `analyze_chart_with_ai`, `analyze_trade_with_ai`, `grade_trade_setup` — AI analysis
- `calculate_position_size` — position sizing
- `get_weekly_performance_report`, `generate_fresh_weekly_report` — weekly review
- `sync_daily_performance_to_notion`, `sync_discipline_to_notion`, `sync_weekly_report_to_notion` — Notion sync
- `smart_route`, `router_dry_run` — AI model routing
- `speak_summary` — voice output
- `search_trade_memory` — memory search

### Notion (mcp__fbc229cb)
- `notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page` — Notion CRUD

### Gmail (mcp__105c7214)
- `gmail_search_messages`, `gmail_read_message` — email access

### Google Calendar (mcp__dcc6fb75)
- `gcal_list_events`, `gcal_create_event` — calendar

### Slack (mcp__12efe043)
- `slack_send_message`, `slack_search_public` — Slack

### Google Drive (mcp__38e85a38)
- `read_file_content`, `search_files` — Drive files

### Hugging Face (mcp__8d8b45ae)
- `hf_hub_query`, `paper_search` — AI model research

### Library docs (mcp__874f5a94 — Context7)
- `resolve-library-id`, `query-docs` — up-to-date library documentation
- **Use this for any library/API/SDK docs lookup** (ElevenLabs, FMP, Playwright, etc.)

## Development notes

- **No test suite** yet — use `/qa` (gstack) to test in real browser
- **No build pipeline** — edit `index.html` directly
- **Deploy** by committing `index.html` to `main`; CI/CD is manual push

## Security note

API keys are currently hardcoded in `index.html` (lines 585–588):
- `ElevenLabs API key` (sk_...)
- `FMP API key`
- `ElevenLabs Agent ID`

These are exposed in the browser. Acceptable for a personal tool; do not ship this pattern publicly.

## Skill routing

gstack skills are available for all development tasks on this project. Use them proactively:

| When you need to... | Use |
|--------------------|-----|
| Plan a new feature or refactor | `/office-hours` → `/autoplan` |
| Review code before shipping | `/review` |
| Security audit | `/cso` |
| Test the UI in a real browser | `/qa` |
| Debug a silent failure | `/investigate` |
| Ship a PR | `/ship` |
| Remember a pattern for next session | `/learn` |
| Weekly retrospective | `/retro` |

For all web browsing, screenshots, and UI testing use `/browse` from gstack (not other browser tools).

Use the **Context7 doc server** (`resolve-library-id` + `query-docs`) for any ElevenLabs, FMP, Playwright, or other library documentation lookups — never rely on training data alone for API syntax.
