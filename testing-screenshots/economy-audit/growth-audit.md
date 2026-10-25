# Growth and business viability audit

Read-only simulation audit. No player saves or gameplay source were edited.

Method: create a fresh `Village()` and persistent `Town()`; install the named upgrades through existing `complete_*_job()` fixture helpers on day 1; then call `advance_day(town)` 365 times. No further player purchases, project deliveries, service, or computation orders. Grace still bids and installs later jobs naturally. The full-upgrade fixture completes mill, bakery, vent, market, pump, and sorter on day 1. Every helper returned true. These fixtures test long-run autonomous viability rather than circuit-building progression. Result data: `growth-audit.json`.

## Confirmed results

- Mill-only start: first day of a sustained zero-households-fed stretch is day120; zero bakery production begins day122. At day365, the streaks are246 and244 days respectively. Farm, mill, bakery, and market each have0c. Jun remains paused with500c. Six residents remain.
- All-upgrades start: first sustained zero-households-fed day168; zero bakery-production day169. At day365, the streaks are198 and197 days. Farm, mill, bakery, and market each have0c. Jun remains paused with674c. Six residents remain.
- No negative business cash or stocks in either365-day scenario.
- Rowan arrives on day5 in both fixtures and leaves on day54 (mill fixture) or56 (all upgrades). In the mill fixture, his household has1c by day30 despite daily work.
- Separate initial baseline audit without player upgrades also declined: at day365, founding food firms had0c, but3 households were fed that particular day. Thus collapse timing depends on upgrade/order history; some scenarios still intermittently trade.

## Causes visible in current formulas

With four loaves of total daily output split between two bakers, the incumbent upgraded bakery earns14c for two loaves, spends10c on flour,4c on wages, and2c on steam: a2c daily loss. An upgraded market selling four loaves for8c each earns32c, buys them for28c, and pays4c wages plus2c steam: another2c daily loss. Jun's owner-operated oven has no resident wage or steam cost and can retain4c per day. Liquidity accumulates outside the food employers while the food chain loses working capital.

Migration adds Rowan at4c/day to a household needing a loaf costing at least8c. Added apprentice slots do not raise current firms' production caps: a single worker already meets the capacity limit for their current recipe/upgrades. They therefore add wage expense without additional maximum output.

These are long-run economic balance failures, not evidence that transactions create negative funds. Current short tests cannot justify claiming the economy is fully functional and sustainably balanced. A repair should review operating margins, household earning power, and productive labor capacity together, then repeat these stress scenarios.
