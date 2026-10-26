# Numbermill visual style

Current implementation reference, October 26, 2026. This describes the code in the checkout, not a promise that the full visual overhaul is finished. [ROADMAP.md](ROADMAP.md) owns delivery priorities and story plans.

## Direction and shared foundations

October 26 canal/clock addition: the town's copper-rimmed disc uses equal sun/day and moon/night halves rotating beneath a fixed top pointer. Its saved fractional simulation phase also drives a cyclic light palette and lantern fade, including the brief night/dawn passage across the day boundary. Business-day duration and resident schedules retain their existing semantics; the exploration HUD shows a phase label instead of a conflicting numeric time.

Reedhaven follows the player's canal/lake/dock sketch, retained in `testing-screenshots/canal-settlement/layout-reference.png`. A northern towpath joins the northeastern lake landing to a timber footbridge; the settlement sits south of the canal. Pale lockstone, copper seams, ropework, reed beds, a cistern square and lake reflections distinguish it from Copperside while retaining the same pixel scale, shared typography/panels, actor silhouettes, daylight and ground-contact depth ordering. The shoreline polygon drives both visible banks and collision. Travel and the boat controller use the existing field editor and saved workshop goods. Audio remains deferred.

Numbermill uses code-drawn pixel art: warm timber, worn copper and brass, restrained teal machinery, soft green landscapes and ivory records. Build recognizable silhouettes and broad material areas first; add joints, grain, masonry, foliage and small highlights where they clarify the object. Keep decorative contrast below actors, useful controls, routes and hazards. Existing art is drawn with Pygame primitives and cached surfaces; this pass does not introduce a bitmap asset pack.

The shared presentation foundation is implemented:

- **Palette:** `ui_theme.py` supplies ink `(39, 51, 49)`, ivory paper `(249, 240, 217)`, teal `(39, 107, 104)`, copper `(165, 92, 57)`, gold `(220, 171, 81)` and deep teal `(24, 49, 51)`. Environments have their own material palettes within that family.
- **One interface style:** village and adventure HUDs, instruments, conversations and records use the same ivory panels, copper corner bindings, shadows, teal headings and dark text. `expedition_ui.py` delegates panel drawing to `ui_theme.draw_panel`; an adventure changes which information is shown, not the interface style. Engineering keeps its drafting canvas within the same panel/button system.
- **Typography:** one bundled Chakra Petch family with clean, squared retro letterforms covers body text, headings, small labels, numeric readings, signs and machine displays through `ui_theme.make_font`. Use Medium and SemiBold weights from that family instead of switching small text to an unrelated monospace face. Antialias lettering to preserve readable strokes at small sizes; the scenery retains its pixel-art treatment. Current logical sizes are 18 body, 24 heading, 16 small and 14 tiny. Reserve capitals for short instrument labels. Use `fit_text` and `wrapped_text` with deliberate bounds; do not silently squeeze a paragraph into a label.
- **Controls:** shared buttons expose active, hover, pressed, disabled and focus states. Keyboard focus navigation is implemented for menus, pause and settings; it is not a complete keyboard-navigation retrofit of every editor.
- **Display:** `presentation.py` renders a fixed 1280 × 760 canvas into a resizable, letterboxed window, with fullscreen, crisp scaling by default and optional smooth scaling. Pointer input uses the same transform. Settings also include reduced motion and a controls reference; preferences are separate from game saves.

These foundations are complete for this implementation pass. Accessibility and interaction coverage remain partial: text-size adjustment, rebinding, audio controls and broader keyboard navigation are still outstanding.

Fullscreen follow-up: Windows now renders at real monitor pixels with per-monitor DPI awareness. `window_display.py` positions the borderless window at the current monitor's exact origin and restores windowed placement. Smooth scaling off uses centered whole-pixel enlargement in fullscreen; on uses the largest proportional smooth fit. Both use the same pointer transform. This improves scaling clarity without claiming native-resolution text rendering: the source canvas remains 1280 × 760.

