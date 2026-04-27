# Master Game Summary For Pro Mode

This document is a fast handoff for another model or collaborator. It describes the live state of the game, the major systems already in place, the current content footprint, the most important recent additions, and the strongest next recommendations.

## 1. Game Identity

- **Genre:** roguelike deck-building card battler
- **Core inspiration:** Slay the Spire style progression with a cyberpunk tone
- **Tech stack:** Python + Pygame
- **Resolution:** `1280x720` fixed
- **Architecture:** modular, system-based

### Design pillars

- Turn-based combat only
- Card-driven actions only
- Deterministic rules with controlled randomness
- Modular systems: map, combat, cards, enemies, events, rewards, UI
- UI clarity over visual complexity
- Systems should be testable without visuals
- No hidden mechanics in the rules layer, even when presentation includes mystery or corruption flavor

## 2. Current Playable Loop

The live run structure is:

1. Choose a character.
2. Navigate a branching node map.
3. Enter combat, elite, shop, or event nodes.
4. Resolve turn-based combat through cards, statuses, relic hooks, and enemy intents.
5. Gain rewards, modify the deck, buy from shops, collect run modifiers, and continue.
6. Progress through authored maps until victory or death.

Core node types are `combat`, `elite`, `shop`, `event`, and `boss`.

## 3. Content Snapshot

These counts reflect the current live data and generated references.

- **Characters:** 3
- **Cards:** 68 total
- **Hidden cards:** 5
- **Status cards:** 4
- **Enemies:** 47
- **Bosses:** 9
- **Events:** 91
- **Relics / run modifiers in the main relic catalog:** 65
- **Blessings:** 10
- **Curses:** 9
- **Combat statuses:** 15
- **Run-modifier statuses:** 6
- **Maps:** 5

### Card ownership split

- `shared`: 17
- `enforcer`: 17
- `operator`: 17
- `bio_hacker`: 17

### Event rarity split

- `common`: 29
- `uncommon`: 33
- `rare`: 18
- `special`: 11

### Event character split

- 30 character-specific events total
- 10 each for `enforcer`, `operator`, and `bio_hacker`

## 4. Characters And Core Playstyles

### Enforcer

- Role: brute force, strength scaling, momentum pressure
- Style: heavy offense and combat snowballing
- Starter identity: direct attacks, block, strength, burst

### Operator

- Role: control / tech
- Style: card flow, cost control, efficient sequencing
- Starter identity: planning, chain-building, turn optimization

### Bio-Hacker

- Role: risk / sustain
- Style: trade HP for tempo, recover through pressure, weaponize mess and status
- Starter identity: self-damage, healing, infect pressure, attrition

## 5. Combat And Status Model

Combat is a standard deckbuilder loop:

- draw into hand
- spend energy to play cards
- discard / exhaust as effects resolve
- enemy intents execute after the player turn

Important combat statuses include:

- `strength`
- `weak`
- `vulnerable`
- `infect`
- `burn`
- `bleed`
- `block`
- `marked`
- `suppressed`
- `nullified`

The status layer is one of the game's strongest differentiators because it connects cards, enemies, and relic hooks cleanly. The references already document who can apply what, which is useful for tuning and feature planning.

## 6. Run Structure And Campaign Maps

There are currently **5** authored map definitions:

- `outskirts`
- `city_streets`
- `helix_ward_depths`
- `blackwire_lockdown_sector`
- `cinder_jackals_edgeworks`

Each map currently uses **15 floors**.

### Progression shape

- `outskirts` leads to `city_streets`
- `city_streets` branches by boss outcome into one of three faction routes:
  - `blackwire_lockdown_sector`
  - `cinder_jackals_edgeworks`
  - `helix_ward_depths`
- Branch routes end in victory

### Important caveat

The generated enemy reference explicitly notes that `city_streets` currently has authored boss-route content, but regular combat and elite routing still point at placeholder IDs in `campaign_maps.json`. That is one of the clearest content gaps still visible in the live game state.

## 7. Enemies, Bosses, And Factions

There are **47 enemies** and **9 bosses** across the current content set.

Boss routes and enemy presentation are already factionalized. Major faction flavor presently includes:

