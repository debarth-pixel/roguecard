# Statuses Master Reference

Generated from combat/status code plus `data/cards.json`, `data/enemies.json`, and `data/run_modifiers.json`.

- Combat statuses: **15**
- Status cards: **4**
- Run-modifier statuses: **6**

## Combat Statuses

### Strength (`strength`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Adds its value to outgoing attack damage.
- Clears / Decay: Persists until combat ends or another effect removes it.
- Visual Flavor: A clenched gauntlet or piston-loaded arm outlined in red power lines and hard impact sparks.
- Who Can Apply It: Ashfang Rook (`ashfang_rook`), Culture Shepherd (`culture_shepherd`), Embersnout (`embersnout`), Failed Saint (`failed_saint`), Furnace Hound (`furnace_hound`), Gland Brute (`gland_brute`), Miremother Vexa (`miremother_vexa`), Sandpack Alpha (`sandpack_alpha`), Scrap Caller (`scrap_caller`), Serum Acolyte (`serum_acolyte`), The Graft Saint (`graft_saint`), Battle Roar (`enforcer_battle_roar_01`), Open Wound (`enforcer_open_wound_01`), Pain Circuit (`bio_pain_circuit_01`), Redline Core (`enforcer_redline_core_01`), War Engine (`enforcer_war_engine_01`), Enemy phase transitions such as Gland Brute and Graft Saint

### Weak (`weak`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Outgoing attack damage is reduced to 75% while Weak is active.
- Clears / Decay: Ticks down by 1 at the start of that unit's turn.
- Visual Flavor: A flickering reticle, blurred stance lines, and signal wobble that make the target look off-balance.
- Who Can Apply It: Dune Raider (`dune_raider`), Black Ice Bloom (`drift_black_ice_bloom_01`), Needle Ping (`operator_needle_ping_01`), Static Haze (`operator_static_haze_01`), Execution Array (`execution_array`) [relic], Exposure Grid (`exposure_grid`) [relic], Grave Lantern (`grave_lantern`) [relic], Grave Matrix (`grave_matrix`) [relic], Grave Sprinkler (`grave_sprinkler`) [relic], Pressure Mesh (`pressure_mesh`) [relic], Pressure Sight (`pressure_sight`) [relic], Reaper Census (`reaper_census`) [relic], Verdict Engine (`verdict_engine`) [relic]

### Vulnerable (`vulnerable`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Incoming attack damage is increased by 50% while Vulnerable is active.
- Clears / Decay: Ticks down by 1 at the start of that unit's turn.
- Visual Flavor: A cracked armor plate or exposed seam lit by sharp hazard highlights.
- Who Can Apply It: Black Ice Bloom (`drift_black_ice_bloom_01`), Crackdown (`enforcer_crackdown_01`), Execution Array (`execution_array`) [relic], Exposure Grid (`exposure_grid`) [relic], Grave Matrix (`grave_matrix`) [relic], Pressure Mesh (`pressure_mesh`) [relic], Pressure Sight (`pressure_sight`) [relic], Verdict Engine (`verdict_engine`) [relic]