## Scene and screen inventory

“Implemented” below identifies the treatment present now. “Partial” identifies remaining work within the larger approved overhaul. A completed treatment does not establish that the entire scene is finished.

| Scene or screen | Implemented treatment | Coverage and remaining work |
| --- | --- | --- |
| Title, introduction, save slots, pause, settings and controls | Shared backdrop, typography and button states; clearer title/save flow, summaries, pause navigation, display settings and controls page. | Shared menu pass implemented. Rebinding, text size and sound options remain partial. |
| Copperside and residents | Building-specific roof forms, masonry/timber, connected chimneys, shutters, machinery and cargo; richer planting, curbs and plaza; natural river; clearer nearby nameplates. Named workwear, shopping baskets, trays and tool gestures reflect existing activities. Clock-based morning-to-evening color, warm panes/dormers, lanterns, sparse leaves and state-driven mill/fire/smoke/gear/river motion are pause-aware. | Substantial town and daylight pass implemented. Reduced motion holds decoration still while preserving the actual clock and warm windows. A short night/dawn passage now continues smoothly across rollover, with a rotating day/night disc. Weather remains future work. Richer cinematic expressions remain later polish. |
| Reedhaven | Player-drawn canal/lake layout, northeastern dock, towpath and footbridge; pale lockstone, copper/slate/clay roofs, boatyard, ropework, gardens, cistern and four residents. Unified paving masks clip complete bricks and join every branch before texturing. | Initial settlement and boat progression delivered; upstream waterworks is a lead for the next expedition. Audio is deferred. |
| Mosswater | Regional woodland, wetland and archive ground treatments; ruins, layered vegetation, natural pond/river banks and clearer depth. Compact health and brass receiver instruments show bearing, channel, distance and survey state. | Environment/HUD pass implemented. Full motion, camera refinement, navigation balancing and arrival/recovery/reward presentation remain partial. |
| Boiler Tower | Warm masonry and furnace galleries, darker iron driveworks, cooler condenser crown with mountain windows; detailed platforms and machinery; compact health/pack readings and contextual station actions. | Three-section art/HUD pass implemented. Full animated machinery, ascent/camera framing, pack-wear feedback, pacing and summit presentation remain partial; the saved homecoming is implemented. Decorative background gears are not all animated. |
| Production workshop | Brick/windows/timber room, nine distinct equipment sprites, selection brackets, working indicators, readable catalogue labels and prices, supplies/customer rows and machine status. Recovered steam accumulator has a physical installation on the rear wall. | Floor/catalogue/inspector pass implemented. Richer production-completion, material-transfer and upgrade celebrations remain partial; existing simulation and shortage text remain authoritative. |
| Circuit bench, sandbox, invention, nested devices and machine/field controller editors | Quiet framed drafting board, preserved grid and sockets, clearer inactive traces, directional wiring and rendering-only crossing bridges; shared typography and controls. | Board/theme pass implemented across shared editors. Exact placement, manual routes and existing editor behavior are retained. Further result/failed-case and inspector redesign is partial. |
| Dialogue and Shannon | Sprite portraits, clearer name/topic header, restrained dividers and bounded text; coherent existing character art. Factory Shannon uses simulation time and respects reduced motion. | Portrait/layout pass implemented. The connected opening chapter now adds shared-panel scene portraits, a paginated evidence journal, saved homecomings and evidence-sensitive Journey topics. Expressive portraits and fuller cinematic staging remain future work. |
| Library, contracts, ledger and map | Shared office framing and typography. Ledger charts reserve space for values, use subtle area fills and readable labels; people have portraits and named workplaces. Map styling and river geometry match the town. | Shared office treatment and targeted ledger/map pass implemented. Library/contracts keep their existing information architecture; complete review of every long-content, result and empty state remains partial. |
| Requests, shop transactions, delivery, computation, timing/test results, help, component info and secondary dialogs | Shared fonts, panels and buttons propagate through existing screens; existing contextual data and controls remain. | Partial: these have not all received a bespoke layout/content redesign in this pass. Check them independently when changing shared UI. |
| Developer tools | Existing overlay remains available through the pause menu's developer entry, using the current shared controls. | Functional supporting screen; no dedicated visual overhaul is claimed. |

