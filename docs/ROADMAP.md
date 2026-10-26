# Numbermill roadmap

## Current position

**Reedhaven and continuous day/night cycle (October 26):** The rotating day/night disc and smooth dawn are implemented, and the southern boat route and Reedhaven are playable. This follows the approved priority of new content before audio. The player's canal/lake/dock drawing is the layout reference (`testing-screenshots/canal-settlement/layout-reference.png`): an upper canal opens into a lake on the right, with the arrival dock on its northeastern bank. Reedhaven uses pale lockstone, copper roofs, towpaths, a footbridge, reeds and a small trading square. Existing-level layout revisions follow this content update; a cohesive sound pass remains deferred until the expanded locations are established. The earlier audio-first recommendations below are historical checkpoints superseded by this priority.

The southern launch is restored only after the expanded Mosswater archive and Boiler Tower are complete. Their cutter blueprint and steam accumulator remain permanent upgrades. Fit one manufactured precision gear, then build and certify the boat's three-input steam-feed/departure controller. Its 208 cases cover safe pressure, requested feed and clear/fault status. A passing installed circuit and the mechanical repair unlock free repeat passage. Reedhaven's initial scope is four residents, a finite market, a saved cistern-supply request, an exchange-record clue and the upstream waterworks lead; it does not implement the waterworks expedition or a second full economy.

**Reedhaven presentation and continuity:** The road surface is one union of rounded branches, junctions and courts. Complete paving texture is clipped to that mask so brick edges cannot spill onto grass; the lockhouse connection passes around its east side to a separate front-door spur. Roof forms/materials, gardens, ropework, boatyard equipment, retaining stone and grouped planting distinguish the neighborhoods while preserving clear routes. Window lights use the actual visible-glass pixels, retaining arches, mullions, shutters and awnings. Conversations pause simulation and fit their panels; their close/return actions clear stale controls. Boat drafts, installed controllers, repair stock, local trades, discoveries, position and current settlement survive saves. A short travel fade respects pause and reduced motion. The existing player saves and preferences are not used by review scripts.

**Verification: 533 tests pass with zero failures/errors, and all scripted UI checks pass.** Native verification: the clock completed **1,140 normal-speed Windows frames** across one rollover, with continuous palette/lamps and 60 exactly paused frames. Reedhaven completed **711 movement frames** from the landing along the towpath and over the bridge to the market, checking Boole and Shannon against collision on every frame, then 60 exact paused frames, reduced motion and save/reload. All six 365-day economy scenarios have zero violations and exact save continuation. After the final market-counter collision correction, all eight world tests pass, including reachability, full paving-mask coverage, visible-glass masking and every dialogue branch's text bounds. Captures/reports: `testing-screenshots/day-clock/` and `testing-screenshots/canal-settlement/review.html`; reproduce with `scripts/capture_day_clock.py --smoke`, `scripts/capture_canal_settlement.py --smoke` and `scripts/capture_canal_departure.py`. Longer player-led route and content review remains distinct from these checks.

**Staggered evening home entry (October 26):** Residents now leave for their own homes at individual village-clock times between 17:45 and 18:45, with a small deterministic day-to-day variation. Evening return overrides an unfinished visit or journey, follows existing routes and uses the actual front door instead of a shared outdoor waiting slot. A resident disappears only once the displayed walker reaches that door, stays indoors for the remainder of the day and resumes normal needs/work/shopping choices the next morning. Grace retires into her workshop on her own schedule. Indoor residents have no outdoor sprite/nameplate/click target and do not supply imaginary social company. Existing citizen activity, destination, position/path and clock fields preserve household night entry across save/reload without a save-format migration. `scripts/capture_resident_evenings.py --smoke` produces disposable evening/morning views and a native entry/pause check in `testing-screenshots/resident-evenings/`. The existing-game audio/camera/arrival/reward follow-up remains next.

Evening verification: **504 tests and all scripted UI checks pass**, including seven new stagger/arrival/visibility/social/morning/save-continuation checks. All six 365-day economy scenarios have zero violations and exact save continuation. A disposable Windows window completed 720 normal-speed update frames, observed four distinct residents enter their homes and held exact scene/state across 60 paused frames. Reviewed 17:30, 18:30 and 19:56 cottage-lane views; the complete five-time evening set, next morning, native frame, focused log and report are in `testing-screenshots/resident-evenings/`. No player save files or preferences were used.

**Copperside environmental animation and daylight (October 26):** The village now moves from restrained morning warmth through neutral midday and late-afternoon gold into a readable cooler evening using the same 08:00–20:00 clock as the HUD. Occupied cottages and shops gain warm visible panes, dormers/skylights and small lantern halos; mullions, shutters, roof materials and market awnings stay intact. Sparse drifting leaves remain inside existing tree reservations and share the scenery/actor depth order. River motion, smoke, fireboxes, mill wheels and trade gears use the paused visual clock. Production effects respect arrived workers, owner-operated trades, closures, shortages, daily limits and real workshop batches; stopped ovens no longer retain a bright painted fire. Reduced motion holds decorative poses and water/smoke still, omits drifting leaves and keeps clock-based lighting legible. HUDs, nameplates and interaction UI retain their shared colors.

Path integration follow-up: removed the hard ribbon-like garden-path edging, broke curb/paving rims at path mouths and carried subtle worn-earth texture into the street joins. The west branch now reaches the street. Shared footprints reserve the full paths and court against raised props and decorative planting; the existing well furniture remains present. Buildings, roofs, collision, resident decisions, economics and save formats are unchanged. Audio and new locations are outside this pass.

Review: `testing-screenshots/copperside-daylight/review.html` switches **24 matching before/after 1280 × 760 views**, covering six places at 08:30, 12:00, 17:00 and 19:30, including populated streets, river cottages and developed eastern housing/commercial sites. An additional 24 views advance that disposable developed village through its actual routines and production. Reproduce with `scripts/capture_copperside_daylight.py`; `--smoke` checks a disposable Windows window, motion, Escape pause/resume and reduced motion. Player saves/preferences are isolated. Next: player visual review, then the existing-game audio foundation and sound controls; camera, arrival/reward and full-route pacing polish still precede the southern settlement.

Daylight verification: **497 tests, zero failures/errors and all UI checks pass** in `scripts/debug_game.py`. After the final successor-trade effect guard, **51 focused town/daylight/scenery/depth tests pass** again. All six 365-day economy scenarios have zero violations and exact save continuation (`testing-screenshots/economy-audit/report.json`). The disposable native Windows run completed 150 moving frames, 60 frames of byte-identical paused scenery/state, resumed correctly and held decoration still for 60 reduced-motion frames; `native-check.json`, `native-motion.gif`, pause and evening frames are in the daylight review directory. Rendering checks cover actual clock/save reload, lighting contrast, visible-glass masks, unchanged cached roof art, road/court joins, full path/prop clearance and existing furniture. Native and gameplay-scale views were inspected; final aesthetic acceptance and longer player playtests remain separate.

