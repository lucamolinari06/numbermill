# Numbermill roadmap

## Current position

**Current milestone: Phase 4 earned arithmetic and computation service playable; Phase 3 complete.** The workshop has a compact symbol palette and a 16 by 9 build grid. Standard ADD, SUB, GT/EQ, and MUL blocks are now earned through binary challenges: half-adder, difference/borrow, comparison, and limited two-row multiplication. The challenges use fixed terminals, constrained gate slots, stepwise visible signals, and exhaustive binary tests. Only objectives and controls are shown; solution hints and worked examples have been removed. Unlocks and successful evidence persist in village saves, alongside unfinished drafts. Earned industrial blocks carry 16-bit decimal values through versioned nested devices. Mely and Luca's calculators earn setup fees and limited daily paid orders using real fuel and maintenance costs. Older villages retain arithmetic technology already used in their existing designs.

**Next implementation:** Connect citizen attendance and individual purchases to economic outcomes, then add migration and competing firms. Later Phase 4 extensions include memory, clocking, configurable multi-cell port layouts, more ports, and larger batch calculations. The current reusable device has two named 16-bit inputs (A west, B south) and one output (east), rotating as a unit. Interior inspection is a simulation copy; edit by loading the source from Library, then save a new version. Phase 2 and the extended Phase 4 remain in progress.

| Phase | Status | Remaining work |
| --- | --- | --- |
| 1. Business foundation | Playable expanded version | More operation effects, customer value and financial balancing |
| 2. Village and households | Playable expansion | Migration, deeper character consequences, competing firms, ownership behavior |
| 3. Contracts and inventors | Complete first version | Further job variety can be added alongside later phases |
| 4. Nested devices and compute | Arithmetic and paid computation playable | Memory, clocking, configurable port layouts, batch jobs |
| 5. Regional trade | Planned | Second village, transport, regional markets |
| 6. Generated content | Planned | Validated job templates and local model integration |

Completed playable features:

- [x] Circuit building, delayed signals, tests, submission, rewards, and reusable floor plans.
- [x] Five save slots, loading, deletion confirmation, and migration of older saves.
- [x] Separate business stock/cash and machine capacity effects.
- [x] Scrolling town, market shopping, cottages, household wages and food purchases.
- [x] Contract board with availability, prerequisites, benefits, and job selection.
- [x] First rival inventor and business-driven contract offers.
- [x] Due days and visible business decisions after missed jobs.
- [x] Workshop Help menu and uncluttered build panel.
- [x] Third and fourth authored levels: NAND bakery safety vent and NOR market cooler.
- [x] Fifth and sixth authored levels: AND-NOT farm pump interlock and three-input market majority controller.
- [x] Player design ownership, customer-owned copies, and paid licenses.
- [x] Compact two-dimensional village, map, visible farm, fuel yard, repair shop, and inventor workshop.
- [x] Mely and Luca as central named residents, with shared household, motives, conversations, and fuel-to-parts trade.
- [x] Installed steam machines purchase Mely's fuel each production day and pause when fuel is unavailable.
- [x] Luca's parts shop sells to a passing mechanic as a small external trade route; full regional markets remain Phase 5.
- [x] Residents and Nell walk to their current destinations; player movement respects building footprints.
- [x] Remote NPC inspection by clicking; timed visits and new decisions without advancing economic days.
- [x] Wider space between the market road and houses, with a connected residential street.
- [x] Town Ledger with overview, map, people, businesses, trade, inventors, and workshop service.
- [x] Saved daily charts and exchange records, with older/newer day navigation.
- [x] Optional repeatable workshop service that buys fuel and parts, tunes a customer's machine, and pays net income.
- [ ] Migration and automatic village expansion.
- [x] Named input/output ports, saved device versions, and nested devices with independent state and preserved signal delays.
- [x] Inspect devices within devices; recursive definitions rejected and existing placements retain their saved versions.
- [x] Compact symbol palette and 16 by 9 workbench (144 build cells, previously 88).
- [x] 16-bit buses, addition, subtraction, multiplication, greater-than and equality, including nested numeric devices.
- [x] Earn permanent arithmetic unlocks by building compact binary-gate inventions; no full-width binary implementation required.
- [x] Binary prototype tracing, all-case tests, saved drafts and evidence, and protection against locked technology in nested devices or compute registration.
- [x] Mely's fuel quotes and Luca's repair estimates and stock comparisons, with eight-case validation including numeric boundaries.
- [x] Customer-funded setup payments and paid calculation orders, capped at two runs per day and one order per calculator per day.
- [x] Contract progression extended with multi-gate interlocks, a third truth-table input, and new farm/market machine effects.
- [x] Fuel purchases, maintenance costs, saved receipts, trade records, and a temporary customer production-planning benefit.
- [ ] Memory, clocking, multi-cell port layouts, and larger batch computation services.