## Rendering and interaction rules

- **Readability before density.** Preserve clear doors, streets, future building sites, landing surfaces and interaction space. Keep text off busy scenery. Layer raised props by their ground contact using `scene_depth.py`; draw actors behind or in front according to position, not an arbitrary global overlay.
- **Visual ground and collision must agree.** Natural water uses shared polygons, not a painted curve over an old rectangular blocker. `water_geometry.py` supplies contour helpers; `town_water.py` owns the town river; Mosswater supplies its pond/channel contours to rendering, collision and vegetation exclusion. Keep bridge exceptions and closed-gate protection intact. Use the actor's visible foot anchor consistently for bank and bridge checks. The town minimap and ledger map must transform the same river contour.
- **Distinguish scenery from gameplay.** Background pipes, gears and masonry are quiet and do not imply extra platforms. Active hazards and warnings must remain identifiable in motion and with reduced motion enabled. Do not reveal concealed survey targets or change traversal/puzzle geometry as incidental decoration.
- **Respect the engineering workspace.** Keep the 16 × 9 circuit grid, sockets, rotations, user-placed parts and manually drawn routes exact. Crossing arcs are visual only; they create no connection. Preserve the production floor's 9 × 6 cell layout. Explain required behavior without drawing a solution circuit or auto-routing it for the player.
- **Reflect real state.** Activity effects follow actual work/simulation state and pause with it. Reduced motion calms decoration, not essential gameplay warnings. The factory's segmented activity strip denotes working state, not a fabricated progress percentage. Upgrades appear only when earned.
- **Keep layouts bounded.** Use logical canvas coordinates for drawing and mapped coordinates for input. New controls need readable names, clear disabled reasons where relevant, and unobscured hit areas. Test long names, wrapped dialogue, empty lists, locked equipment and populated lists as well as ideal examples.
- **Keep procedural art stable.** Use deterministic seeds for static detail and cache reusable scenery. A reload must not move meaningful landmarks. Do not turn decoration into a simulation/save change without deliberately handling compatibility.

### Character performance follow-up

Evening home entry now uses staggered resident departure times between 17:45 and 18:45 on the actual village clock. The existing walker follows its route to the real home door; hide the sprite and its interaction target only after displayed arrival, including the smoothing delay. Shared-home occupants enter independently. Sleeping people provide no visible/social conversation partner, and normal routines resume at the next morning. Grace uses her own workshop. Reproduce evening/morning views and the disposable native pause/entry check with `scripts/capture_resident_evenings.py --smoke`; this changes evening routines, not collision or household membership, and uses existing citizen save fields.

`resident_performance.py` selects presentation from current destinations, displayed arrival at the actual waiting slots, workplace state and nearby arrived company. It does not change resident decisions or saved state. Shopping baskets may travel; tools, stools and social gestures wait for the appropriate destination. A social visit alone does not create an imaginary conversation partner. Spouse visits require the spouse. Palette choices are shared by town sprites and dialogue portraits, including the arriving resident pool.

Keep the existing character scale and feet/depth anchors. All four facings retain recognizable clothes and hair; Grace's one wooden prosthesis must survive every pose. Idle shifts leave feet planted, walk cycles remain distance-driven, and props attach to posed hands within the actor envelope. Back-facing inspection shows the board's wooden back. Shannon turns toward Boole when addressed, with a raised hand and attentive screen. Decorative timing uses update-driven clocks and freezes with pause/reduced motion; walking remains readable with reduced motion.