- `cinder_jackals`
- `blackwire_directorate`
- `helix_ward`

The content reads as deliberately themed rather than generic encounter soup. That gives future work a good base for faction-specific relics, events, route identities, and reward shaping.

## 8. Cards, Relics, Blessings, Curses, And Shops

### Cards

- The card pool is compact but real: 68 cards including shared cards, class cards, hidden cards, and status cards.
- Hidden cards exist and are now meaningfully tied into event outcomes and Protocol Drift content.

### Run modifiers

The generated references distinguish:

- **65 relic catalog entries**
- **10 blessings**
- **9 curses**

The underlying modifier ecosystem is richer than a simple relic list. It already supports:

- passive combat hooks
- event-gained modifiers
- blessings from run start or other sources
- curses as event or consequence content
- shop-affecting and economy-affecting effects

### Shop state

The game has a persistent shop state with rerolls, seen-item tracking, heal offers, and cleanse offers.

Current economy notes from the audit report:

- reroll cost: `12 + (8 x rerolls used in that shop)`
- heal service: flat `14 HP` for `18 credits`
- the audit still concludes that end-of-run credits remain high and a **third shop-only sink is recommended**

That recommendation is one of the safest near-term economy improvements.

## 9. Events And Protocol Drift

This is one of the most important recent expansions.

### Event system state

- Live event count is now **91**
- The 75-event expansion has been integrated
- The 11 Protocol Drift foundation events were preserved instead of duplicated
- Event data supports up to **4 choices**
- Event tags were expanded to cover the draft taxonomy now in live use

### Character-specific event support

- Event-level `character_ids` are live
- The selector honors those assignments
- Each character has 10 exclusive events

### Signature events

Before normal weighted event selection, the first eligible event node can guarantee a one-time signature event:

- `enforcer` -> `riot_drill_square_01`
- `operator` -> `cheap_implant_rack_01`
- `bio_hacker` -> `infection_gallery_01`

No save-format bump was required because `event_history` already prevents repeats.

### Protocol Drift

Protocol Drift is a live run-state system, not just flavor text.

- Stored in `run_state.protocol_drift_pct` from `0` to `100`
- `protocol_drift_seen` tracks when it becomes visible
- `queued_next_combat_effects` stores one-shot payloads granted by events

Supported event effects now include:

- credits
- HP loss / heal
- card gain
- fixed card removal or purge
- fixed modifier gain / removal / refresh
- Protocol Drift changes
- random modifier gain
- queued next-combat effects

### Queued next-combat effects currently supported

- turn-one energy
- draw
- block
- player combat status
- status-card insertion
- temporary card to hand

### Hidden-card event sources

These event sources are already wired and should be treated as canonical live behavior:

- `signal_busker_01` -> `drift_mirror_cache_01`
- `blackwire_broker_01` -> `drift_null_refund_01`
- `bone_receipt_window_01` -> `drift_error_knife_01`
- `protocol_patch_bay_01` -> `drift_unsafe_overclock_01`
- `protocol_eclipse_01` -> `drift_black_ice_bloom_01`

### Adaptation policy already used

The recent pass intentionally did **not** add:

- event-flag infrastructure
- OR-chain selectors
- next-shop state
- next-reward state
- max-HP loss systems
- random deck-loss systems

Instead, unsupported draft mechanics were adapted into currently supported immediate effects, fixed gates, fixed card edits, or queued next-combat effects. That policy should remain the default unless there is a deliberate design decision to widen the engine.

## 10. Save / State / Engine Notes

Important systemic facts:

- The project contract says not to change public interfaces or core schemas casually.
- Save, card, and enemy schema changes require versioning discipline.
- The current event expansion specifically avoided a save-format bump.
- The codebase already tracks enough run state to support map progress, event history, active shop state, queued effects, and Protocol Drift.

This is a game with meaningful runtime state already, not just isolated combat demos.

## 11. Architecture And Key Files

These modules matter most when onboarding another model:

