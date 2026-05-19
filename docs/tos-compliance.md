# Riot Third-Party Policy Compliance

This document maps each LOL Helper feature to Riot's Developer Policy and Third
Party Application Guidelines. Treat as living doc — re-check at every major
Riot policy update.

Reference: <https://developer.riotgames.com/policies/general>, [Third-Party
Applications support article](https://support-leagueoflegends.riotgames.com/hc/en-us/articles/225266848).

## ✅ Explicitly permitted

| Feature | Mechanism | Policy basis |
|---------|-----------|--------------|
| Arena stats site | Riot Match-V5 + Data Dragon / Community Dragon | Same as OP.GG, U.GG, lolalytics |
| Login via Google | Google OAuth | Independent of Riot identity |
| Pre-game / champ-select assist | Read LCU API (HTTPS, lockfile auth) | Same as Mobalytics, Blitz |
| Always-on-top transparent overlay | Standard Win32 window with `WS_EX_TOPMOST` + alpha | Same as Discord overlay |
| Augment / item win rate display | Aggregated stats (read-only) | Same as Blitz Arena, lolalytics |
| Personal Mayhem stats (own LCU history) | LCU `/lol-match-history` for user's own puuid | LCU is intended for client features |

## ⚠️ Edge cases requiring care

### Crowdsourced Mayhem aggregation

Riot has blocked Match-V5 for Mayhem and the policy direction is "no public
aggregation of new rotating modes." We sidestep the *API* restriction by
reading LCU (which is local data, owned by the user), but the *aggregation
goal* is in a grey area.

Mitigations:
- Explicit user consent screen on first launch
- Easy opt-out in settings (off → upload immediately stops)
- Privacy policy lists every field collected
- Stats shown publicly are aggregated (no PII, no individual match links to
  identifiable players)
- If Riot asks us to stop, we stop within 7 days

### Live Client Data API polling

Allowed for *informational* display only. We must NOT:
- Trigger any keystroke / mouse event
- Hide enemy ultimate cooldowns (banned 2025-07)
- Show information not visible to the player in-game (e.g. enemy items
  before they're revealed)

## ❌ Forbidden — DO NOT IMPLEMENT

- Reading game memory (would trip Vanguard, instant ToS violation)
- Automating any in-game action (auto-cast, auto-buy, auto-select)
- Adding ads inside the game client (banned 2025-05)
- Cloning the Riot client UI
- Sharing API keys publicly
- Hosting Riot copyrighted assets we didn't get via DDragon / Community Dragon

## Operational practices

- Privacy policy page on website (collected fields, retention, deletion)
- ToS page with the standard disclaimer:
  > This product isn't endorsed by Riot Games and doesn't reflect the views
  > or opinions of Riot Games or anyone officially involved in producing or
  > managing League of Legends. League of Legends and Riot Games are
  > trademarks or registered trademarks of Riot Games, Inc.
- GDPR delete-account flow (DELETE `/auth/me`)
- `X-Client-Version` header on every .exe request — lets backend reject
  clients that pre-date a compliance change

## When in doubt

1. Re-read the policy
2. Check what Blitz / Mobalytics / Porofessor do (they have legal teams)
3. Email `apisupport@riotgames.com` if a feature feels grey
4. Default to *not* shipping the feature until clarified