`scripts/capture_resident_performance.py` generates `testing-screenshots/resident-performance/review.html`, native-scale facing/walking sheets, a looping destination-motion GIF and staged in-town views. `--smoke` exercises 180 frames in a disposable native window, checking walking return and companion collision. These review fixtures never read or overwrite player saves. The full regression/UI run passed 475 tests; longer player review remains distinct from automated checks.

### Copperside environment follow-up

`town_atmosphere.py` reads the same village clock as the HUD without initializing or changing saved state while drawing. Its flat per-channel palette transform preserves pixel edges/material detail; HUDs and nameplates are drawn in their shared UI colors. Evening windows use cached visible-glass masks taken from the actual building sprites, including dormers/skylights, leaving mullions, shutters, awnings and machinery uncovered. Lights and leaves join the existing ground-contact depth ordering. Decorative timing never uses wall-clock time. Machinery uses real batch/work/operating/shortage state, including owner-operated eastern trades, and inactive fireboxes are dark. Reduced motion fixes water, smoke, gears and character decoration in calm poses and omits falling leaves; daylight still reflects the village time.

Garden paths use subdued worn-earth shoulders and texture, with openings in street curbs and the court rim at actual path mouths. Avoid a dark outline across a junction or a uniform strip pasted over another material. Their shared masks reserve the complete paths/court against raised props and planting. Preserve the well furniture and verify joins at gameplay scale. Matching daylight comparisons and ordinary simulation views of six neighborhoods at four clock times are in `testing-screenshots/copperside-daylight/review.html`; `scripts/capture_copperside_daylight.py --smoke` also checks exact pause/resume and calm decoration in a disposable native window. Reedhaven now reuses this lighting and the day/night disc; audio remains deferred.

Roof polish means improving the existing material textures, not adding three-dimensional side faces. Continue the texture all the way to both sloping edges. Do not cover it with broad, solid-colored strips or wedges; the user specifically rejected these on every building. Keep successful shapes and textures.

`town_ground.py` owns the authored street contours used in the world, minimap and ledger. Their narrower sections and broader forecourts cover existing resident travel lines and waiting positions; they do not change movement or building collision. Main streets use small worn setts, the cottage lane uses quieter gravel, and the well garden and work yards have connected, purposeful ground treatments. Keep all future building envelopes free, including when they are still vacant grass plots. Raised decoration checks its entire bounds against the paved-road mask as well as doorway and building reservations. Use the existing `scene_depth.py` ordering for every raised prop.

`town_roofs.py` keeps the established silhouettes but maps materials onto roof planes. Timber boards have grain and fasteners; shingles and slate overlap; clay tiles have downhill ridges; patinated metal has raised seams. Flat shade bands, ridge caps, fascias and eave shadows establish depth within the pixel-art palette. Triangular roofs retain a complete material surface, with courses getting smaller toward the peak and slate toes casting small overlap shadows. Preserve existing facade detail, dormers, machinery and entrances. The user rejected a diagonal roof strip over an exposed timber triangle; do not reintroduce that conflicting perspective.

Compare the approved environment pass in `testing-screenshots/copperside-environment-review/review.html`: Before/After controls retain the same camera and default to native 1280 × 760 scale. Inspect the developed-site frames as well as the starting town. The subsequent character and resident-activity pass has its own review under `testing-screenshots/resident-performance/`.

## Reproduce and inspect

Use the repository virtual environment. The capture scripts below patch save/design paths into disposable directories; they do not load or overwrite player saves. Render normal building and manufacturing, not only guided lessons. Expedition walkthrough captures use test fixtures and are developer review material, not player-facing hints.