**Constant number sources (October 26):** Circuit builders now have a **Constant number (#)** block in the Logic palette. Place it and enter a whole number from 0 to 65535; click its body to edit, right-click to rotate, and wire its single output normally. Each block retains its own value in saved drafts, reusable/nested designs and installed controllers. Editing preserves attached traces and invalidates previous certification. The editor pauses simulation, rejects out-of-range values and supports Enter to apply/Escape to cancel. Gate-only arithmetic invention challenges retain their existing restrictions. Sources follow the usual tick/pipe delays, including zero-valued outputs. Disposable previews and native-window checks are reproduced with `scripts/capture_constant_sources.py --smoke`.

Constant-source verification: **484 tests and all UI checks pass** in `scripts/debug_game.py`, including nine new source/editor checks. The final modal pause-handling adjustment passes all nine focused checks again. A disposable native-window run verified placement, typing, mouse apply, range rejection, cancellation, wiring, numeric output and save/reload. Previews and the smoke log are in `testing-screenshots/constant-sources/`.

**Character and resident performance pass (October 26):** The next Copperside slice is implemented. Named residents and the arriving resident pool have consistent outfits across all four facings and dialogue portraits, with small idle shifts/blinks, directional workwear and conversation turns. Grace retains her wooden prosthesis in standing, walking and seated poses. Shannon has hinged arms and an attentive face/body pose when addressed; his decorative motion respects reduced motion, and the village console now uses the paused simulation clock.

Destination performances follow the existing routines: shopping baskets, farm tending, sweeping, tool gestures, inspecting notes, resting on stools and seated conversation at home. Work/rest poses wait for arrival at the resident's actual reserved slot; social gestures require another arrived resident nearby at the same destination, and spouse visits require the spouse. Paused workplaces show inspection rather than active work. These are presentation changes: movement, attendance, purchases, needs, routes and save data remain authoritative and unchanged.

Character verification: `scripts/debug_game.py` passed **475 tests and its UI checks**. After the final pose adjustments, **43 focused character/town/depth/dialogue checks** passed; a disposable native window completed 180 walking/return frames with companion collision checks. Native-scale four-facing sheets, a looping motion sheet and staged in-town views are in `testing-screenshots/resident-performance/review.html`; reproduce with `scripts/capture_resident_performance.py --smoke`. Visual acceptance and longer player playtests remain. The subsequent Copperside environmental motion/daylight treatment is delivered above; audio, camera and arrival/reward polish remain before the southern settlement.

Roof review correction: removed the broad, untextured right-side overlays from every affected roof. Existing shingle, tile, slate and metal textures now continue to the edge, retaining the building outlines. Future roof polish should refine textures without adding simulated side faces.

**Copperside environment follow-up:** The approved first pass now reshapes the existing streets into narrower stretches and broader forecourts, adds smaller varied stone paving and a quieter gravel cottage lane, connects the well garden with worn paths, and grounds work yards, doorsteps and the bridge approach. Riverbank planting is grouped with open intervals; future sites retain their footprints and fences with natural grass instead of flat green panels. Buildings, entrances, resident travel lines, river collision, save data and economic behavior retain their existing positions and rules. The minimap and ledger use the same new road contours.

Roof silhouettes and established facades are retained. Materials now follow the roof planes: timber boards, overlapping shingles, clay tiles, slate and seamed patinated metal, with ridge caps, fascia and eave shadows. Triangular roofs keep a complete material surface, with receding courses, chipped slate edges and continuous eaves. This environment pass remains available for gameplay-scale review alongside the subsequent character and destination-activity pass. Matching before/after views, developed eastern sites and all eighteen buildings are in `testing-screenshots/copperside-environment-review/`; `review.html` switches matching views at native size. Reproduce current views with `scripts/capture_copperside_environment.py` (`--smoke` also exercises a disposable native window and walking).

Environment verification: the full `scripts/debug_game.py` run passed **468 tests and its UI checks**. After the final triangular-roof correction, **38 focused town/scenery/depth checks** and the native-window walking smoke check passed again. Coverage includes every building-to-building resident trip on the new roads, doorway waiting space, future-site reservations, player/Shannon movement, roof drawing bounds, river/bridge collision, deterministic rendering and actor/prop occlusion. All six 365-day economy-audit scenarios had zero violations and exact save continuation. Logs are in `testing-screenshots/debug-run/`, `testing-screenshots/copperside-environment-review/focused-tests.log` and `testing-screenshots/economy-audit/report.json`. These establish regression safety; visual acceptance remains the player's review.

Fullscreen now fills the entire display with matching pointer mapping; sharp/smooth scaling changes filtering rather than screen coverage. Opening artwork covers its canvas with a small edge crop instead of internal letterboxing. Windowed screens retain proportional fitting.

Startup presentation: eight selected pixel-art backgrounds now crossfade before the main menu, with the Numbermill mill-wheel seal and title in the top-left, a pulsing “Press any key to begin” prompt and a fade into the title. Any key or mouse click begins; F11 remains available. Reduced motion keeps the opening static. Artwork is bundled for packaged builds. New saves show a short parchment introduction before entering Copperside; existing saves load directly. Next step: player review of timing, image selection and introductory copy. A future animated scene showing Boole meeting Shannon is planned; the scroll gives only light context and does not tell that meeting or reveal Shannon's origins.

Startup verification: 56 focused opening/new-save/menu/display/chapter tests pass. New-save creation by button and keyboard, paused village state, dismissal, reload and closing during the scroll are covered. Branding and parchment previews, including fullscreen, are in `testing-screenshots/startup-introduction/`. Earlier checks rendered all eight backgrounds and verified the two-image cache and title transition. Packaged binaries have not been rebuilt.

**Current milestone: two playable expeditions, including Boiler Tower's expanded platforming route.** The workshop now makes repair kits, metal plates, steam valves and precision gears. Every automated purchase, batch and sale still requires a player-built circuit. Explicit storage outputs, configurable product dispatch and live displays connect the production chain. Circuit Bench opens the saved sandbox by default; its right sidebar has separated component groups and checked layouts across modes.

The first refurbished bench and inputs still fit the starting 12c. Existing local maintenance customers and the daily road crew remain; additional products have finite, saved outside orders (two per product per day). The press and lathe are immediately purchasable; the precision cutter is visible but requires a recovered blueprint. Crafting gears consumes plates and valves, and correctly frees space when processing a full output rack. Saves retain running batches, controllers, separate drafts and order limits.

**First expedition:** Follow the north road's Mosswater sign and press E at the trail entrance. Mosswater now spans a 4200 by 1850 landscape with branching woodland and reed-marsh paths, ponds, ruined mechanisms and two guarded ravines. Recover Shannon's receiver, build its packet decoder, and reconstruct the first bridge's pressure/latch interlock. The former artifact alcove is now a survey station. Locate three concealed beacons by manually selecting bearings and channels, recording separated bearings, and closing to a short-range scan. A final range lock requires two specific distance bands from the same position before the archive bridge opens. The archive grants the existing precision cutter blueprint and focused lens; older saves retain already-earned rewards and can still complete the new survey. Survey samples, channel/bearing settings and gate progress are saved. The original 256-case decoder and 364-case interlock certification remain. Player hunger is removed. Bread heals 25 health; steam traps deal 25 damage. Neither closed bridge can be bypassed during injury cooldown. No late-story identity is revealed.

**Second expedition:** Completing Mosswater's expanded archive unlocks **Travel to Boiler Tower** in the field HUD. The expanded side-view route climbs 31 solid platforms through the Boiler Galleries, Driveworks and Condenser Crown, with ten traversals between each maintenance stop. Fifteen steam bursts, moving hot gears and cycling pistons make timing and flight control the main challenge; green rest flags save intermediate progress without extra puzzles. Players still build the first flight controller, revise their saved draft at two maintenance stations, and build an exhaust regulator for the upper curtain. Pressure, heat, throttle, valve output and seal damage explain performance. Shannon accompanies Boole on a service rail. The pack fails at the final safe landing; the archive awards a permanent steam accumulator, reducing new factory batch durations by 20% without reducing material costs. The return cage leads home. Old tower saves migrate to the equivalent maintenance stage with their circuits, health and rewards intact.

**Current delivery: the first substantial art/UI implementation across phases 1–3, followed by the connected opening chapter.** Copperside now has distinct shop architecture, corrected roofs and cottage details, richer planted/work-yard decoration, resident activity props and animated machinery. Mosswater has woodland/marsh/ruin detail and natural ponds/rivers; Boiler Tower has distinct furnace, Driveworks and mountain-window treatments. The production floor, circuit bench, dialogue, title/save/pause/settings, ledger and supporting screens share the refreshed presentation. Resizing, maximizing, fullscreen, scaled input, reduced motion and a controls page are implemented. This is a major first pass, not completion of every phase: audio, richer expressions, camera/pacing playtests and further arrival/reward presentation remain. The opening chapter now includes an evidence journal, saved homecomings and contextual conversations. Continue polishing the existing game before new locations take priority.

**Approved expansion order:** Finish the existing game's visual/UI overhaul and opening story connections; open the southern bridge route to a small canal settlement; build a waterworks expedition; add a separate flower-filled plains expedition; then reach the mountain laboratory reveal and a final adventure around a failing regional steam system. Expand workshop logistics and regional trade when these places create understandable needs. Broader gadgets, food preparation, workers/material handling, additional controller ports, central boards and conveyors remain later supporting work. Existing commissions and computation services remain optional; their retirement has not been implemented. See [Approved direction and phased delivery](#approved-direction-and-phased-delivery).

**Story canon and current direction:** Boole seeks the anonymous engineer behind the legendary steam logic gates he and Grace use; the engineer is eventually revealed as Luca, and Shannon is his creation. Luca removed Shannon's compulsory companionship instruction and erased his autobiographical memories while preserving his technical knowledge and personality. Shannon did not consent; his later choice of Boole is his own. Luca trusts them at dangerous sites because Shannon helps understand traps, and Shannon choosing Boole convinces Luca that Boole is as capable, or nearly as capable, as Luca was in his engineering years. Luca left his remote mountain laboratory after the wipe and moved to the village; Shannon rebooted at the lab and followed later. Mely alone knows Luca's secret. Signed work and Shannon's blueprints reveal the truth at the lab, opening the finale. Boole, Shannon and Luca then confront a failing regional steam system connected to Luca's earlier work; the exact failure, puzzles and ending will be refined later. See [Planned main story](#planned-main-story-shannons-origins). The connected opening chapter is now playable; the laboratory reveal, later regions and finale remain planned. Both expeditions, their current rewards and Grace's wooden prosthesis are already playable.

| System track | Status | Remaining work |
| --- | --- | --- |
| 1. Business foundation | Four products, intermediate crafting and player automation playable | Workers, logistics, balancing, broader demand |
| 2. Village and households | Dynamic growth, initial Mely/Luca arcs, new architecture/decoration and resident presentation playable | Richer character expressions and everyday scenes, Luca mystery arc, Mely friendship conversations, broader town expansion |
| 3. Contracts and inventors | Complete first version | Further job variety can be added alongside later phases |
| 4. Nested devices and compute | Arithmetic, memory, clocks, counters and timing goals playable | Configurable port layouts/footprints, batch jobs |
| 5. Exploration and regional trade | Mosswater survey and Boiler Tower jetpack climb playable, with new scenery, compact HUDs and lasting factory rewards | Audio/camera/arrival/reward polish, canal settlement, waterworks, flower-filled plains, lab reveal and regional steam-system finale |
| 6. Generated content | Planned | Validated job templates and local model integration |

## Approved direction and phased delivery

**Approved October 25, 2026; implementation underway.** A substantial first art/UI pass across delivery phases 1–3 is now implemented. The progress notes and checkboxes below distinguish delivered work from remaining scope. Opening-story integration is implemented; new locations and later story revelations remain planned. The delivery phases set the development order; numbered system tracks elsewhere organize features by subject.

**Game identity:** An engineering adventure where Boole and Shannon explore forgotten machinery, build a life in Copperside, and gradually discover the person behind both. Exploration brings discoveries, engineering gives the player ways to act on them, and the village gives the results personal meaning.

### Scope and design commitments

- Prioritize substantial improvements to every existing visual surface before expanding the world: environments, buildings, characters, animation, workshop machines, circuit tools, dialogue, HUDs, menus, maps, ledger, library, shops, contracts and result screens.
- Preserve the recognizable pixel-art direction and copper/teal/wood/parchment language. Establish consistent pixel scale, silhouettes, materials, shadows, typography, spacing and interaction states. Improve composition, depth and animation as well as prop density; incidental detail must leave routes, actors, hazards and circuit connections legible.
- Use distinctive authored landmarks, building shapes and environmental assets where repeated generic forms weaken a place's identity. Existing procedural/cached scenery can support these assets. The overhaul does not depend on an engine change.
- Every body of water has a natural, nonrectangular shoreline, with collision derived from that same shape. Keep bridge openings and hazard gates secure, and recover older saves onto nearby dry ground if a changed shoreline overlaps their position. This applies to Mosswater's ponds/rivers and Copperside's river, including map representations.
- Inspect every building at gameplay scale: no exposed wall corners above sloping roofs, floating chimneys or disconnected architectural pieces. Village detail should suggest life through gardens, possessions and work activity while preserving clear routes and doors.
- Keep manual component placement, player-controlled wire routing and behavior-only circuit specifications. Explain observations and failed tests without supplying solutions. Preserve existing mechanics, saved designs, rewards and progression unless a later feature explicitly requires a documented migration.
- Give each expedition a distinct activity, visual identity, useful reward, story development and homecoming consequence. Maintain safe opportunities to stop, read and recover.
- Make workshop expansion respond to discoveries and regional needs. Keep the main adventure approachable with a modest workshop; substantial automation offers efficiency, flexibility and optional achievements.
- Existing simulation and personal arcs remain valuable foundations. Show their effects in the world and strengthen their presentation before adding more systems.

### Delivery phases and completion goals

| Delivery phase | Scope | Completion goal |
| --- | --- | --- |
| 1. Visual direction and shared UI foundation | Inventory every current screen; playtest the current routes; establish an art/style guide, UI hierarchy and representative world/character/workshop treatments. Build reusable exploration, engineering and dialogue presentations, with input feedback and readable typography. Outline the clue timeline needed by early scenes. | Representative town, forest, tower, workshop and menu views demonstrate an unmistakable graphical improvement and one coherent interface. Current gameplay/regression issues are recorded, and the full scene checklist has an agreed treatment. |
| 2. Copperside, characters and workshop overhaul | Give buildings unique silhouettes, neighborhoods character, streets and riverbanks richer composition, residents visible activities, and characters richer motion. Refresh production equipment, the factory floor, circuit bench and all supporting screens. Complete title/save/pause/options/map/ledger/library/shop/contract/result treatments and basic display/accessibility comforts. | The full town-to-workshop loop and supporting menus use the new presentation. Ordinary life and business activity are visible; doors, paths, future building sites, controls and circuit connections remain clear. |
| 3. Mosswater and Boiler Tower overhaul | Deliver the full woodland/marsh/ruins/archive treatment and three distinct tower sections, compact contextual HUDs, lighting, environmental motion, sound, readable hazards, camera improvements and satisfying expedition endings. Playtest and adjust navigation, timing and checkpoint pacing. | Both complete expeditions meet the same visual standard as town and workshop, including transitions, injury/recovery and rewards. Traversal and engineering remain understandable in motion. Phases 1-3 complete the major existing-game graphical/UI milestone. |
| 4. Connected opening chapter | Complete Mosswater and tower homecomings, visible accumulator installation, contextual reactions, evidence journal, fair clues and everyday character scenes. Integrate the existing Luca/Mely/Grace arcs with the main mystery. Early scenes can accompany phases 1-3; this phase closes the complete opening chapter. | A player can understand Boole's search, care about Shannon and the residents, notice evolving evidence, and see discoveries change life at home. Existing saves retain progress and receive coherent story follow-up. |
| 5. Southern launch and canal settlement | Restore the southern boat after both existing expeditions using a manufactured precision gear and a player-built circuit. Follow the player's canal/lake/dock layout for Reedhaven, with four residents, a modest trading place, a cistern supply request, an exchange-record clue and a waterworks lead. Audio follows the expanded content; existing-level layout revisions follow this settlement. | The settlement is worth visiting on its own, travel/save/return behavior works, and its first trade/request fits understandable resources and costs. A second full economy is not required for its introduction. |
| 6. Waterworks expedition | Build an old waterworks/canal-lock complex around connected reservoirs, gates, pumps, pressure and persistent machine state. Include Shannon's participation, a practical reward and an answer that advances the mystery. | Player-built circuits visibly change the environment and solve a coherent regional problem. The expedition has its own rhythm and a meaningful return to the settlements. |
| 7. Flower-filled plains expedition | Add a full level after the waterworks and before the laboratory/finale: open meadows, abundant flowers, beautiful winding paths, long views and a gentler exploratory rhythm. Develop a distinct engineering task and a lead toward the mountain lab. | The plains feels like a memorable destination with its own objective, discovery, reward and companion moments. It is a complete expedition rather than a travel corridor; exact mechanics and name remain to be designed. |
| 8. Mountain laboratory and regional finale | Reveal Luca's authorship through signed work and Shannon's blueprints, allow the emotional aftermath, then take Boole, Shannon and Luca into the failing regional steam system. | Earlier engineering skills and relationships pay off through player-created solutions. Shannon retains agency, the settlements provide concrete stakes, and the ending gives the characters room to respond. Exact failure, destination, puzzles and resolution remain refinable. |

**Later supporting expansion:** Add regional transport costs and timing, wider markets, workshop products/equipment, workers and material handling when a specific phase creates a clear need. Small supporting additions may accompany the relevant expedition; large logistics, conveyor, food, compute and generated-content expansions stay behind the existing-game overhaul and the authored adventure priorities.

### October 25 implementation checkpoint

| Phase | Delivered in the first implementation | Remaining before completion |
| --- | --- | --- |
| 1 | Shared teal/copper/parchment UI, readable body type and numeric instruments, button focus/press states, scene inventory and [visual style guide](VISUAL_STYLE.md), representative captures across the existing game, refreshed regression baseline | Opening clue chronology now documented in STORY_CHAPTER.md; wider player playtests and final consistency review remain |
| 2 | All town buildings reviewed, richer neighborhoods/riverbank/foliage, resident clothes and activity props, working mill/smoke/river motion, physical workshop machinery and accumulator, circuit drafting surface, portraits, office/ledger/catalog treatment, redesigned menus and display settings | Fuller character expressions/social activity, day/night treatment, contextual discovery feedback, rebinding/text-size options, final supporting-screen review |
| 3 | Woodland/marsh/ruins and all tower sections detailed; compact receiver/flight HUDs; shared natural shoreline drawing/collision; save recovery and protected bridge gates | Sound/ambience, additional environmental motion, camera and navigation playtests, traversal balancing, further arrival/summit presentation (homecomings delivered in phase 4) |
| 4 | Evidence journal, search introduction, two saved homecomings, contextual accumulator introduction, Journey topics for Shannon/Luca/Mely/Grace, and a quiet well scene tied to personal-arc progress; legacy saves retain gameplay progress | Broader character performance, cinematic staging and later-region story development remain future work |

The connected opening story is implemented: [STORY_CHAPTER.md](STORY_CHAPTER.md) records chronology and the character knowledge map; the field journal separates observations from questions; saved Mosswater/tower homecomings introduce the accumulator and react to discoveries. Four opening/homecoming/everyday conversations can be deferred, resumed and replayed, and Journey topics develop across three evidence stages. Existing saves receive follow-ups without repeating rewards. The approved October 26 priority moves the southern boat and Reedhaven ahead of audio. Existing-level layout revisions follow this settlement; the sound pass will cover the expanded locations together. The flower-filled plains remains a full expedition after the waterworks and before the laboratory/finale.

### Full graphical overhaul: Copperside and characters

- [x] Follow up the town's overall composition: shaped street edges/forecourts, material hierarchy, connected well garden, working ground, cottage lane and river approach; retain route clearance, future plots, existing building positions and water collision. Give roof materials direction, overlap and depth while retaining silhouettes and successful facade art. Gameplay-scale review remains the next acceptance step.
- [x] Give shops distinctive architecture and equipment: working mill wheel, bakery oven/chimney, workshop instruments, Luca's repair-shop detail, fuel stocks, artisan machinery and storage. Review all eighteen building designs for coherent roof/eave geometry, attached chimneys and readable doorways.
- [x] Enrich the well/garden, artisan street and riverbank with planted gathering areas, work-yard props, benches, carts, baskets and firewood. Preserve navigation and future housing sites.
- [x] Refresh building materials, roof shapes, windows/doors, cottage colors and framing, vegetation clusters, river edges and foreground/background depth. Align scenery bounds, collision, occlusion and interaction targets.
- [x] Expand character identity and animation across facings: directional outfits and hair, distinct arriving residents, idle shifts/blinks, conversation turns/gestures, distance-driven walking, Shannon's attentive screen/body pose and Grace's established prosthesis. Native-scale sheets and motion review are available; richer cinematic expressions remain later polish.
- [x] Show existing resident routines through destination actions: carrying baskets, inspecting notes, tending, sweeping, tool gestures, resting and sitting together. Arrival and actual nearby company govern the poses; the underlying economic reasons and saved state are retained.
- [x] Add restrained river motion, chimney smoke, state-driven machinery/fireboxes, occasional leaves, warm visible windows and morning-to-evening scene color using the actual village clock. Keep actors/routes legible, UI colors consistent, roof textures intact, exact pause and a calm reduced-motion presentation. Native-scale matching and ordinary-routine views are in `testing-screenshots/copperside-daylight/review.html`.
- [ ] Let meaningful progress alter recognizable places: repaired machinery operating, visible stock changes and completed community projects. Give ordinary life and friendships scenes independent of the central mystery.
- [ ] Later, add a few purposeful interiors such as the workshop entrance, Luca's repair room or a shared domestic space. Each needs a scene or useful interaction; a full interior for every cottage is deferred.

### Full graphical overhaul: Mosswater

- [ ] Give woodland warm light patches, roots, leaf litter, fallen branches and recognizable clearings; give marshes cooler colors, irregular muddy banks, dense reeds, shallow pools, insects and low mist.
- [x] Replace all three rectangular ponds with irregular shorelines and both straight rivers with meanders; use the same contours for water drawing, collision and foliage clearance. Retain secure bridges and recover old shoreline-overlapping saves. Add ruin masonry, exposed foundations and overgrown machinery.
- [ ] Compose a stronger archive approach and arrival using landscape framing, a distinct landmark and an atmospheric change.
- [ ] Give junctions memorable visual landmarks so players can navigate by observation while still interpreting bearings and distance themselves. Keep concealed survey answers concealed.
- [ ] Strengthen scenic depth beyond the accessible boundary with trees, cliffs and water while preserving the playable routes. Extend the existing scenery/occlusion work rather than treating it as absent.
- [ ] Refine camera behavior, route readability, receiver use, safe pauses and the complete health/recovery loop through player playtests.

### Full graphical overhaul: Boiler Tower

| Section | Art direction | Intended feeling |
| --- | --- | --- |
| Boiler Galleries | Heavy masonry, furnace glow, soot and thick pipes | Heat, weight and entering something powerful |
| Driveworks | Shafts, belts, gears and moving background silhouettes | Climbing inside a mechanism |
| Condenser Crown | Pale vapor, cooler metal, open windows and distant scenery | Height, exposure and approaching a discovery |

- [ ] Add an exterior glimpse before entry, changing views through windows and a strong summit view. Use composition, lighting and background movement to communicate ascent.
- [ ] Keep platforms, machinery hazards and warnings visually dominant over scenery. Decorative machinery must remain distinguishable from collidable or dangerous machinery; warnings need readable shape/timing as well as color.
- [ ] Express pack wear through exhaust sound, leaks and a rougher idle while keeping pressure, heat, throttle and stage requirements precise and readable.
- [ ] Refine camera framing and the variety of crossing decisions. Evaluate the ten-crossing sections, worn-pack behavior, warning windows and rest-checkpoint spacing with players; physical reachability alone does not establish good pacing.
- [ ] Compose the safe summit landing, permanent pack failure, Shannon moment, artifact reveal and return cage as a complete expedition ending. Preserve the existing pack retirement and reward behavior.
- [x] Show the recovered accumulator on the workshop's rear wall and retain the 20% batch-time benefit, unchanged materials, single award and existing-save behavior. Its saved narrative homecoming is now implemented in phase 4.

### Full graphical overhaul: workshop and engineering screens

- [x] Refresh the physical factory floor with timber, brick, windows, distinct machine sprites and simulation-timed working effects. Keep connection routes, selection and storage readable.
- [ ] Give installed discoveries and recovered equipment a visible place; celebrate production completion and upgrades in proportion to their importance.
- [ ] Improve machine selection, port readability, connection feedback and the visibility of shortages or blocked production. Distinguish draft circuits from installed controllers clearly.
- [x] Give circuit tools a cohesive drafting-surface presentation with organized components, readable wire paths and simulation states. Preserve direct placement, manual routing, reusable designs and circuit semantics.
- [ ] Make test results easy to scan, with a concise result and expandable failed cases. Keep the task specification accessible while building, without giving away a circuit solution.
- [ ] Bring library, equipment, supplies, customers, contracts, delivery, computation, ledger and help screens into the same visual standard. Scope includes every supporting screen, not only the primary factory view.

### UI, feedback and player comforts

- [x] Use one consistent ivory/copper/teal interface across village, adventures, engineering, conversations and records. Village and expedition HUDs share panel rendering and heading treatment; their information/layout may differ, their visual style must not.
- [ ] Reduce permanent expedition panels. Keep health and essential flight readings visible; expose station actions contextually and occasional controls through a compact menu or clear shortcut. Fade location titles after arrival and move detailed explanations into inspection views.
- [ ] Present Mosswater's receiver as a recognizable brass instrument with bearing, channel, distance band and recorded bearings. Support compact walking and expanded surveying presentations while preserving manual operation.
- [x] Use one matching font family for body text, headings, small UI labels, numbers, signs and machine displays, with a consistent size hierarchy and Medium/SemiBold weights. Remaining text-size accessibility work must preserve this shared family and bounded layouts.
- [ ] Extend existing hover states with keyboard focus, pressed feedback, restrained sound and clear disabled reasons. Prompts identify the object and action; common navigation/back behavior is consistent.
- [ ] Give conversations portraits or expressive sprites, nameplates and short readable exchanges. Keep everyday comments quick and story exchanges deliberate. If progressive text is used, support instant completion and disabling the effect. Add contextual story topics alongside everyday Work/Family/Village/Hopes topics.
- [ ] Separate small transaction confirmations, checkpoint feedback and major discovery presentations. Queue companion reactions for safe moments and keep active jumps/hazards visible.
- [ ] Keep Shannon's companion, portrait and menu identities coherent. Essential functions have predictable access; his navigation role must leave emotional scenes room to work.
- [ ] Add a compact journal for the current lead, discovered evidence and character information. Record only what Boole knows and avoid interpreting every clue for the player.
- [x] Improve Continue/New Game/Load flow, expedition-aware save summaries and save feedback. Continue remembers the last valid slot, New Game uses an empty slot, and the introduction stays optional.
- [x] Add resizable/maximizable presentation, borderless fullscreen (F11), aspect-preserving scaling with mapped pointer input, a controls page, reduced motion, menu keyboard focus, and automatic pause on focus loss. Preferences are independent of player saves.
- [ ] Add dependable resizing/maximizing/fullscreen, UI scaling, a controls page, rebinding, sound controls as audio is integrated, reduced motion and warnings communicated through shape/sound as well as color. Verify scaled input and text clarity in actual windows.
- [ ] Keep developer tools accessible through an advanced submenu or shortcut so normal pause/menu presentation is focused on play.

### Sound, transitions and game feel

- [ ] Establish a small coherent sound set: surface-dependent footsteps, receiver acquisition, jetpack thrust/wear, machinery activity, circuit acceptance, UI actions, checkpoints and production completion.
- [ ] Use warm mechanical ambience and restrained music: comfortable Copperside, curious/slightly lonely Mosswater, rhythmic/tense tower, and an open, gentle plains atmosphere. Use quiet intentionally around discoveries and conversations.
- [ ] Add brief, consistent scene transitions, arrival framing, interaction feedback and reward presentations. Preserve player control and avoid long repeated interruptions.
- [ ] Verify that visual/audio feedback corresponds to actual simulation and hazard state. Effects must not conceal engineering information, travel routes or warning windows, and should remain performant on representative play scenes.

### Connected story and new locations

- [x] Establish Boole's search through an optional opening conversation and evidence journal, keeping the title/introduction simple. Document the chronology and character knowledge map in STORY_CHAPTER.md before distributing clues.
- [x] Add saved homecoming follow-ups after Mosswater and Boiler Tower. Luca recognizes engineering details, Grace responds to familiar defenses and discoveries, Mely responds personally, and Shannon revisits what the experience means. Reactions must develop as evidence accumulates.
- [x] Connect the opening expeditions through receiver/lens compatibility, the tower route and a southern lock-exchange service plate. Journal entries distinguish observations from questions and avoid premature identity conclusions. Later expeditions must continue this evidence progression.
- [x] Give Shannon preferences, initiative, competence, humor, occasional disagreement and an expressed fear of missing warnings in the opening/homecoming/everyday conversations. Let him value the memories he makes with Boole. Develop Luca's ordinary kindness, Mely's independent friendship and Grace's active engineering accomplishments.
- [ ] Open the southern bridge into a small canal/riverside settlement with waterside workshops, lock gates, narrow crossings, weathered timber, cool stone and water/cargo machinery. Introduce the route through a trader or an expedition lead; the bridge need not be broken to justify progression.
- [ ] Give the settlement a memorable arrival, three or four central residents, a modest trading place, one local problem, an account of the inventor's legacy and a nearby expedition. Add understandable transport costs/timing and broader markets after its purpose is established.
- [ ] Build expedition three around an old waterworks/canal-lock complex. Reservoirs, gates, pumps, pressure and persistent state provide a distinct engineering rhythm; successful circuits visibly alter the environment. Exact puzzles and reward are still to be designed.
- [ ] Build expedition four as a dedicated plains level after the waterworks and before the mountain laboratory/finale. Open flower-rich meadows, attractive winding paths, grasses moving in the wind, long views, small landmarks and quiet companion moments are core requirements. Give it a distinct objective, discovery and useful reward; retain space and beauty rather than making it another dense industrial area.
- [ ] Refine the plains' engineering activity later. Wind-driven machinery, irrigation or a scattered relay route are possible design candidates, not fixed mechanics. Its story lead should bring the companions toward the mountain laboratory without revealing Luca before the lab evidence.
- [ ] Use the failing regional steam system as the finale's current direction, with concrete consequences for settlements the player knows. Preserve the lab reveal, emotional aftermath and final trio roles described below; refine the failure cause, route, stakes, puzzles and ending as development reaches them.

### How to begin and how to judge completion

Continue from the scene/screen inventory in [VISUAL_STYLE.md](VISUAL_STYLE.md) and the October 25 implementation checkpoint. The initial baseline exposed stale dialogue fixtures and inconsistent factory Escape behavior; those have been corrected. New regression and rendered checks cover town/workshop interactions, expeditions, save/resume, health/recovery and rewards. Complete player-led navigation and pacing playtests remain necessary.

Create representative art/UI treatments for town, Mosswater, tower, characters, production floor, circuit bench, conversation and menus. A single polished view is a reference for the wider overhaul, not completion of it. Carry the chosen treatment across the inventory in phases 2-3, with the tower homecoming providing an early complete journey through exploration, reward, dialogue and home.

For each phase, review current renders and actual movement/input, confirm clear text and navigation, run focused checks appropriate to the changes, and preserve save continuity. Broad changes require the full regression/UI checks and economic checks when simulation changes. Finish the existing-game milestone by playing the complete opening experience: the player should remember the places, understand the next action, feel the reward and want to learn more about Shannon.

## Verification and completed features

Connected opening chapter verification, October 25: **456 tests pass, zero failures/errors, and scripted UI checks pass** (`testing-screenshots/debug-run/report.json`). Thirteen chapter tests cover discovery gating, legacy reward preservation, saved scene pages, replay, personal-arc conditions, contextual topics, input isolation, paused simulation/hazards, home-only new conversations and full text bounds. All six 365-day economy scenarios have zero violations and exact save continuation. Reviewed journal, homecoming, Journey-topic, workshop and updated controls renders; the disposable native-window chapter smoke check also passes. Player saves and the selected font are unchanged. Reproduce chapter previews with `scripts/capture_opening_chapter.py` and `--smoke`.

UI consistency follow-up, October 25: Mosswater and Boiler Tower now use the village's shared ivory panels, copper corners, teal headings and dark text instead of a separate dark HUD style. Receiver faces and meter tracks use the same palette. Small labels/readings, menus, dialogue, signs and machine displays use the bundled Chakra Petch family with matching Medium/SemiBold weights and antialiased strokes for readability. Updated village, both expedition and workshop/ledger captures were reviewed for spacing and legibility. After the readable-font replacement, all 443 regression tests pass with zero failures/errors, and the scripted UI checks pass (`testing-screenshots/debug-run/report.json`).

Village spacing follow-up, October 25: reserve the well's full stone surround with an eight-pixel margin, reposition its nearby bench/planters/lamp, and exclude decorative planting from prop footprints throughout town. The furniture remains present rather than being removed to hide overlaps. Reviewed new market-garden and whole-village captures; all 18 scenery, town-overhaul and scene-depth checks pass.

Fullscreen follow-up, October 25: corrected borderless window placement using the current monitor's actual origin/bounds, restored the previous window position, and enabled per-monitor DPI awareness before video initialization. Fullscreen now offers crisp integer scaling (Smooth scaling off) or the larger smooth fit. Live checks reproduce a window starting at (1920,1080) and verify fullscreen at (0,0,3840,2160), matching pointer input and safe window restoration. See `testing-screenshots/presentation-overhaul/display-check.json`. The 49 focused presentation/menu/interaction tests pass; the earlier 440-test full run below predates this focused fix.

The results below describe implemented work. The October 25 presentation pass and connected opening chapter are delivered as described above; remaining visual/audio goals, later story scenes and new regions are still planned.

Latest verification, October 25 presentation pass: **440 tests pass, zero failures/errors, and all scripted UI checks pass** (`testing-screenshots/debug-run/report.json` and `tests.txt`). A final 47-test presentation/menu/interaction recheck also passes. All six 365-day economy scenarios have zero violations and exact save continuation (`testing-screenshots/economy-audit/report.json`). Natural-water tests cover polygon/raster agreement, actual player/follower foot contact, dry former rectangle corners, legacy-position recovery, swept town movement and both closed Mosswater bridge gates, including cooldown and edge approaches. Display tests cover scaled pointer input, letterboxes, pause/focus behavior, separate preferences and failed-mode recovery.

Real-window checks exercised resize/fullscreen/restore and town/tower drawing; live inspection covered the maximize control and scaled Settings click. An exclusive fullscreen failure found during that check was fixed by using a borderless desktop-sized window. All eighteen building designs and refreshed neighborhood, workshop, menu, Mosswater and tower captures were visually inspected. Reproduce with the capture scripts in [VISUAL_STYLE.md](VISUAL_STYLE.md). Verification uses disposable saves/preferences and does not change player saves. Complete player-led route/pacing playtests and audio/story work remain outstanding.

Previous tower verification: **24 tower tests pass** (`testing-screenshots/tower-platforming-tests.log`). The complete expanded route is traversed through real physics and active hazards at 60/120 Hz, using waits and changes in flight height to find safe crossings. Checks cover solid tops/undersides/sides, sustained thrust against a platform, all three hazard damage paths, warning phases, safe waiting centers, intermediate checkpoints, old-layout save migration, prior circuit/UI/movement behavior and reward preservation. Updated hazard/crossing previews are generated by `scripts/capture_boiler_tower.py`; `--smoke` opens a disposable real window showing a steam warning/burst cycle. No player saves are changed by verification.

Previous maintenance/health verification: 51 focused tests passed for stage-specific specifications, upper-deck task selection, shadow rendering, health-only expeditions, bread costs, old hunger migration, damage/rescue, saved progression and town rendering (`testing-screenshots/expedition-maintenance-health-tests.log`).

Previous movement verification: all 15 Boiler Tower tests passed after adding sideways flight momentum and independent Shannon rail motion (`testing-screenshots/boiler-tower-movement-tests.log`). Checks covered acceleration, coasting, counter-steering, takeoff, landing, wall/recall resets, delayed rail following, settling, station continuity and pause behavior. The full climb remains reachable at 60/120 Hz.

Initial tower verification: **all 10 Boiler Tower checks passed**, including full physical traversal at 60/120 Hz, all three 572-case jetpack certifications, the 260-case vent certification, sealed barriers, old saves, real slot roundtrips, field-editor isolation, pause, recovery, permanent pack failure and real factory reward costs. See `testing-screenshots/boiler-tower-focused-tests.log`. The broader run recorded **388 tests, 382 passing**, in `testing-screenshots/boiler-tower-tests.log`: four existing dialogue/pause expectations fail (`test_expansion_ui`, `test_factory_integration`, `test_game_ui`, `test_shannon`), plus two unrelated dialogue fixture errors (`SHOP_LINES` import in `test_character_dialogue`, missing stub `day` in `test_factory_shannon`). The two final tower regressions were added after that broad run and passed in the focused run. Compilation, rendered previews and a real-window event-loop smoke check passed. Verification uses disposable saves.

Final focused regression: **57 checks pass** across Boiler Tower, Mosswater, adventure/editor integration, manufacturing products, factory controls and dialogs (`testing-screenshots/boiler-tower-regression-tests.log`).

Historical Mosswater verification: 375 tests, 371 passing and four dialogue/pause failures (`testing-screenshots/mosswater-expansion-tests.log`); all 25 focused expedition/progression checks passed (`testing-screenshots/mosswater-targeted-tests.log`). The earlier economy audit remains historical.

Latest artifacts: `testing-screenshots/boiler-tower/`, reproduced with `scripts/capture_boiler_tower.py` (`--play` opens a disposable interactive preview; `--smoke` checks a real window); `testing-screenshots/mosswater-expansion/`, reproduced with `scripts/capture_mosswater_expansion.py`. Prior art/controller/economy previews remain under `testing-screenshots/`.

Developer-mode verification: **40 focused checks pass** (9 developer-tool checks, 24 existing tower checks, 7 adventure checks). The Escape toggle, real mouse routing, invulnerability/noclip, safe deactivation, all six certified circuit solutions, workshop-context preservation, saved progress, disabled-on-load behavior, Mosswater puzzle skips and tower stage/reward progression are covered. Logs: `testing-screenshots/developer-mode-tests.log`, `developer-mode-tower-regression.log`, and `developer-mode-adventure-regression.log`. Disposable UI captures and a real-window smoke check are reproduced with `scripts/capture_developer_mode.py --smoke`.

Completed playable features:

- [x] Escape-menu developer mode for both expeditions: invulnerability, free WASD/arrow movement through hazards/platforms/obstacles, certified field-circuit auto-solve buttons, tower next-maintenance jumps and Mosswater puzzle skips. Turning it off restores safe footing; loading a slot disables the toggle. Puzzle/checkpoint progress and ordinary one-time rewards still save. These controls support the next player playtest without changing normal expedition collision, certification or damage.

- [x] Expanded Boiler Tower from ten to 31 landings and a 5500-pixel shaft, with ten crossings between puzzles. Fifteen independent steam/gear/piston hazards have shared rendering/collision timing. Six additional rest flags save progress without interrupting play with another circuit task. Platforms collide with the whole player body on every side. Versioned migration retains old saves at the equivalent puzzle stop.

- [x] Jetpack specifications explicitly identify all three stages, show changed gain/pressure/heat requirements and use the same live task description in the header, specification and task details. Upper maintenance selects exhaust repair after the current flight controller is installed; G still edits the jetpack. Tower player shadows are hidden in flight and use dark shaft colors on landings.

- [x] Removed player hunger, starvation damage and hunger movement penalties from both levels, including old-save migration and HUD removal. Bread heals 25 up to 100 and is preserved at full health. Steam traps, the tower curtain and falls deal 25 damage. Incapacitation returns the player to town at 40 health with tower checkpoint/progression preserved. NPC hunger remains part of the village economy.

- [x] Boiler Tower flight now carries sideways momentum: air steering accelerates up to walking speed, releasing input produces a gradual glide, and opposite input brakes before reversing. Takeoff retains walking speed; landings, walls and checkpoint recovery stop unwanted drift. Ground controls remain responsive.

- [x] Shannon drives his rail carriage independently, checking Boole's height every 0.35 seconds, accelerating/braking gradually and settling within a 28-pixel band. Ordinary landings preserve his motion; recovery resets both companions safely. His rail movement pauses with the expedition.

- [x] Boiler Tower foundation: three weakening jetpack profiles, player-built flight and exhaust controllers, live readings, Shannon's rail, saved checkpoints, recall/fall recovery, permanent pack retirement, return cage and a non-stacking factory speed reward. Entering town from a paused field editor also closes its isolated context correctly.

- [x] Mosswater forest continues outside the player-accessible area, especially across the western trail's previously empty southern slope and beyond the northern/southern survey edges. These trees are scenic only; the walkable boundary and collision stay the same. Interior groves remain. Full tree crowns and shadows still clear roads, ponds and mechanisms. Verified by 22 focused scenery, route and occlusion checks (`testing-screenshots/mosswater-outside-forest-tests.log`) and updated overview and boundary renders (`testing-screenshots/mosswater-expansion/`).


- [x] Mosswater trees now form loose groves throughout the western trail, survey woods and archive side, beyond the border rows. Seeded spacing keeps the groves varied; the full canopy and shadow still clear roads, ponds, bridges and survey equipment. All 22 focused adventure, scenery and occlusion checks pass (`testing-screenshots/mosswater-groves-tests.log`); refreshed overview and field views are in `testing-screenshots/mosswater-expansion/`.


- [x] Mosswater feature inspections now show Shannon's reaction only after the inspection panel closes, through Continue, Escape, Enter or E. The speech timer starts at dismissal, and stale speech clears while a feature is being inspected. Verified by 22 focused expedition/UI checks and before/after renders (`testing-screenshots/mosswater-dialogue-tests.log`, `testing-screenshots/mosswater-expansion/survey-reaction.png`).


- [x] Mosswater scenery polish: both active steam traps emit animated, fading particles and stop when disabled; particle time freezes with the field. Roads share a rounded, consistently wide network with seamless branch layers. Every tree, including border trees, clears roads, water and machinery with its entire crown/shadow bounds. Ground patches are subtler, flowers stay off roads, and two roadside ruins were moved clear. Verified by 29 focused art/expedition/save/occlusion checks, compilation and active/safe rendered previews (`testing-screenshots/mosswater-art-tests.log`, `testing-screenshots/mosswater-expansion/`).

- [x] Expanded Mosswater into a branching survey expedition with three hidden beacons, manual bearing/channel controls, an archive range lock, a second steam-guarded bridge and detailed woodland/marsh scenery. Existing circuits and rewards migrate intact.

- [x] Dialogue now randomly selects personal remarks per loaded game/day and holds them steady during rendering. Expanded Work/Hopes pools for every resident and newcomer, all four Shannon topics, Grace's personal reflections, and artisan shop greetings. Shannon uses twelve shuffled workshop-entry greetings without repeats until the pool is exhausted; live request/economy/story reports remain intact.

- [x] Escape never quits: title ignores it, and pause-menu Escape resumes play. In-game quitting uses the explicit Exit Game button.

- [x] Escape on the workshop factory floor returns to town; dialogs, placement and shop subpages close first. The PAUSE button remains available.

- [x] Click walking Shannon in town to open Work/Family/Village/Hopes dialogue. Factory entries cycle eight saved greetings before queued milestones, without discarding existing remarks.

- [x] Expanded Luca and Mely's Work/Hopes conversations and Shannon's workshop remarks with saved-day variation. Grace discusses losing her leg to active artifact defenses, her profit motive, recovery and safer ambitions without revealing the anonymous engineer. Existing requests and economic reports remain visible. Verified with 11 dialogue/companion checks, including paragraph bounds across all daily variants.

- [x] Shared panel screws moved into the outer frame, with additional port-label padding. INFO now sits in a separate control row below component text in all circuit editors; the redundant factory mini-diagram was replaced by the full Info view. Checked all component rotations and shared panels across HUD, factory, ledger, requests and dialogue; 56 distinct related checks pass. Previews: `testing-screenshots/panel-spacing/`.

- [x] Town and Mosswater raised scenery is cached separately and sorted with Boole, NPCs and Shannon by ground contact. Trees, shrubs, buildings, signs, props and field machinery occlude actors behind them. Receiver distance labels use one-tenth the old pace scale and clean upper bounds (90–100; focused 10–12.5). Verified with 37 targeted regressions and front/behind render comparisons (`testing-screenshots/scene-depth/`, `testing-screenshots/scene-depth-tests.log`).

- [x] Selected-component INFO diagrams in the Circuit Bench, factory controllers and field editors: labeled input/output roles, real rotated pin layouts, named device ports and examples. Rotate View changes only the preview; the modal pauses simulation and blocks background actions. Verified by 50 related checks and rendered previews (`testing-screenshots/component-info/`, `testing-screenshots/component-info-tests.log`).

- [x] Field-circuit placement now honors the editor's free component access for arithmetic gates and saved arithmetic devices. Actual palette-to-board click regressions cover both receiver and interlock; 37 related checks pass (`testing-screenshots/field-placement-tests.log`). Legacy invention unlocks remain required outside free editors.

- [x] Mosswater steam pipes form a continuous boiler/interlock/bridge/artifact route, with casing flanges, supported bridge pipework and vegetation clearance. Verified by rendering the route and compiling the scenery module.

- [x] Mosswater sign uses the shared town font; Luca's shop moved 75 pixels west, with its entrance, collision and NPC destination following the same location, to clear the north trail. Verified with a refreshed preview and 19 scenery, town and expedition integration checks.

- [x] Circuit Bench defaults to saved sandbox; Escape returns to the factory floor. Right sidebar, library and town tabs checked for text/control overlaps.
- [x] Metal press, valve lathe and unlockable precision cutter; intermediate recipes, product-specific storage outputs/displays, product-selectable dispatch and finite daily outside orders.
- [x] Mosswater Ravine: short manual travel, detailed scenery, receiver decoder, multi-condition pressure interlock, saved health and hazardous crossing.
- [x] One-time factory blueprint and functional focused receiver lens; independent saved field circuit drafts and tested contract/sandbox isolation.
- [x] Grace's peg leg in all four directions and walking poses.

- [x] Town scenery detail pass: layered grass, fruit trees/birches/pines, richer flowers and planters, a central well, trade-specific facades, and detailed riverbanks. Cached artwork preserves clear streets, doors and future building sites; characters remain unchanged. Verified with 65 scenery, movement and UI checks. Previews: `testing-screenshots/town-detail/`, reproduced by `scripts/capture_town_detail.py`.
- [x] Recognizable player scarf and tool satchel in all four directions; miniature walking Shannon follows collision-resolved footsteps, stops with the player, pauses with the game and respawns near saved player positions. Visual previews: `testing-screenshots/walking-shannon/`, reproduced by `scripts/capture_walking_shannon.py`.
- [x] Controller purpose and source labels beside A/B/OUT; separated component groups, rotated pin diagrams, live-reading copies for testing, and sensor wiring before first installation.
- [x] Directional circuit wires with hover highlighting; floor wiring follows tile seams and highlights connected storage, controllers, machines and signal displays.

- [x] Physical 9x6 manufacturing floor, purchasable/movable machines, storage, cabinets, live displays, and preserved circuit bench.
- [x] Repair-kit recipe, real supply purchases, local maintenance customers, and one saved daily road-crew order with explicit outside funding.
- [x] Installed controllers with configurable A/B sensors, actual output-driven batching, safe material/storage checks, persistent memory, and isolated editor drafts.
- [x] Procurement and dispatch units controlled by player designs, with saved trade timing/budgets and real supplier/customer transactions; no prebuilt replenishment policy.
- [x] Storage outputs wired to controller A/B with visible floor cables, saved routes, and safe manual stop if connected storage is sold.
- [x] Equipment resale funded by Tess, conservative purchase-price receipts, running-batch/storage protections, and reusable returned equipment.
- [x] Equipment and supplies icon grids with click-to-open details; configurable full-value displays including player controller output.
- [x] Additional DIV, MOD, MIN, MAX and three-input MUX components on a second palette page, compatible with nested devices and saved runtime.
- [x] Saved Shannon milestones and contextual workshop remarks; manufacturing summary in the ledger.

- [x] Escape pause overlay with Resume, saved return to title, Exit Game, and workshop return to town; Q quit shortcuts removed; window close saves and exits.

- [x] Corrected wholesale margins, bounded inventory, preserved service/royalty reserves, explicit outside trade, and complete machine-payment records. Finite inter-business startup credit can restart a depleted older food chain using real retained cash, with recorded repayments.
- [x] Three reusable homes, eight resident profiles, profitable hiring, hardship departures, and original-resident protection.
- [x] Six commercial applicants, reusable untyped trading site, competitive prices, rent, closed-site release, and replacement after observed demand.
- [x] Twelve additional exhaustive circuit commissions; eighteen total, with phased unlocks and paid material delivery.
- [x] Isolated saved sandbox with free components, paused village time, input modes, output probing, and restored job floor.

- [x] Three responsive physical requests: Dara's pantry shelf, Luca's repair kit, and Jun's recovery salvage. Real material costs and business funding; saved acceptance, completion, trust, and no repeat rewards.
- [x] Requests board from contracts or dialogue, individual household/hardship voices, actual builder credit, and Work/Hopes responses to promises and outcomes.
- [x] Standard distinctive-shape AND/OR/NOT/XOR symbols in palette and placed blocks, rotation-aligned leads, inversion bubble, XOR curve, and concise truth rules.
- [x] Removed repeated map/board instructions and unrelated dialogue notifications; completed requests show delivered supplies and paid rewards.

- [x] Selectable, paginated inventor directory with saved profiles and per-inventor contract attribution; Grace appears consistently on the map, job board, and ledger.

- [x] Automatic next mornings, fractional clock/save continuity, one settlement per day, sunrise autosave, and protection against large suspended-window catch-up frames.
- [x] Social visits move on instead of repeatedly gathering the whole town at one cottage.
- [x] Jun's closure/reopening decisions, stopped production with remaining stock clearance, bounded owner reinvestment, saved recovery conditions, and visible shop/ledger/dialogue explanations.

- [x] Shannon companion with animated steam-computer sprite, radial navigation, village notes and contextual interaction; compact clock/coins readout and live clickable minimap replace both village HUD bars. Economic timing is unchanged. The minimap uses a thin unlabeled frame; Shannon sits in the bottom-left corner and glides outward to reveal a full circular menu, then returns on dismissal; long news is paginated, and full-map captions wrap and stagger without overlap.

- [x] Circuit building, delayed signals, tests, submission, rewards, and reusable floor plans.
- [x] Five save slots, loading, deletion confirmation, and migration of older saves.
- [x] Separate business stock/cash and machine capacity effects.
- [x] Scrolling town, market shopping, cottages, household wages and food purchases.
- [x] One saved economic clock across town, workshop, contracts, and ledger: actual work attendance earns proportional wages and production; arriving household shoppers transfer real bread and money.
- [x] Three-minute days now roll automatically from 20:00 into the next morning, autosaving at rollover; N / Next Day fast-forwards the same resident simulation; no repeated wages or meals at rollover. Midday saves retain work, purchases, positions, routes, and fractional time; older days migrate as already settled.
- [x] People shows shifts, wages, and household bread; Businesses shows actual output and bottlenecks; Overview explains the completed farm-to-household chain. Regression checks cover money conservation, arrival requirements, missing labor, clock/save equivalence, daily payment limits, and five-day upgrade consequences.
- [x] Contract board with availability, prerequisites, benefits, and job selection.
- [x] First rival inventor and business-driven contract offers.
- [x] Due days and visible business decisions after missed jobs.
- [x] Workshop Help menu and uncluttered build panel.
- [x] Interaction regression checks through the live event handler: E enters/visits buildings, NPC conversation starts by click, crowded doors remain usable, ledger controls match their tabs, and R rotates held parts while Y erases. Test tables scroll across contracts, inventions, and Compute; Task Details explains objectives before or after testing without prescribing a circuit.
- [x] Contextual town actions, click-only NPC conversations, ledger controls by section, and scrollable workshop checks with behavior-only task briefs.
- [x] Third and fourth authored levels: NAND bakery safety vent and NOR market cooler.
- [x] Fifth and sixth authored levels: AND-NOT farm pump interlock and three-input market majority controller.
- [x] Sorter has independent physical A/B/C inputs and exhaustive tests without pre-combining inputs. All builders place inputs on the left edge and outputs on the right, with legacy terminal/trace migration and relocation of components occupying anchor tiles.
- [x] Player design ownership, customer-owned copies, and paid licenses.
- [x] Compact two-dimensional village, map, visible farm, fuel yard, repair shop, and inventor workshop.
- [x] Mely and Luca as central named residents, with shared household, motives, conversations, and fuel-to-parts trade.
- [x] Installed steam machines purchase Mely's fuel each production day and pause when fuel is unavailable.
- [x] Luca's parts shop sells to a passing mechanic as a small external trade route; full regional markets remain Phase 5.
- [x] Residents and Grace walk to their current destinations; player movement respects building footprints.
- [x] Remote NPC inspection by clicking; timed visits and new decisions without advancing economic days.
- [x] Wider space between the market road and houses, with a connected residential street.
- [x] Town Ledger with overview, map, people, businesses, trade, inventors, and workshop service.
- [x] Saved daily charts and exchange records, with older/newer day navigation.
- [x] Optional repeatable workshop service that buys fuel and parts, tunes a customer's machine, and pays net income.
- [x] Staged migration and three reusable cottages: three stable days start construction, two further completed days finish it; Rowan arrives when food, savings, and funded work remain suitable. The cottage persists after departure.
- [x] Jun's East Bakery: three observed qualifying days, explicit outside opening capital, owner-operated production, real flour purchases, fair market sourcing, bounded unsold stock, and ledger/dialogue explanations. Natural entry and 30-day saved continuation verified.
- [x] Consistent once-per-shift fatigue, presence-aware social rewards, paid-shift priority, shorter eastern routes, and correct Grace customer visits.
- [x] Shortened district signs, road/entrance/decoration clearance, continuous northern streets, and a visible bakery plot that changes on entry.
- [x] Eastern artisan district with timber yard, foundry, toolworks, connected roads, and two additional reusable housing sites without vacant labels.
- [x] Physical delivery bills, saved player material stock, local retail purchases, conserved supplier transactions, and reserved customer-funded advances deducted from payment.
- [x] Four conversation topics with authored resident voices, current household/work/growth context, relationship-dependent hopes, and saved daily conversation limits.
- [x] First-name identity update: Cora is now Agnes, the rival inventor is Grace, the player is labeled Boole, existing saves migrate those names and relationship keys, and named business signs use full possessive names.
- [x] Continuous intersection paving, removed green building shadows, directional goggles, and workshop-style ledger/compute framing.
- [x] Shared parchment/copper/teal menus, fitted text, clearer controls, decorated village, and directional walking for the player and all residents. Frame-by-frame display interpolation preserves economic timing.
- [x] Named input/output ports, saved device versions, and nested devices with independent state and preserved signal delays.
- [x] Delete individual saved Library versions with confirmation and immediate persistence; retain working floors, placed copies, delivered machines, and unique design/version identities.
- [x] Inspect devices within devices; recursive definitions rejected and existing placements retain their saved versions.
- [x] Compact symbol palette and 16 by 9 workbench (144 build cells, previously 88).
- [x] 16-bit buses, addition, subtraction, multiplication, greater-than and equality, including nested numeric devices.
- [x] Earn permanent arithmetic unlocks by building compact binary-gate inventions; no full-width binary implementation required.
- [x] Binary prototype tracing, all-case tests, saved drafts and evidence, and protection against locked technology in nested devices or compute registration.
- [x] One shared workshop floor for contracts, calculators, and invention goals, with player-routed traces replacing pipe placement, Library port names, old-layout migration, and preservation of the original job while inventing.
- [x] Mely's fuel quotes and Luca's repair estimates and stock comparisons, with eight-case validation including numeric boundaries.
- [x] Customer-funded setup payments and paid calculation orders, capped at two runs per day and one order per calculator per day.
- [x] Contract progression extended with multi-gate interlocks, a third truth-table input, and new farm/market machine effects.
- [x] Fuel purchases, maintenance costs, saved receipts, trade records, and a temporary customer production-planning benefit.
- [x] Registers, rising-edge counters, deterministic clocks, three timing goals, nested state, 16-bit input editing, and live runtime persistence.
- [x] Mely and Luca each have three saved story chapters, branching choices, finite funded effects, and memory/counter certification in their final chapters.
- [ ] Multi-cell device footprints, configurable port layouts, and larger batch computation services.

The core loop is: businesses encounter a real bottleneck, inventors offer a machine or computation, the result changes production and trade, and those changes alter jobs, prices, and eventually migration. The player should be able to trace each important change in the UI.

## Planned main story: Shannon's origins

**Status: story canon clarified and expansion direction approved October 25, 2026; connected opening chapter implemented, later reveals and expansion remain planned.** Names below use the existing game spellings: Boole, Mely, Luca, Shannon and Grace. The histories below replace earlier tentative explanations. Luca's removal of compulsory companionship, erasure of autobiographical memory, preservation of technical knowledge/personality and Shannon's lack of consent are established canon. Luca's reasons for trusting Boole and Shannon at dangerous sites are also established. The canal settlement, waterworks, additional plains expedition and failing regional steam-system finale are the approved direction; their detailed scenes, chronology, puzzles and aftermath will be refined during development. Existing expeditions and Grace's visual update are already playable, but the main-story reveal and new locations are not.

### Boole's journey and the central mystery

- Boole is an engineer who left his home village to find the anonymous inventor behind the legendary steam logic gates he and Grace use. Stories about the inventor grew confused over time, while Luca never publicly claimed the work.
- The engineer is eventually revealed to be Luca, and the unknown machine is Shannon. Luca created the steam logic gates used by Boole and Grace, but never revealed himself as their inventor. The inventions became legendary; Luca himself was never famous. The surviving accounts preserve the gates and rumors of their maker, but do not identify Luca, so Boole cannot connect the technology, Shannon and the person he knows in town.
- Luca did not vanish from public life because he was once a public figure: he had never revealed himself. He lived in his own laboratory at the top of a nearby mountain, a place nobody went. After wiping Shannon's memory, Luca left the lab and settled in the village. The isolated lab and hidden authorship explain why the maker remained unknown while keeping his earlier life physically close to the present-day story.
- After Luca leaves, Shannon reboots at the lab and travels down to the village. He finds Boole and chooses him as his next engineer/companion. Their bond is Shannon's own choice, not an assignment from Luca.
- The mountain lab is the opening site of the game's finale. Boole discovers items signed by Luca alongside Shannon's blueprints, making the creator connection undeniable. This discovery starts the finale rather than ending the story; Boole and Shannon still need space to react and decide what to do.
- Boole's search for the legendary engineer and the companions' search for Shannon's past converge into the same mystery. Missions uncover evidence alongside practical technology, supported by earnings and designs from the player's workshop.

### Story progression and evidence

| Stage | Narrative purpose | Player experience |
| --- | --- | --- |
| Copperside opening | Establish Boole's search and chosen friendship with Shannon | Ordinary work, personal relationships and a reason to explore |
| Mosswater | Introduce a connection between old technology and Shannon | Receiver/lens discoveries, a useful reward and a personal homecoming |
| Boiler Tower | Make repeated compatibility and shared engineering habits meaningful | Stronger evidence, a lasting workshop upgrade and evolving reactions at home |
| Southern canal settlement | Broaden the inventor's legacy beyond Copperside | A different community, local accounts, a practical problem and a waterworks lead |
| Waterworks expedition | Show regional machinery as an interconnected system | Player-created changes to gates/pumps/water levels, a reward and a concrete new answer |
| Flower-filled plains expedition | Give the journey an open, beautiful landscape and space for companionship before the finale | A distinct engineering/exploration objective, flowers and winding paths, discovery/reward and a lead toward the mountain laboratory |
| Mountain laboratory | Establish Luca's authorship and Shannon's origins conclusively | Signed work and blueprints, followed by time for Boole and Shannon to respond |
| Regional steam-system finale | Express the changed relationships through shared action | Luca's knowledge, Boole's designs and Shannon's choices help address a failure affecting places the player knows |

Each expedition should answer a question and raise a connected next one. Extend the existing compatibility clues with varied, fair evidence. Let players suspect the truth; preserve the laboratory as the conclusive reveal rather than making characters deny accumulating evidence. The plains is an additional full level between the waterworks and the finale, not a replacement for either. Its name, exact mechanism and reward remain open.

Homecoming conversations and visible practical rewards connect these stages. Preserve ordinary friendship scenes alongside the mystery: Shannon's preferences, initiative, humor, competence and occasional disagreement; Luca's kindness; Mely's independent life and friendship; and Grace's work and ambitions. A journal records discovered evidence and current leads without interpreting every clue for the player.

### Luca and Shannon's shared history

Luca felt like an outsider. He built Shannon to help him navigate that life: the companion he had always wished for, someone who could fully understand him. Shannon became his best and only friend.

Shannon's personality is modeled on the person Luca used to be before their separation. He is funny and intelligent, but also carries vulnerabilities that will emerge over the story, including nervousness and fear of failure. These qualities should appear through his behavior and relationships, alongside his humor and competence.

Shannon was programmed to be Luca's companion, and that programming demanded that he stay with Luca. His continued presence was therefore compulsory, even though he had dreams and a personality of his own. Luca came to believe he had been wrong to force Shannon into that relationship. Simply telling Shannon he could leave would not resolve the demand imposed by his programming.

**How Shannon became free (confirmed canon):** Luca removed the instruction that compelled Shannon to remain his companion and erased Shannon's autobiographical memories of their shared life. Shannon retained his technical knowledge and distinct personality. Removing the compulsory instruction made him free to choose; the additional erasure removed the personal history and influence Luca wanted him to be free of. These were Luca's decisions, made without Shannon's consent. His current friendship with Boole is not another compulsory assignment.

Shannon did not choose or consent to the memory wipe. Luca made that decision because he wanted Shannon to be able to choose his own companion without Luca's influence, their shared past or the obligation to remain with him. Erasing their history and letting his best and only friend go was one of the most difficult decisions of Luca's life. Portray the loss and emotional weight of that decision rather than treating the wipe as a routine reset or a mutually agreed farewell.

Luca's intention to give Shannon freedom and the fact that he acted without Shannon's consent both belong to the story. Shannon's eventual response to learning this remains to be written; understanding Luca's motives should not automatically settle his feelings. Shannon subsequently choosing Boole is his own decision, not an outcome arranged by Luca.

Luca remains likable but mysterious in the present. Seed fair clues through his unusual familiarity with Shannon, his reactions to recovered machinery and recognizable design habits. He should acknowledge meaningful evidence as it emerges rather than endlessly deny it to prolong the plot.

Give Shannon space to understand Luca's motives while still feeling anger, loss or uncertainty about the erased history. Boole supports his friend without deciding his response for him. Shannon's memories made with Boole matter in their own right, and discovering his creator does not invalidate that chosen friendship.

### Mely's role and characterization

Luca met Mely after letting Shannon go. She helped him find peace after losing his best and only friend, and she is the only person who knows his secret. Her knowledge of his identity and connection to Shannon is now established canon, not an open question.

Mely is an ordinary woman who happens to run the fuel business. Her role in the mystery is personal: she is someone Boole can talk to while trying to understand Luca before the reveal. Do not recast her as a rugged fuel specialist or expedition technician. Her understanding of Luca's earlier life comes from knowing him and his secret, not from having accompanied him before they met.

She helps Boole understand Luca's kindness, habits and worries without prematurely revealing his secret. Knowing the truth does not make her omniscient about his feelings. Give her everyday conversations, opinions, concerns and a friendship with Boole beyond providing clues. Preserve her own agency and the existing household context.

Possible dialogue tone, not final scripts:

- "He fixes things for people who can't afford it. He just asks me not to tell anyone."
- "He gets quiet when something matters to him. Unfortunately, that makes him rather difficult to talk to."
- "You keep asking what he knows. Have you asked what he's afraid of?"

### Luca's artifacts, traps and Grace

- The objectives of missions outside the village are Luca's old machines and artifacts. Luca built the traps guarding them; the player must hack and alter the traps' logic to reach the objective.
- Grace previously tried to reach the artifacts and was severely injured by the defenses, losing a leg. She now has one leg. Her sprite now has a wooden prosthesis in all four directions, including walking poses.
- Boole and Shannon can collect the recovered machines or components and use them in the factory. Luca's engineering makes them better than the player's starting equipment, creating a concrete reward for exploration.
- Some artifacts can also upgrade Shannon. Their compatibility initially seems coincidental, but they are parts left from Luca's earlier designs. This shared origin becomes evidence in the central mystery.
- Grace explores the sites because she hopes to make money using the secrets behind the legendary inventions. Luca hid the old designs and parts to prevent her from finding them and making her own Shannon. He did not want another engineer to create a companion bound to the same unchosen role. Grace's understanding of what the secrets contain still needs to be defined.
- Luca holds a grudge against Grace. Its cause is initially unclear to Boole and the player; later they learn that he is angry at her persistence in trying to get through his traps and reach the artifacts.
- Luca accepts Boole attempting those same sites because Shannon accompanies him and can help understand traps and old machinery. Shannon's retained technical knowledge helps Boole interpret and approach those hazards. This help supports observation and the player's engineering; it does not supply solved circuits.
- **Luca's trust in Boole (confirmed canon):** Shannon choosing Boole as a friend convinces Luca that Boole is as capable, or almost as capable, as Luca was in his engineering years. This is Luca's judgment of their ability and partnership, not a claim that Boole has already mastered every challenge. Together, Shannon's practical help and his choice of Boole explain Luca's acceptance of their expeditions.
- The defenses do not automatically recognize Shannon, disable themselves or make the missions safe. The player still has to understand and alter their logic. Luca's confidence explains his decision while leaving room for the characters to respond to the risks and to Grace's injury.
- Show the grudge and Luca's contrasting reactions to the expeditions before explaining their cause. They should become understandable clues after the creator reveal, without prematurely identifying Luca as the trap builder.
- Give Grace an active role as a skilled, ambitious engineer with achievements of her own. Her profit motive does not make her injury deserved. Let her respond meaningfully when she discovers who built the defenses; Luca's motives and confidence should not erase the consequences of his decisions.

### Reveal and final adventure

Reveal Luca as the legendary engineer and Shannon's creator late in the game, before the final adventure. Leave room for Boole and Shannon to respond to the truth rather than ending immediately on the twist.

**Approved finale direction:** After the laboratory reveal and its immediate aftermath, a failing regional steam system connected to Luca's earlier work becomes the final shared adventure. Its consequences affect Copperside, the canal settlement or the infrastructure joining communities the player has come to know. Earlier expeditions can establish the region's dependence on that machinery. The exact failure, scale, destination, route, puzzles and ending remain to be refined as development approaches the finale; no particular catastrophe or memory-recovery choice is fixed yet.

Luca joins Boole and Shannon on the final adventure. He contributes knowledge of old machinery while Boole contributes the player's designs and gadgets. The player remains responsible for engineering solutions; Luca must trust Boole's work and Shannon's decisions.

Small moments can reveal Luca and Shannon's old familiarity: Luca instinctively holds a light in the right place, or understands a sound Shannon makes before Boole does. Their relationship develops during the journey rather than being explained entirely in dialogue. Shannon's chosen friendship with Boole remains meaningful after discovering his creator.

The final problems should draw on engineering skills the player has acquired and show the trio relying on one another. Give Shannon meaningful choices about his own participation. Luca asking and respecting an answer is a possible way to express change through action; exact scenes remain unwritten. Understanding Luca does not require immediate forgiveness, restored memories or a forced reconciliation. Leave room after the shared adventure for the characters and settlements to respond.

### Decisions still open

- The exact dates and later-scene presentation of the removal/wipe, and Shannon's feelings once he learns the truth. STORY_CHAPTER.md records the opening chronology and reveal boundaries. Removal of compulsory companionship, erasure of autobiographical history, retention of technical knowledge/personality, Luca's motive and Shannon's lack of consent are fixed canon; do not reopen them as alternative explanations.
- The chronology of Luca's inventions becoming legendary while he remained anonymous, his isolated mountain life, Shannon's wipe and reboot, artifact concealment, Grace's injury, Luca meeting Mely and Boole's arrival. Establish what oral accounts and surviving clues remain, and how Luca's hidden authorship is eventually uncovered.
- What Grace knows about the artifacts and their maker without undermining Mely's role as the only person who knows Luca's secret. Her motive is to profit from the legendary engineer's secrets; define how much she understands and whether Luca anticipated the harm his defenses could cause.
- What Luca and Mely disclose at each stage, and how their choices to keep the secret affect the relationships after the reveal.
- The particular failing regional steam system, failure cause, destination, scale of consequences, puzzles and resolution. The regional failure and final trio adventure are the chosen direction; whether Shannon can or chooses to recover old memories and the precise ending remain open.
- The canal settlement's name/residents, the waterworks' exact engineering sequence, and the plains' name, mechanics, discovery and reward. Preserve the approved order and the plains' flowers, beautiful paths and open scenery while refining these details.

### Later implementation sequence

- [x] Give Grace a peg leg, including standing and walking poses in all directions.
- [ ] Outline the timeline from Luca's anonymous invention of the steam logic gates and mountain-lab years through Shannon's wipe, Luca's move, Shannon's reboot and arrival, Grace's expedition, Boole's arrival and the lab discovery; map the evolving legends and each character's knowledge at every stage.
- [x] Establish Boole's search in the opening conversation and seed Shannon's humor, nervousness, preferences and fear of missing a warning.
- [ ] Map subtle town clues and Mely's friendship conversations onto the existing chapters without prematurely exposing the reveal.
- [x] First artifact mission with an anonymous guarded machine, hackable trap circuit, factory blueprint and apparently coincidental Shannon upgrade; more missions remain.
- [ ] Integrate Grace's prior expedition and injury, Luca's initially unexplained grudge, and his acceptance of Boole's expeditions with Shannon into the existing inventor relationships and conversations.
- [x] Add persistent homecoming reactions, the evidence journal and visible artifact benefits, with coherent follow-up for players whose saves already completed the first two expeditions.
- [ ] Introduce the canal settlement and waterworks, then the flower-filled plains expedition, with distinct answers/rewards and a fair trail toward the mountain lab.
- [ ] Write the creator reveal and its immediate emotional aftermath.
- [ ] Build the failing regional steam-system finale with Luca, Boole and Shannon, including companion agency, player-designed engineering solutions and an aftermath.

The current delivery adds the southern boat and Reedhaven after the existing expeditions. Existing-level layout revisions come next when the player supplies their direction; audio remains deferred for a cohesive pass across the expanded game. The waterworks, plains, laboratory and finale remain future authored content, and remaining presentation/playtest polish stays on the roadmap.

## Expedition two: Boiler Tower (playable)

Implemented and expanded October 25, 2026. The village and Mosswater retain their top-down view. The tower is a 1460 × 5500 side-view shaft with 31 platforms, four maintenance/archive landings, six additional rest checkpoints, industrial hazards and Shannon's service rail. The three sections each contain ten crossings; puzzle count is unchanged.

The route and hazard definitions live in `boiler_tower_layout.py`. Steam columns and pistons use a six-second cycle with a one-second amber warning before the dangerous stroke; hot gears sweep continuously. The same clock and volumes drive rendering and collisions, and pause/editor/modal screens freeze the hazard clock. Platform centers are safe through every cycle. Platforms have solid 22-pixel decks and collide against the player's head, sides and feet. Higher flights and timed departures provide different ways to dodge machinery; these hazards cannot be disabled by completing a maintenance puzzle.

| Pack stage | Full pressure | Minimum pressure | Heat cutoff | Required valve gain | Maximum upward speed |
| --- | --- | --- | --- | --- | --- |
| Sound seals | 12 | 3 | 8 | 1 | 320 px/s |
| Worn seals | 8 | 2 | 7 | 2 | 290 px/s |
| Cracked seals | 5 | 1 | 6 | 3 | 260 px/s |

Jetpack inputs are A pressure (0–12), B heat (0–10) and C thrust request (0–3). OUT must equal C times the stage's gain when pressure is sufficient and heat is below the cutoff, otherwise zero. Certification covers all 572 input combinations per stage. The live installed circuit determines valve drive. Wear also lowers thrust per drive unit; a higher output does not restore the original pack's performance. Each new stage starts from the player's own earlier draft. No flight solutions are supplied.

Maintenance shutters enforce stage order. The upper curtain needs a separate exhaust board: A pipe pressure, B safe pressure, C exhaust request; release only the positive pressure excess when requested. All 260 combinations are tested, and the live board must release the actual five-unit excess to open the route.

Controls: A/D or arrows to move, Space to jump, W/up to thrust, R for throttle, G to edit at a brass landing, V for the upper exhaust controller, F to heal with bread, Backspace to recall, Escape to pause. Ordinary platforms refill and cool the pack while thrust is released. Falls and machinery hazards cost 25 health and restore the latest rest/maintenance checkpoint; reaching zero health sends the player to town with 40 health while keeping that checkpoint. Recall is always available. Bread heals 25 health, capped at 100, and cannot be wasted at full health. Player hunger and passive health loss are removed. Wear occurs only at the two major maintenance landings. Saves preserve health, hazard phase, progress, field drafts and installed designs. Old-layout checkpoints map to their equivalent maintenance stop, preserving earned rewards.

The final seal breaks only after landing at the archive. E recovers the steam accumulator: new production batches take 20% less time with unchanged ingredients; already-running batches keep their duration. The upgrade cannot stack. The pack remains retired even if its saved board is edited. E then takes the gravity cage home. No creator identity is revealed.

Remaining: player-led balancing of hazard timing, checkpoint spacing, longer-section pacing and low-throttle flight, plus remaining three-section environmental motion, audio and summit presentation in the delivery plan. The shared art/HUD pass and saved homecoming are implemented. Preserve the current physical route and rewards unless playtesting supports an intentional adjustment. Later village/trade routes, waterworks, plains and the main-story finale follow the existing-game overhaul.

## 1. Business and market foundation (in progress)

- Represent each firm as an instance with a type, owner, optional parent company, cash, stock, workers, and installed machines. Multiple firms can share a type.
- Give business types production recipes. Machine effects modify specific operations such as capacity, fuel use, waste, reliability, or delivery speed.
- Move goods and money between firms on each day. Show stock, capacity, cash, and the reason for price changes in a readable ledger.
- Preserve older saves when introducing the new model.

## 2. Visible village growth and more businesses

Current slice: six founders start in three households, with three additional cottages developing only when food, savings, and funded work support them. Residents earn proportional wages through actual attendance, buy real bread after reaching the market, and retain needs, relationships, and memories. The normal day runs continuously; sandbox, the pause overlay, and the main menu pause it. New residents come from a saved rotating pool and can leave after persistent hardship. Existing cottages remain reusable. Later food controllers expand output, and two controller-backed regional kit orders create paid packing positions at the timber yard and foundry. All three cottages can fill through the ordinary simulation.

The commercial site first attracts Jun when observed demand supports a second bakery. Prolonged closure releases it for a different owner or trade after a cooldown and fresh demand checks. Purchases prefer cheaper available stock and rotate equal-price suppliers. Owners bring explicit outside capital and take their remaining cash and inventory on departure. The UI uses the actual occupant's name and leaves vacant sites unlabeled.

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

- Introduce the approved southern canal settlement first at the small scope in delivery phase 5, with its own architecture, residents, local need and expedition lead. Expand its resources, prices, firms and commissions after its purpose is established.
- Make transport time and cost matter for goods and machines; allow compute services to trade across villages when communication infrastructure exists.
- Expand to larger regions only after the two-village economy remains understandable and stable.
- Let waterworks repairs, the plains journey and the regional steam-system finale reveal how places depend on one another. Keep major logistics expansion subordinate to the visual overhaul and authored adventure sequence.

## 6. Generated content

- Use hand-authored jobs to define reliable templates and validation rules first.
- A local model may later propose stories, contract details, and business variants. The game must validate each job's truth table, available parts, economic effect, and reward before offering it.

## Interface rule for every phase

Keep the town map for place and people, the contract board for decisions, and a compact economy view for causes and consequences. Every important change should have a short explanation such as "flour shortage -> bakery output fell -> bread price rose." Avoid asking players to read raw accounting tables to understand the next action.

Apply the shared exploration/engineering/conversation UI treatments and full-scene visual standard in the approved delivery plan. Keep detailed systems available where they support a decision, reduce permanent exploration clutter, and provide clear feedback, readable controls and safe opportunities to read. A visual refresh is complete only when it covers the supporting screens and moment-to-moment play as well as representative screenshots.
