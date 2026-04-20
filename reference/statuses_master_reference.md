# Statuses Master Reference

Generated from combat/status code plus `data/cards.json` and `data/enemies.json`.

## Combat Statuses

### Strength (`strength`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Adds its value to outgoing attack damage.
- Clears / Decay: Persists until combat ends or another effect removes it.
- Who Can Apply It: Ashfang Rook (`ashfang_rook`), Culture Shepherd (`culture_shepherd`), Embersnout (`embersnout`), Failed Saint (`failed_saint`), Furnace Hound (`furnace_hound`), Gland Brute (`gland_brute`), Miremother Vexa (`miremother_vexa`), Sandpack Alpha (`sandpack_alpha`), Scrap Caller (`scrap_caller`), Serum Acolyte (`serum_acolyte`), The Graft Saint (`graft_saint`), Battle Roar (`enforcer_battle_roar_01`), Open Wound (`enforcer_open_wound_01`), Pain Circuit (`bio_pain_circuit_01`), Redline Core (`enforcer_redline_core_01`), War Engine (`enforcer_war_engine_01`), Enemy phase transitions such as Gland Brute and Graft Saint

### Weak (`weak`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Outgoing attack damage is reduced to 75% while Weak is active.
- Clears / Decay: Ticks down by 1 at the start of that unit's turn.
- Who Can Apply It: Dune Raider (`dune_raider`), Needle Ping (`operator_needle_ping_01`), Static Haze (`operator_static_haze_01`), Execution Array (`execution_array`), Grave Lantern (`grave_lantern`), Pressure Sight (`pressure_sight`)

### Vulnerable (`vulnerable`)

- Category: Core Combat Modifier
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`
- Effect: Incoming attack damage is increased by 50% while Vulnerable is active.
- Clears / Decay: Ticks down by 1 at the start of that unit's turn.
- Who Can Apply It: Crackdown (`enforcer_crackdown_01`), Execution Array (`execution_array`), Pressure Sight (`pressure_sight`)

### Infection (`infect`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At end of the afflicted unit's turn, it loses HP equal to Infection. If Infection is 6 or more, it takes 4 extra damage and resets to 3.
- Clears / Decay: Persists until combat ends or an explicit effect changes it.
- Who Can Apply It: Culture Shepherd (`culture_shepherd`), Gland Brute (`gland_brute`), Miremother Vexa (`miremother_vexa`), Serum Acolyte (`serum_acolyte`), Sludge Whelp (`sludge_whelp`), Waste Leech (`waste_leech`), Harvest Bite (`bio_harvest_bite_01`), Leech Jab (`bio_leech_jab_01`), Parasite Fang (`bio_parasite_fang_01`), Septic Round (`bio_septic_round_01`), Execution Array (`execution_array`), Field Dampener (`field_dampener`), Septic Reservoir (`septic_reservoir`)

### Burn (`burn`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At end of the afflicted unit's turn, it loses HP equal to Burn.
- Clears / Decay: Burn decays by 1 at end of turn until it reaches 0.
- Who Can Apply It: Burner (`burner`), Burner Mite (`burner_mite`), Embersnout (`embersnout`), Furnace Hound (`furnace_hound`), Scrap Gunner (`scrap_gunner`), The Graft Saint (`graft_saint`), Wastes Colossus (`wastes_colossus`), Execution Array (`execution_array`), Field Dampener (`field_dampener`)

### Bleed (`bleed`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: When the afflicted target is hit, it takes bonus damage equal to Bleed.
- Clears / Decay: Bleed drops by 1 each time the bonus damage triggers.
- Who Can Apply It: Caravan Reaver (`caravan_reaver`), Carrion Hound (`carrion_hound`), Sandpack Alpha (`sandpack_alpha`), Bash Protocol (`enforcer_bash_protocol_01`), Breaker Line (`enforcer_breaker_line_01`), Gouge (`enforcer_gouge_01`), Butcher Hooks (`butcher_hooks`), Execution Array (`execution_array`), Field Dampener (`field_dampener`), Grave Lantern (`grave_lantern`)

### Marked (`marked`)

- Category: Combat Status
- Lives In: `entities/player.py`, `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Blackwire attacks gain +2 damage per current Marked stack, then consume 1 stack on hit.
- Clears / Decay: Player Marked lasts up to 2 turns unless consumed sooner. Generic enemy-side counters persist until removed.
- Who Can Apply It: Audit Hound (`audit_hound`), Director Vale (`director_vale`), Junction-9 Sentinel (`junction_9_sentinel`), Patrol Drone (`patrol_drone`), Relay Vulture (`relay_vulture`), Scrap Ticker (`scrap_ticker`), Signal Analyst (`signal_analyst`), Signal Junker (`signal_junker`), Suppression Sniper (`suppression_sniper`), Wastes Colossus (`wastes_colossus`)