| Capture script | Output under `testing-screenshots/` | Coverage |
| --- | --- | --- |
| `scripts/capture_presentation.py` | `presentation-overhaul/` | Title, settings, controls, save slots, town and pause. `--smoke` exercises a real window through resize/fullscreen; `--play` opens a disposable interactive title. |
| `scripts/capture_town_overhaul.py` | `town-overhaul/` | Several neighborhoods, river cottages, map overview and resident sheet. `--smoke` runs a short live window. |
| `scripts/capture_copperside_environment.py` | `copperside-environment-review/after/` | Nine matching gameplay-scale views, native overview, developed eastern cottages/commercial site and all eighteen roof treatments. `--smoke` exercises a native window and movement with disposable state. |
| `scripts/capture_day_clock.py` | `day-clock/` | Disc phases, exact rollover palette/lamp continuity, gradual dawn; `--smoke` checks a real day rollover and exact pause. |
| `scripts/capture_canal_settlement.py` | `canal-settlement/` | Arrival, quays, bridge, square, homes, conversations, cistern repair and overview; `--smoke` walks the dock-to-market route and checks pause/reload. |
| `scripts/capture_canal_departure.py` | `canal-settlement/boat-*.png` | Locked route, gear repair, blank controller specification, ready launch and controls reference. |
| `scripts/capture_copperside_daylight.py` | `copperside-daylight/` | Matching Before/After views at four actual clock times, six populated/developed neighborhoods, plus ordinary-routine views. `--smoke` verifies native motion, exact pause/resume and calm reduced motion; `--hold 45` leaves the final window available for inspection. |
| `scripts/capture_workshop_overhaul.py` | `workshop-overhaul/` | Empty and active factory, equipment/supplies/orders, machine detail, normal free-build, Library/contracts, every ledger tab and four dialogue portraits. |
| `scripts/capture_mosswater_expansion.py` | `mosswater-expansion/` | Woods, ponds, marsh, bridges, receiver/survey, archive and reward states. |
| `scripts/capture_boiler_tower.py` | `boiler-tower/` | Three sections, controller views, flight, hazard phases, landings and ending. `--play` starts a disposable preview; `--smoke` runs a short live hazard check. |

Example from the repository root:

```powershell
New-Item -ItemType Directory -Force .test-tmp | Out-Null
$env:TEMP = (Resolve-Path .test-tmp).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe scripts\capture_workshop_overhaul.py
```

Inspect full-size frames and actual movement. Captures show appearance at selected states; they do not establish route feel, animation quality, collision correctness or reliable scaled input on their own. Relevant regression coverage includes presentation/interaction tests, town overhaul and scene depth, Mosswater shorelines, expedition presentation, factory UI and traces. Run affected tests for changes; use `scripts/debug_game.py` and `scripts/audit_economy.py` for broader integration checks.

## Still outstanding

The full visual milestone remains in progress. Finish integrated sound and music, scene transitions, animation and camera work, injury/recovery and production/reward feedback, and playtest pacing across complete routes. Standalone WAV drafts are not an integrated audio system. Add text sizing, rebinding and sound settings with layout and input verification.

Story canon and the planned canal settlement, waterworks, flower-filled plains, laboratory and regional steam-system finale remain roadmap work. The visible accumulator is implemented; that alone does not complete the tower homecoming, evidence journal or connected opening chapter. Keep these distinctions when describing progress or choosing screenshots.

## Connected opening chapter

`chapter_ui.py` uses the shared panel, buttons, typography and existing character portraits. Small journal/receiver/accumulator illustrations use integer-scaled code-drawn pixels in the world palette. Evidence and open questions occupy separate bounded areas; scene paragraphs are fully visible, with no timed text or automatic advance. B opens the journal in town, the factory and expeditions. New homecoming conversations wait for Copperside; completed memories can be replayed elsewhere. Reading freezes simulation and hazards; Esc defers without losing the saved page.

Reproduce the opening, both homecomings, well scene, every evidence entry, Journey topics and installed accumulator with `scripts/capture_opening_chapter.py`; `--smoke` also exercises a disposable native window and event dispatch. No player saves or font settings change.