- `main.py`
- `config.py`
- `core/game_loop.py`
- `core/state_manager.py`
- `combat/combat_manager.py`
- `combat/turn_manager.py`
- `combat/action_resolver.py`
- `cards/card_base.py`
- `cards/card_library.py`
- `cards/deck_manager.py`
- `entities/player.py`
- `entities/enemy.py`
- `entities/enemy_library.py`
- `map/map_generator.py`
- `map/node.py`
- `ui/ui_manager.py`
- `ui/combat_ui.py`
- `ui/map_ui.py`
- `ui/event_ui.py`

Reference and content files worth reading first:

- `reference/cards_master_reference.md`
- `reference/characters_master_reference.md`
- `reference/enemies_master_reference.md`
- `reference/bosses_master_reference.md`
- `reference/relics_master_reference.md`
- `reference/blessings_master_reference.md`
- `reference/curses_master_reference.md`
- `reference/statuses_master_reference.md`
- `reference/events_master_reference.md`
- `reference/protocol_drift_catalog_note.md`
- `roguecard/master-project-charter`
- `roguecard/technical-contract`

## 12. Current Strengths

The game already has more real structure than a typical prototype:

- three distinct characters with readable archetypes
- playable combat identity with statuses and relic hooks
- branching campaign structure with faction routes
- robust event catalog with character-specific content
- live Protocol Drift system with hidden-card integration
- generated references that make the data layer legible
- modular architecture with explicit contracts

The strongest content pillar right now is the combination of:

- card archetypes
- status interactions
- event flavor
- Protocol Drift corruption / preview scaffolding

## 13. Current Gaps And Risks

These are the clearest issues another model should keep in mind.

### Content gaps

- `city_streets` regular combat and elite routing still use placeholder IDs
- economy still leaves too many credits unused by endgame
- some advanced draft-style event chains were intentionally flattened into supported immediate outcomes

### System risks

- the codebase has a strong technical contract, so schema or interface changes should be treated carefully
- save state is now broad enough that new systems can create migration risk quickly
- Protocol Drift is live enough that future corruption features should be added deliberately rather than casually bolted on

### Process risk

- live JSON and generated references should be treated as authoritative over older draft planning docs when they disagree

## 14. Best Next Recommendations

These are the highest-value follow-ups if the goal is to improve the live game in a practical order.

### 1. Finish authored encounter routing for `city_streets`

This is probably the most obvious content completeness issue. The game has strong route identities, and the placeholder routing undercuts that.

### 2. Add a third shop-only credit sink

This is the safest economy improvement because the audit already recommends it. Good candidates:

- paid upgrade service
- temporary combat prep service
- event/relic intel service
- card transform or tech-tune service

### 3. Do a reward-flow tuning pass

Now that the event catalog is larger, the next pass should inspect:

- reward pacing
- card acquisition rate
- relic saturation
- curse pressure
- branch difficulty curves

### 4. Deepen Protocol Drift as a route-defining system

The scaffolding is strong now. Good expansions would be:

- more drift-threshold interactions
- route-specific drift reactions
- more corruption riders on cards and modifiers
- boss or elite responses to high drift

### 5. Add a focused event polish pass

The event expansion is broad. A quality pass would now be valuable for:

- sharper preview consistency
- stronger choice differentiation
- rarity tuning
- floor-band tuning
- more bespoke art and flavor consistency checks

### 6. Strengthen cross-system references and onboarding docs

This repo benefits a lot from generated references. A next step could be a single generated dashboard or summary page covering:

- counts
- route structure
- event pools by character and rarity
- hidden-card sources
- modifier source breakdown

## 15. Suggested Prompting Guidance For Another Model

If handing this project to another model, the most useful instructions are:

- treat live data and references as the source of truth
- preserve modular interfaces
- avoid schema changes unless clearly necessary
- respect existing save compatibility unless explicitly choosing to version
- use the generated references first before editing raw content files
- consider `Protocol Drift` and `event_history` first before proposing new event-chain infrastructure

## 16. Bottom Line

This is no longer a thin prototype. It is a playable, system-rich cyberpunk deckbuilder with:

- a real three-character foundation
- meaningful combat identities
- 91 live events
- faction route structure
- boss content
- a substantial modifier ecosystem
- a live Protocol Drift corruption layer

The highest-leverage next steps are content completion, economy sinks, reward tuning, and deeper use of Protocol Drift as a defining run-shaping mechanic.