The core loop is: businesses encounter a real bottleneck, inventors offer a machine or computation, the result changes production and trade, and those changes alter jobs, prices, and eventually migration. The player should be able to trace each important change in the UI.

## 1. Business and market foundation (in progress)

- Represent each firm as an instance with a type, owner, optional parent company, cash, stock, workers, and installed machines. Multiple firms can share a type.
- Give business types production recipes. Machine effects modify specific operations such as capacity, fuel use, waste, reliability, or delivery speed.
- Move goods and money between firms on each day. Show stock, capacity, cash, and the reason for price changes in a readable ledger.
- Preserve older saves when introducing the new model.

## 2. Visible village growth and more businesses

Current slice: the farm, mill, workshop, bakery, market, fuel yard, repair shop, three homes, and Nell's workshop are on the walkable map. Six residents belong to three households. The action system tracks hunger, energy, mood, social needs, relationships, and a short memory. Economic days update meals and household finances. While in town, residents finish visits and choose another feasible activity; resting restores energy, work uses energy, and visits reduce social needs. Social visits use neighbors' workplaces rather than funneling everyone to one cottage. Click a visible NPC to inspect activity, family, and town information. Household purchases and wages still run on the daily economy tick; attendance and individual shopping decisions are the next simulation link. Migration and automatic building growth remain future work.

- Extend the walkable town with more buildings that correspond to real firms. Add a market as the first new buyer of bakery goods, then introduce distinct trades and competing firms.
- Keep the map navigable as it grows, with clear signs, local interactions, and a business directory instead of crowding every firm into one panel.
- Introduce citizens as persistent people with a home, workplace, wage, household budget, and needs. They buy goods from businesses; purchases become business income and shortages affect their well-being.
- Let jobs, wages, food affordability, housing, and safety affect arrivals and departures. New households and firms create commissions and attract additional inventors.
- Allow business entry, competition, closure, and parent/subsidiary ownership to respond to the market. Keep early growth bounded and understandable.
- Give Mely and Luca multi-step personal arcs and meaningful effects of friendships, hardships, and competing inventor decisions. Preserve their agency outside quests.

## 3. Contracts and inventor market

- Add a contract board with customer, problem, reward, deadline, required behavior, and projected business effect.
- Let businesses post work when an expected loss is greater than the price of a fix. Let a rival inventor bid and complete a limited amount of work.
- Let the player keep designs, install a machine for a customer, sell a copy, or license its use. Show who owns each design.
- Missing a contract must lead to a visible business decision, such as waiting, buying from another inventor, or reducing output. Do not make one missed job end a save.

## 4. Nested devices, workbench, and computation services

- Let players save a design with named input and output ports, then place it as one reusable device on another design's grid. A device may occupy multiple cells (for example, 2 by 3) to fit its ports. Nested designs must support many layers without a fixed nesting limit in normal play.
- Evaluate nested devices with shared circuit semantics. Detect direct or indirect recursion, preserve timing and state, and provide a way to enter a device to inspect or edit its internals. Version saved designs so changing a reusable part does not silently break old machines.
- Upgrade from floor-sized blocks to the compact workbench view as builds become denser. The larger floor grid can stay the same size while the workbench allows detailed internals.
- Add multi-bit inputs and outputs, memory, clocking, arithmetic, and a test harness that checks cases and timing.
- Add per-use compute contracts: sums and comparisons first, then batches, finite differences, and more advanced jobs.
- Charge workshop steam, time, and maintenance so service capacity and outsourcing matter.

## 5. Regional trade

- Add another village with different resources, prices, firms, and commissions.
- Make transport time and cost matter for goods and machines; allow compute services to trade across villages when communication infrastructure exists.
- Expand to larger regions only after the two-village economy remains understandable and stable.

## 6. Generated content

- Use hand-authored jobs to define reliable templates and validation rules first.
- A local model may later propose stories, contract details, and business variants. The game must validate each job's truth table, available parts, economic effect, and reward before offering it.

## Interface rule for every phase

Keep the town map for place and people, the contract board for decisions, and a compact economy view for causes and consequences. Every important change should have a short explanation such as "flour shortage -> bakery output fell -> bread price rose." Avoid asking players to read raw accounting tables to understand the next action.