### Suppressed (`suppressed`)

- Category: Combat Status
- Lives In: `entities/player.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Attack cards deal 15% less damage per stack, with a minimum of 1 damage.
- Clears / Decay: Clears at the end of the player's turn. Player stacks are capped at 3.
- Who Can Apply It: Audit Hound (`audit_hound`), Compliance Engine AX-9 (`compliance_engine_ax9`), Director Vale (`director_vale`), Null Baton Officer (`null_baton_officer`), Riot Guard (`riot_guard`), Signal Analyst (`signal_analyst`), Spine Warden Null (`spine_warden_null`), The Toll Reeve (`toll_reeve`), Field Dampener (`field_dampener`), Null Damper (`null_damper`)

### Nullified (`nullified`)

- Category: Combat Status
- Lives In: `entities/player.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Blocks the next positive player combat gain: Block, positive Strength, positive next-attack bonus, or a negative next-card-cost modifier.
- Clears / Decay: Removes itself after blocking one eligible positive effect or when combat ends.
- Who Can Apply It: Signal Junker (`signal_junker`), Field Dampener (`field_dampener`), Null Damper (`null_damper`)

### Fortified (`fortified`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At the start of turn, gain Block equal to Fortified, capped at 12.
- Clears / Decay: Persists until combat ends or another effect removes it.
- Who Can Apply It: Spawn rules for Audit Hound, Sentry Node, Compliance Engine AX-9, and Junction-9 Sentinel, Director Vale's first drone or machine summon gets Fortified 4

### Regenerate (`regenerate`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: At the start of turn, heal HP equal to Regenerate.
- Clears / Decay: Consumes 1 stack after each start-of-turn heal.
- Who Can Apply It: Failed Saint phase transition grants Regenerate 3

### Momentum (`momentum`)

- Category: Combat Status
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Adds its value to the next outgoing enemy attack.
- Clears / Decay: Clears after that attack or at the end of the enemy's turn.
- Who Can Apply It: Cinder Jackals also gain Momentum from scripted ally-attack synergies such as Ashfang Rook's Blood Rally

### Overheat (`overheat`)

- Category: Boss Resource
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Stored heat resource used by Furnace Hound to scale Boiler Spit and Redline Charge.
- Clears / Decay: Boiler Spit consumes 1 Overheat. Redline Charge clears all Overheat. Furnace Hound gains 1 at end of each turn.
- Who Can Apply It: Furnace Hound end-of-turn passive gain

### Biomass (`biomass`)

- Category: Boss Resource
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Stored Helix boss resource used by Miremother Vexa to empower Biomass Collapse.
- Clears / Decay: Miremother Vexa clears Biomass after a thresholded Biomass Collapse.
- Who Can Apply It: Miremother Vexa gains Biomass when allied fodder dies

### Mutated (`mutated`)

- Category: Enemy Phase State
- Lives In: `entities/enemy.py`, `combat/combat_manager.py`, `ui/combat_ui.py`
- Effect: Marks an enemy as having crossed a phase threshold and switched to its phase-rule intent pattern.
- Clears / Decay: Persists for the rest of combat once applied.
- Who Can Apply It: Applied automatically by enemy phase transitions from enemies.json phase_rules

## Status Cards

### Burn (`status_burn_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Lose 2 HP.
- Live Generators: Rot Slash (`bio_rot_slash_01`)

### Glitch (`status_glitch_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Random one of: Glitch drains power. | Glitch bites back.
- Live Generators: None found in current data.

### Junk (`status_junk_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`
- Behavior: No direct effect.
- Live Generators: Dust Saboteur (`dust_saboteur`), Pain Circuit (`bio_pain_circuit_01`), Waste Recycler (`bio_waste_recycler_01`)

### Lag (`status_lag_01`)

- Owners: `shared`
- Cost: `0`
- Keywords: `combat_only`, `exhaust`
- Behavior: `on_draw` -> Modify the next card cost by 1.
- Live Generators: Signal Junker (`signal_junker`)