### Infection (`infect`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At end of the afflicted unit's turn, it loses HP equal to Infection. If Infection is 6 or more, it takes 4 extra damage and resets to 3.
- Clears / Decay: Persists until combat ends or an explicit effect changes it.
- Visual Flavor: Verdant spores, septic fluid, and invasive biotech growth crawling across metal or flesh.
- Who Can Apply It: Culture Shepherd (`culture_shepherd`), Gland Brute (`gland_brute`), Miremother Vexa (`miremother_vexa`), Serum Acolyte (`serum_acolyte`), Sludge Whelp (`sludge_whelp`), Waste Leech (`waste_leech`), Harvest Bite (`bio_harvest_bite_01`), Leech Jab (`bio_leech_jab_01`), Parasite Fang (`bio_parasite_fang_01`), Septic Round (`bio_septic_round_01`), Containment Loop (`containment_loop`) [relic], Execution Array (`execution_array`) [relic], Field Dampener (`field_dampener`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Septic Crown (`septic_crown`) [relic], Septic Reservoir (`septic_reservoir`) [relic], Septic Siphon (`septic_siphon`) [relic], Verdict Engine (`verdict_engine`) [relic], Viral Clamp (`parasite_seal`) [relic], Viral Relay (`viral_relay`) [relic]

### Burn (`burn`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At end of the afflicted unit's turn, it loses HP equal to Burn.
- Clears / Decay: Burn decays by 1 at end of turn until it reaches 0.
- Visual Flavor: Ember-orange scorches, ash flakes, and heated metal glowing through blackened edges.
- Who Can Apply It: Burner (`burner`), Burner Mite (`burner_mite`), Embersnout (`embersnout`), Furnace Hound (`furnace_hound`), Scrap Gunner (`scrap_gunner`), The Graft Saint (`graft_saint`), Wastes Colossus (`wastes_colossus`), Ash Veil (`ash_veil`) [relic], Execution Array (`execution_array`) [relic], Field Dampener (`field_dampener`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Verdict Engine (`verdict_engine`) [relic]

### Bleed (`bleed`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: When the afflicted target is hit, it takes bonus damage equal to Bleed.
- Clears / Decay: Bleed drops by 1 each time the bonus damage triggers.
- Visual Flavor: Razor-red cuts, cable slashes, and fresh droplets drawn in aggressive diagonal marks.
- Who Can Apply It: Caravan Reaver (`caravan_reaver`), Carrion Hound (`carrion_hound`), Sandpack Alpha (`sandpack_alpha`), Bash Protocol (`enforcer_bash_protocol_01`), Breaker Line (`enforcer_breaker_line_01`), Gouge (`enforcer_gouge_01`), Arterial Reservoir (`arterial_reservoir`) [relic], Bleed Brand (`open_circuit_brand`) [relic], Blood Indexer (`blood_indexer`) [relic], Butcher Hooks (`butcher_hooks`) [relic], Controlled Bleed Valve (`controlled_bleed_valve`) [relic], Execution Array (`execution_array`) [relic], Execution Relay (`execution_relay`) [relic], Field Dampener (`field_dampener`) [relic], Grave Lantern (`grave_lantern`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Verdict Engine (`verdict_engine`) [relic]

### Marked (`marked`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Blackwire attacks gain +2 damage per current Marked stack, then consume 1 stack on hit.
- Clears / Decay: Player Marked lasts up to 2 turns unless consumed sooner. Generic enemy-side counters persist until removed.
- Visual Flavor: Clean compliance brackets, target pings, and white tracking circles locking onto prey.
- Who Can Apply It: Audit Hound (`audit_hound`), Director Vale (`director_vale`), Junction-9 Sentinel (`junction_9_sentinel`), Patrol Drone (`patrol_drone`), Relay Vulture (`relay_vulture`), Scrap Ticker (`scrap_ticker`), Signal Analyst (`signal_analyst`), Signal Junker (`signal_junker`), Suppression Sniper (`suppression_sniper`), Wastes Colossus (`wastes_colossus`), Field Dampener (`field_dampener`) [relic], Marker Scrambler (`marker_scrambler`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Toll Spike (`toll_spike`) [relic]

### Suppressed (`suppressed`)

- Category: Combat Status
- Lives In: `entities/player.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Attack cards deal 15% less damage per stack, with a minimum of 1 damage.
- Clears / Decay: Clears at the end of the player's turn. Player stacks are capped at 3.
- Visual Flavor: Compression rings, muted muzzle glyphs, and downward force lines pressing an attack flat.
- Who Can Apply It: Audit Hound (`audit_hound`), Compliance Engine AX-9 (`compliance_engine_ax9`), Director Vale (`director_vale`), Null Baton Officer (`null_baton_officer`), Riot Guard (`riot_guard`), Signal Analyst (`signal_analyst`), Spine Warden Null (`spine_warden_null`), The Toll Reeve (`toll_reeve`), Field Dampener (`field_dampener`) [relic], Null Damper (`null_damper`) [relic], Protocol Drift (`protocol_drift`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Toll Spike (`toll_spike`) [relic]

### Nullified (`nullified`)

- Category: Combat Status
- Lives In: `entities/player.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Blocks the next positive player combat gain: Block, positive Strength, positive next-attack bonus, or a negative next-card-cost modifier.
- Clears / Decay: Removes itself after blocking one eligible positive effect or when combat ends.
- Visual Flavor: A blank hex sigil, a slashed circuit icon, and a deadened field swallowing positive glow.
- Who Can Apply It: Signal Junker (`signal_junker`), Field Dampener (`field_dampener`) [relic], Null Damper (`null_damper`) [relic], Protocol Drift (`protocol_drift`) [relic], Quarantine Vault (`quarantine_vault`) [relic], Toll Spike (`toll_spike`) [relic]

### Fortified (`fortified`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At the start of turn, gain Block equal to Fortified, capped at 12.
- Clears / Decay: Persists until combat ends or another effect removes it.
- Visual Flavor: Layered defensive plates and reinforcing braces stacking into a machine-ready bastion.
- Who Can Apply It: Spawn rules for Audit Hound, Sentry Node, Compliance Engine AX-9, and Junction-9 Sentinel, Director Vale's first drone or machine summon gets Fortified 4

### Regenerate (`regenerate`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At the start of turn, heal HP equal to Regenerate.
- Clears / Decay: Consumes 1 stack after each start-of-turn heal.
- Visual Flavor: Soft medical green pulses, stitched tissue, and repair light knitting damage closed.
- Who Can Apply It: Failed Saint phase transition grants Regenerate 3

### Momentum (`momentum`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Adds its value to the next outgoing enemy attack.
- Clears / Decay: Clears after that attack or at the end of the enemy's turn.
- Visual Flavor: Forward-slashing speed lines, revved engine glow, and a wound-up attack posture.
- Who Can Apply It: Cinder Jackals also gain Momentum from scripted ally-attack synergies such as Ashfang Rook's Blood Rally

### Overheat (`overheat`)

- Category: Boss Resource
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Stored heat resource used by Furnace Hound to scale Boiler Spit and Redline Charge.
- Clears / Decay: Boiler Spit consumes 1 Overheat. Redline Charge clears all Overheat. Furnace Hound gains 1 at end of each turn.
- Visual Flavor: Orange pressure gauges, furnace coils, and heat haze bleeding from metal seams.
- Who Can Apply It: Furnace Hound end-of-turn passive gain

### Biomass (`biomass`)

- Category: Boss Resource
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Stored Helix boss resource used by Miremother Vexa to empower Biomass Collapse.
- Clears / Decay: Miremother Vexa clears Biomass after a thresholded Biomass Collapse.
- Visual Flavor: Wet organic matter pooling in vats and feeding thick green growth into a central mass.
- Who Can Apply It: Miremother Vexa gains Biomass when allied fodder dies

### Mutated (`mutated`)

- Category: Enemy Phase State
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Marks an enemy as having crossed a phase threshold and switched to its phase-rule intent pattern.
- Clears / Decay: Persists for the rest of combat once applied.
- Visual Flavor: A sudden body shift of split skin, exposed grafts, and phase-change growth bursting through.
- Who Can Apply It: Applied automatically by enemy phase transitions from enemies.json phase_rules

## Status Cards

### Burn (`status_burn_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Lose 2 HP.
- Visual Flavor: A burning warning chit or ember-eaten scrap ticket with a small orange glow. Keep status cards simpler and more symbolic than normal cards.
- Theme Lens: faction `shared`, palette `starter_neutral`, art style `circuit_burst`
- Live Generators: Rot Slash (`bio_rot_slash_01`)

### Glitch (`status_glitch_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Random one of: Glitch drains power. | Glitch bites back.
- Visual Flavor: A broken display mask or error face with scrambled pixels and torn scanlines. Status card art should feel like a hazard ticket, not a full scene.
- Theme Lens: faction `shared`, palette `starter_neutral`, art style `signal_mesh`
- Live Generators: Black Ice Bloom (`drift_black_ice_bloom_01`)

### Junk (`status_junk_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`
- Behavior: No direct effect.
- Visual Flavor: A pile of bolts, broken chips, bent plates, and useless machine trash. Simple pile silhouette, easy to read.
- Theme Lens: faction `shared`, palette `starter_neutral`, art style `patch_grid`
- Live Generators: Dust Saboteur (`dust_saboteur`), Pain Circuit (`bio_pain_circuit_01`), Waste Recycler (`bio_waste_recycler_01`)

### Lag (`status_lag_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Modify the next card cost by 1.
- Visual Flavor: A buffering ring or progress bar frozen mid-load with drag arrows. Abstract UI hazard imagery is fine here.
- Theme Lens: faction `shared`, palette `starter_neutral`, art style `signal_mesh`
- Live Generators: Signal Junker (`signal_junker`), Unsafe Overclock (`drift_unsafe_overclock_01`)

## Run Modifier Statuses

### Echo (`echo`)

- Description: The first card you play each combat repeats.
- Visual Flavor: A mirrored waveform token with duplicate edges and a pale afterimage trailing behind it.
- Rarity: `special`
- Base Weight: `2`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `offense`, `scaling`, `blessing`
- Hooks:
  - `passive`
    - The first card you play each combat repeats.

### Efficient (`efficient`)

- Description: The first card each combat costs 0.
- Visual Flavor: A clean zero-cost command chip with trimmed edges, teal timing marks, and perfect economy.
- Rarity: `special`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `blessing`
- Hooks:
  - `passive`
    - The first card each combat costs 0.

### Glitch State (`glitch_state`)

- Description: Each combat begins with a random glitch.
- Visual Flavor: A corrupted status badge of jittering pixels, split colors, and unstable signal tears.
- Rarity: `special`
- Base Weight: `2`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `volatility`, `risk`, `event`
- Hooks:
  - `combat_start`
    - Random one of: Glitch surge: +1 Energy. | Glitch buffer: Gain 6 Block. | Glitch cache: Draw 1. | Glitch backlash: Lose 4 HP.

### Momentum (`momentum`)

- Description: Attack cards deal 3 extra damage if you attacked last turn.
- Visual Flavor: A forward-tilted speed emblem of rev bars and attack chevrons, always leaning into the next hit.
- Rarity: `special`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `offense`, `scaling`, `blessing`
- Hooks:
  - `passive`
    - If you attacked last turn, Attack cards deal 3 extra damage.

### Stim Boost (`stim_boost`)

- Description: Next 3 combats: start with 1 extra Energy.
- Visual Flavor: A compact stim cartridge with fresh green charge, timer ticks, and combat-prep seals.
- Rarity: `special`
- Base Weight: `6`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `blessing`, `event`
- Duration: `{"type": "combat", "value": 3}`
- Stack Behavior: `refresh_duration`
- Hooks:
  - `combat_start`
    - Gain 1 Energy.

### System Corruption (`system_corruption`)

- Description: Next combat: lose 4 HP at the start.
- Visual Flavor: A sickly warning badge with corrupt code bleed, dead pixels, and damage-start alert lines.
- Rarity: `special`
- Base Weight: `4`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `volatility`, `risk`, `curse`, `event`
- Duration: `{"type": "combat", "value": 1}`
- Stack Behavior: `refresh_duration`
- Hooks:
  - `combat_start`
    - Take 4 damage.
