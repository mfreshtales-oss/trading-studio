# Trading Studio — Project Context

## Overview
Single-file HTML app. No build step, no framework, no package.json.
The entire application is `/home/user/trading-studio/index.html`.
Deploy = copy `index.html` to the server.

## Stack

| Layer | Technology |
|---|---|
| UI | Vanilla HTML/CSS/JS (ES2022) |
| Charts | Chart.js 4 (CDN), TradingView widgets |
| Market Data | FMP (Financial Modeling Prep) REST API |
| Voice | ElevenLabs v1 — TTS + Conversational AI (WebSocket) |
| AI Agent | ElevenLabs ConvAI — `agent_9101kp3xsh6tf1gs813edp1nqkwc` |
| Research | Tavily Search API (browser-side, user-provided key) |

## Key File

| File | Purpose |
|---|---|
| `index.html` | Entire application — CSS + HTML + JS in one file |

### Architecture (line ranges, approximate)
- **Lines 1–220**: Global CSS, layout, component styles
- **Lines 221–268**: Optimizer/AutoResearch CSS
- **Lines 269–283**: FMP watchlist CSS
- **Lines 284–720**: HTML structure (ticker, header, trading panel, EL panel, optimizer panel)
- **Lines 721–810**: JS constants, state variables, init
- **Lines 811–1350**: Market data (FMP), watchlist, ticker, bias notes
- **Lines 1351–1552**: ElevenLabs TTS, S2S, ConvAI WebSocket, `buildLiveContext()`
- **Lines 1553–1930**: Optimizer/AutoResearch engine + Tavily

### Hardcoded API Keys (lines ~724–727)
```
API_KEY  = sk_524569ce2cf217196514ae23cd02a0c890cb5963017dcbbe  (ElevenLabs)
AGENT_ID = agent_9101kp3xsh6tf1gs813edp1nqkwc
FMP_KEY  = 3r9vq1WORcFNCxoL6OimVbTuUP4VpamD
```
Acceptable for personal tool. Do not commit additional secrets.

## Key JS Functions

| Function | Purpose |
|---|---|
| `connectFMP()` | Authenticates FMP key, kicks off live market polling |
| `fetchFMPData()` | Fetches quotes for all watchlist symbols |
| `buildLiveContext()` | Assembles real-time market + discipline context string for ConvAI |
| `toggleConversation()` | Start/stop ElevenLabs ConvAI WebSocket session |
| `startConversation()` | Opens WS, sends auth + live context, wires mic/speaker |
| `generateTTS()` | ElevenLabs TTS REST call → AudioContext playback |
| `runS2S()` | Speech-to-speech via ElevenLabs audio isolation API |
| `updateMarketData()` | Updates all market cards, ticker, bias notes from FMP data |
| `buildTickerFromFMP()` | Populates top ticker bar from FMP quotes |
| `buildWatchlistPanel()` | Renders FMP live watchlist cards in trading panel |
| `startResearch()` | AutoResearch: 60-combo EMA/RSI parameter grid + Tavily |
| `runBaselineBacktest()` | Single backtest with fixed params (EMA 12/50, RSI 40–60) |
| `fetchSymbolHistory(sym)` | FMP 2yr OHLC for any of 5 symbols |
| `runTavilyResearch()` | Calls Tavily API, populates Market Intelligence panel |

## MCP Tool Inventory

### Trading Intelligence — `mcp__eae4afe6`
Primary server for all trade/market intelligence tasks:
`log_trade`, `get_full_trade_journal`, `get_trade_journal_summary`,
`get_market_context`, `get_market_sentiment`, `get_session_brief`,
`get_discipline_snapshot`, `get_discipline_trend`, `grade_trade_setup`,
`run_pre_trade_checklist`, `analyze_chart_with_ai`, `analyze_trade_with_ai`,
`calculate_position_size`, `get_latest_tradingview_alert`,
`list_recent_tradingview_alerts`, `get_weekly_performance_report`,
`generate_fresh_session_brief`, `generate_fresh_weekly_report`,
`smart_route`, `query_ai_model`, `list_ai_models`, `ping`, and more.

### Notion — `mcp__fbc229cb`
`notion-fetch`, `notion-search`, `notion-create-pages`, `notion-update-page`,
`notion-create-database`, `notion-get-users`, `notion-get-teams`

### Gmail — `mcp__105c7214`
`search_threads`, `get_thread`, `create_draft`, `list_labels`

### Google Calendar — `mcp__dcc6fb75`
`list_events`, `create_event`, `update_event`, `delete_event`, `get_event`, `suggest_time`

### Slack — `mcp__12efe043`
`slack_send_message`, `slack_read_channel`, `slack_search_public`,
`slack_search_users`, `slack_read_user_profile`

### Google Drive — `mcp__38e85a38`
`read_file_content`, `search_files`, `list_recent_files`, `get_file_metadata`

### Hugging Face — `mcp__8d8b45ae`
`hf_hub_query`, `hub_repo_search`, `hub_repo_details`, `paper_search`, `hf_doc_search`

### Context7 Docs — `mcp__874f5a94`
`resolve-library-id` + `query-docs` — use for ALL library/API/SDK lookups.
Never rely on training data for Chart.js, ElevenLabs SDK, FMP API, Tavily API — resolve and query instead.

## Development Notes
- **No test suite** — verify in browser at `http://localhost:8003`
- **No build pipeline** — edit `index.html` directly, refresh browser
- **No linter/formatter** — CSS is minified single-line by convention
- Branch convention: `claude/<description>-<id>`
- Always commit to the designated feature branch, never push to `main` directly

## gstack Skill Routing

| Task | Command |
|---|---|
| Code review / PR review | `/review` |
| QA / browser testing | `/qa` |
| Ship feature end-to-end | `/ship` |
| Design review / UI feedback | `/design-review` |
| HTML/CSS design from scratch | `/design-html` |
| Engineering planning | `/plan-eng-review` |
| CEO-level planning | `/plan-ceo-review` |
| Retro / post-mortem | `/retro` |
| Health check | `/health` |
| Learn project patterns | `/learn` |
| Investigate a bug | `/investigate` |

Use `/browse` (requires Chromium) for all browser/UI verification once available.
Install Chromium when network allows: `cd ~/.claude/skills/gstack && npx playwright install chromium`
