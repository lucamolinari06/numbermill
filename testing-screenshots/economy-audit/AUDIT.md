# Economy stabilization verification

Six independent 365-day simulations completed (2,190 simulated days). No player saves were read or changed. Each step ran the same attendance, purchases, settlement, and rollover code as the game.

| Scenario | Fed at day 365 | Residents | Delivered contracts | Cash / stock violations | Exact save continuation |
| --- | --- | --- | --- | --- | --- |
| unassisted | 6/6 | 9 | 18 | 0 | True |
| mill_upgrade | 6/6 | 9 | 18 | 0 | True |
| all_upgrades | 6/6 | 9 | 18 | 0 | True |
| all_upgrades_service | 6/6 | 9 | 18 | 0 | True |
| all_18_player_deliveries | 6/6 | 9 | 18 | 0 | True |
| all_18_player_service | 6/6 | 9 | 18 | 0 | True |

## Changes verified

- Wholesale flour costs 4c and bread 6c; normal household bread remains 8c. Three daily sales cover a founder's 4c wage and 2c steam cost. Competitive bakers pay the incumbent a real 2c facility lease.
- Working inventory is bounded. Optional workshop service rotates customers and keeps at least 48c operating funds plus the next controller budget; royalties also preserve that reserve. Service pays Luca 3c per part, covering his fuel input, and charges the customer 8c so the player still earns 2c net.
- New resident jobs pay 8c, cover one household loaf, and need three days of demonstrated operating surplus. Continued growth follows later controllers: food capacity reaches six daily loaves, and the repair-selector/priority controllers open bounded regional kit orders.
- Each timber/metal kit consumes one actual material, protects local reserves, and pays 10c/12c from an explicit outside workshop. Once a packing employee is hired, shipment requires their completed work shift. One order per supplier per day.
- A regional cart buys at most one surplus fuel unit for 3c per day after six fuel reserves. The established mechanic's 8c parts order remains. Every outside payment is marked in the Trade ledger.
- Contract payments and royalties now appear in the Trade ledger. Loading preserves all eight journal entries.
- A separate depleted-save simulation started all four food businesses with zero cash and zero food stocks. A funded 36c inter-business startup advance per firm restarted production without creating cash. After 365 days all six households were fed; all four advances had been fully repaid. Each firm can take this startup advance only once; repayment takes at most 4c/day from cash above 64c.

The first four scenarios allow Grace to progress later commissions; the final two deliver all available later commissions as the player, with and without recurring service. Commission setup helpers test their economic effects and real customer payouts; circuit correctness and physical-material delivery have separate regression coverage. These runs establish deterministic stability for the tested strategies, not every possible player-induced shortage or spending pattern.

Reproduce with `.\.venv\Scripts\python.exe scripts/audit_economy.py`. Detailed checkpoints and exact cash-conservation checks are in `report.json`.
