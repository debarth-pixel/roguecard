# Enemies Master Reference

Generated from `data/enemies.json`.

- Total enemies: **47**

## blackwire_directorate

### Audit Hound (`audit_hound`)

- Faction: `blackwire_directorate`
- Role / Tier: `elite` / `elite`
- Max HP: `64`
- Tags: `anti_combo`, `tracker`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Marked, Suppressed, Strip Buff
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `trace_bite`: Bite for 9 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 9 damage to default.
      - Apply 1 Marked to default.
  - `ledger_sweep`: Sweep for 8 and strip one buff
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
      - Strip a removable player buff from default.
  - `compliance_leap`: Leap for 10 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Apply 1 Suppressed to default.

### Compliance Engine AX-9 (`compliance_engine_ax9`)

- Faction: `blackwire_directorate`
- Role / Tier: `boss` / `boss`
- Max HP: `165`
- Tags: `shield`, `machine`, `suppression`
- Bark Profile: `compliance_engine_ax9`
- Summon IDs: None
- Special Mechanics: Suppressed, Strip Buff, Summoning, Phase change
- Phase Rules:
  - `overdrive` at <= 0.5 HP ratio -> pattern ['overdrive_cannon', 'barrier_cycle', 'null_wave', 'overdrive_cannon']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `barrier_cycle`: Gain 16 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 16 Block.
  - `pacify_burst`: Burst for 13 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 13 damage to default.
      - Apply 1 Suppressed to default.
  - `deploy_node`: Deploy a Sentry Node
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `sentry_node`.
  - `null_wave`: Wave for 8 and strip one buff
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
      - Strip a removable player buff from default.
  - `overdrive_cannon`: Cannon for 18
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 18 damage to default.

### Director Vale (`director_vale`)

- Faction: `blackwire_directorate`
- Role / Tier: `boss` / `boss`
- Max HP: `145`
- Tags: `suppression`, `commander`, `drone`
- Bark Profile: `director_vale`
- Summon IDs: None
- Special Mechanics: Marked, Suppressed, Strip Buff, Summoning, Phase change
- Phase Rules:
  - `kill_authority` at <= 0.5 HP ratio -> pattern ['kill_authority', 'tracked', 'deploy_kill_asset', 'kill_authority']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `tracked`: Apply 2 Marked
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 2 Marked to default.
  - `revoke`: Revoke for 9 and strip one buff
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 9 damage to default.
      - Strip a removable player buff from default.
  - `deploy_kill_asset`: Deploy a Patrol Drone
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `patrol_drone`.
  - `lockdown`: Lockdown for 12 and Suppress 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
      - Apply 2 Suppressed to default.
  - `kill_authority`: Authority fire for 16
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 16 damage to default.
      - Strip a removable player buff from default.

### Null Baton Officer (`null_baton_officer`)

- Faction: `blackwire_directorate`
- Role / Tier: `specialist` / `normal`
- Max HP: `34`
- Tags: `buff_strip`, `suppress`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Suppressed, Strip Buff
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `null_strike`: Strike for 6 and strip one buff
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 6 damage to default.
      - Strip a removable player buff from default.
  - `pressure_hit`: Hit for 7 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.
      - Apply 1 Suppressed to default.

### Patrol Drone (`patrol_drone`)

- Faction: `blackwire_directorate`
- Role / Tier: `utility` / `normal`
- Max HP: `22`
- Tags: `mark`, `summon`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Marked
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `tag_ping`: Ping for 3 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 3 damage to default.
      - Apply 1 Marked to default.
  - `pulse`: Pulse for 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.

### Riot Guard (`riot_guard`)

- Faction: `blackwire_directorate`
- Role / Tier: `frontline` / `normal`
- Max HP: `46`
- Tags: `shield`, `guard`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Suppressed
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `shield_wall`: Gain 10 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
  - `bash`: Bash for 7 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.
      - Apply 1 Suppressed to default.

### Sentry Node (`sentry_node`)

- Faction: `blackwire_directorate`
- Role / Tier: `summoned_support` / `normal`
- Max HP: `12`
- Tags: `summon`, `fortified`, `machine`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `laser_ping`: Ping for 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
  - `field_screen`: Grant 5 Block
    - Target: `lowest_hp_ally`
    - Cooldown: `0`
    - Effects:
      - Gain 5 Block.

### Signal Analyst (`signal_analyst`)

- Faction: `blackwire_directorate`
- Role / Tier: `controller` / `normal`
- Max HP: `28`
- Tags: `mark`, `amplify`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Marked, Suppressed
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `tracking_lock`: Apply 2 Marked
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 2 Marked to default.
  - `signal_burst`: Burst for 4 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Marked to default.
  - `suppress_route`: Apply Suppressed 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 1 Suppressed to default.

### Suppression Sniper (`suppression_sniper`)

- Faction: `blackwire_directorate`
- Role / Tier: `ranged` / `elite`
- Max HP: `38`
- Tags: `telegraph`, `burst`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Marked
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `aim`: Gain 6 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 6 Block.
  - `execution_round`: Fire for 16
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"player_status_at_least": {"status": "marked", "value": 1}}`
    - Effects:
      - Deal 16 damage to default.
  - `tag_shot`: Shot for 9 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 9 damage to default.
      - Apply 1 Marked to default.

### Turret Handler (`turret_handler`)

- Faction: `blackwire_directorate`
- Role / Tier: `deploy_support` / `normal`
- Max HP: `33`
- Tags: `summon`, `turret`
- Bark Profile: `blackwire_directorate`
- Summon IDs: None
- Special Mechanics: Summoning
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `deploy_drone`: Deploy a Sentry Node
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `sentry_node`.
  - `service_pistol`: Fire for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
  - `reinforce`: Gain 7 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 7 Block.

## cinder_jackals

### Ashfang Rook (`ashfang_rook`)

- Faction: `cinder_jackals`
- Role / Tier: `boss` / `boss`
- Max HP: `146`
- Tags: `momentum`, `war_chief`, `summon`
- Bark Profile: `ashfang_rook`
- Summon IDs: None
- Special Mechanics: Strength gain, Summoning, Phase change
- Phase Rules:
  - `all_out` at <= 0.45 HP ratio -> pattern ['all_out', 'pack_in', 'all_out', 'blood_hot']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `pack_in`: Call two Scavvers
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 2 `scavver`.
  - `blood_hot`: Hit for 10 and gain 1 Strength
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Gain 1 Strength.
  - `cleaver_rush`: Rush for 12
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
  - `crowd_surge`: Surge for 14
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Deal 14 damage to default.
  - `all_out`: All-out strike for 18
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 18 damage to default.

### Burner (`burner`)

- Faction: `cinder_jackals`
- Role / Tier: `bomber` / `normal`
- Max HP: `22`
- Tags: `burn`, `volatile`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: Burn
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `ember_jar`: Jar for 5 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
      - Apply 1 Burn to default.
  - `detonate`: Detonate for 8 and Burn 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
      - Apply 2 Burn to default.

### Burner Mite (`burner_mite`)

- Faction: `cinder_jackals`
- Role / Tier: `summoned_fodder` / `normal`
- Max HP: `10`
- Tags: `summon`, `burn`, `volatile`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: Burn, Self-destruct
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `spark_bite`: Bite for 4 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Burn to default.
  - `flash_pop`: Flash for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
      - Self-destruct.

### Chain Brute (`chain_brute`)

- Faction: `cinder_jackals`
- Role / Tier: `bruiser` / `normal`
- Max HP: `56`
- Tags: `heavy`, `momentum`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `wind_up`: Gain 8 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 8 Block.
  - `crush`: Crush for 12
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
  - `rush_crush`: Rush crush for 15
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Deal 15 damage to default.

### Dust Knife (`dust_knife`)

- Faction: `cinder_jackals`
- Role / Tier: `skirmisher` / `normal`
- Max HP: `24`
- Tags: `fast`, `bleed`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `flurry`: Cut twice for 3
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 3 damage to default 2 times.
  - `hook_cut`: Hook cut for 7
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.

### Furnace Hound (`furnace_hound`)

- Faction: `cinder_jackals`
- Role / Tier: `boss` / `boss`
- Max HP: `170`
- Tags: `siege`, `machine`, `burn`
- Bark Profile: `furnace_hound`
- Summon IDs: None
- Special Mechanics: Burn, Strength gain, Summoning, Phase change
- Phase Rules:
  - `overheat` at <= 0.5 HP ratio -> pattern ['overheat_ram', 'loose_mites', 'incinerate', 'overheat_ram']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `loose_mites`: Loose two Burner Mites
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 2 `burner_mite`.
  - `artillery_prep`: Gain 10 Block and 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
      - Gain 1 Strength.
  - `incinerate`: Incinerate for 10 and Burn 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Apply 2 Burn to default.
  - `ram`: Ram for 15
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 15 damage to default.
  - `overheat_ram`: Overheat ram for 19
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 19 damage to default.

### Road Hyena (`road_hyena`)

- Faction: `cinder_jackals`
- Role / Tier: `beast` / `normal`
- Max HP: `28`
- Tags: `pack`, `fast`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `bite`: Bite for 6
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 6 damage to default.
  - `feast`: Feast for 9
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"player_hp_below_ratio": 0.5}`
    - Effects:
      - Deal 9 damage to default.

### Scavver (`scavver`)

- Faction: `cinder_jackals`
- Role / Tier: `fodder` / `normal`
- Max HP: `18`
- Tags: `swarm`, `momentum`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `slash`: Slash for 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
  - `mob_rush`: Rush for 6
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Deal 6 damage to default.

### Scrap Caller (`scrap_caller`)

- Faction: `cinder_jackals`
- Role / Tier: `summoner` / `normal`
- Max HP: `30`
- Tags: `pack`, `spawn`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: Strength gain, Summoning
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `call_scavver`: Call a Scavver
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `scavver`.
  - `pack_jab`: Jab for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
  - `whip_up`: Gain 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 1 Strength.

### Scrap Gunner (`scrap_gunner`)

- Faction: `cinder_jackals`
- Role / Tier: `elite` / `elite`
- Max HP: `52`
- Tags: `ranged`, `swingy`
- Bark Profile: `cinder_jackals`
- Summon IDs: None
- Special Mechanics: Burn
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `snap_fire`: Fire for 11
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 11 damage to default.
  - `wild_burst`: Burst for 14
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Deal 14 damage to default.
  - `cover_flame`: Fire for 7 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.
      - Apply 1 Burn to default.

## grayspine_general

### Junction-9 Sentinel (`junction_9_sentinel`)

- Faction: `grayspine_general`
- Role / Tier: `boss` / `boss`
- Max HP: `150`
- Tags: `general`, `machine`, `defense`
- Bark Profile: `junction_9_sentinel`
- Summon IDs: None
- Special Mechanics: Marked
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `defense_mode`: Gain 14 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 14 Block.
  - `heavy_charge`: Charge for 16
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 16 damage to default.
  - `scan_burst`: Burst for 8 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
      - Apply 1 Marked to default.

### Spine Warden Null (`spine_warden_null`)

- Faction: `grayspine_general`
- Role / Tier: `boss` / `boss`
- Max HP: `160`
- Tags: `general`, `adaptive`, `guardian`
- Bark Profile: `spine_warden_null`
- Summon IDs: None
- Special Mechanics: Suppressed
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `pattern_lock`: Gain 10 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
  - `veto_wave`: Wave for 10 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Apply 1 Suppressed to default.
  - `null_barrage`: Barrage for 15
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 15 damage to default.

### The Toll Reeve (`toll_reeve`)

- Faction: `grayspine_general`
- Role / Tier: `boss` / `boss`
- Max HP: `132`
- Tags: `general`, `tax`, `disruption`
- Bark Profile: `toll_reeve`
- Summon IDs: None
- Special Mechanics: Suppressed, Strip Buff
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `gate_tax`: Tax hit for 10 and strip one buff
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Strip a removable player buff from default.
  - `muscle_wall`: Gain 12 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 12 Block.
  - `resource_cut`: Hit for 9 and Suppress 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 9 damage to default.
      - Apply 1 Suppressed to default.

## helix_ward

### Culture Shepherd (`culture_shepherd`)

- Faction: `helix_ward`
- Role / Tier: `summoner` / `normal`
- Max HP: `34`
- Tags: `spawn`, `harvest`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Infection, Strength gain, Summoning, Ally-death passive
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects:
  - Heal self for 4 HP.
  - Gain 1 Strength.
- Moves:
  - `brood_release`: Summon a Sludge Whelp
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `sludge_whelp`.
  - `sludge_whip`: Whip for 5 and Infect 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
      - Apply 1 Infection to default.
  - `siphon`: Heal 5
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Heal default for 5 HP.

### Failed Saint (`failed_saint`)

- Faction: `helix_ward`
- Role / Tier: `elite` / `elite`
- Max HP: `68`
- Tags: `mutate`, `horror`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Strength gain, Summoning, Phase change, Ally-death passive
- Phase Rules:
  - `awakened` at <= 0.5 HP ratio -> pattern ['mutant_bloom', 'graft_maul', 'spill_residue', 'mutant_bloom']
- Death Effects: None
- Ally-Death Effects:
  - Gain 1 Strength.
- Moves:
  - `hushed_advance`: Gain 8 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 8 Block.
  - `graft_maul`: Maul for 12
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
  - `spill_residue`: Summon a Sludge Whelp
    - Target: `self`
    - Cooldown: `2`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `sludge_whelp`.
  - `mutant_bloom`: Bloom for 10 and heal 10
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Heal self for 10 HP.
      - Gain 1 Strength.

### Gland Brute (`gland_brute`)

- Faction: `helix_ward`
- Role / Tier: `bruiser` / `normal`
- Max HP: `54`
- Tags: `frontline`, `mutate`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Infection, Strength gain, Phase change
- Phase Rules:
  - `mutated` at <= 0.5 HP ratio -> pattern ['mutant_rend', 'mutant_guard', 'mutant_rend']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `toxin_crash`: Crash for 11 and Infect 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 11 damage to default.
      - Apply 1 Infection to default.
  - `brace_tissue`: Gain 8 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 8 Block.
  - `mutant_rend`: Mutant Rend for 14 and Infect 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 14 damage to default.
      - Apply 2 Infection to default.
  - `mutant_guard`: Gain 10 Block and 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
      - Gain 1 Strength.

### Leech Nurse (`leech_nurse`)

- Faction: `helix_ward`
- Role / Tier: `drain_support` / `elite`
- Max HP: `42`
- Tags: `siphon`, `cleanse`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Cleanse
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `transfusion`: Heal an ally for 8
    - Target: `most_damaged_ally`
    - Cooldown: `0`
    - Conditions: `{"any_ally_missing_hp": true}`
    - Effects:
      - Heal default for 8 HP.
  - `siphon`: Drain for 6 and heal 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 6 damage to default.
      - Heal self for 4 HP.
  - `purge_serum`: Cleanse an ally
    - Target: `most_debuffed_ally`
    - Cooldown: `0`
    - Conditions: `{"any_ally_debuffed": true}`
    - Effects:
      - Cleanse up to 2 debuff stacks from default.

### Miremother Vexa (`miremother_vexa`)

- Faction: `helix_ward`
- Role / Tier: `boss` / `boss`
- Max HP: `140`
- Tags: `summoner`, `mutate`, `harvest`
- Bark Profile: `miremother_vexa`
- Summon IDs: None
- Special Mechanics: Infection, Strength gain, Summoning, Phase change, Ally-death passive
- Phase Rules:
  - `unstable_design` at <= 0.45 HP ratio -> pattern ['stress_bloom', 'field_trial', 'culture_harvest', 'stress_bloom']
- Death Effects: None
- Ally-Death Effects:
  - Heal self for 4 HP.
  - Gain 1 Strength.
- Moves:
  - `field_trial`: Summon two Sludge Whelps
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 2 `sludge_whelp`.
  - `serum_lance`: Lance for 10 and Infect 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 10 damage to default.
      - Apply 2 Infection to default.
  - `culture_harvest`: Heal 10 and gain 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Heal default for 10 HP.
      - Gain 1 Strength.
  - `rupture_command`: Rupture for 8 and summon one Whelp
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Deal 8 damage to default.
      - Summon 1 `sludge_whelp`.
  - `stress_bloom`: Bloom for 14 and Infect 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 14 damage to default.
      - Apply 2 Infection to default.
      - Summon 1 `sludge_whelp`.

### Scalpel Runner (`scalpel_runner`)

- Faction: `helix_ward`
- Role / Tier: `skirmisher` / `normal`
- Max HP: `24`
- Tags: `fast`, `infect`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `slice`: Slice twice for 3
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 3 damage to default 2 times.
  - `infected_lunge`: Lunge for 7
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"player_status_at_least": {"status": "infect", "value": 1}}`
    - Effects:
      - Deal 7 damage to default.

### Serum Acolyte (`serum_acolyte`)

- Faction: `helix_ward`
- Role / Tier: `support` / `normal`
- Max HP: `30`
- Tags: `heal`, `buff`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Infection, Strength gain
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `stabilize`: Heal an ally for 7
    - Target: `most_damaged_ally`
    - Cooldown: `0`
    - Conditions: `{"any_ally_missing_hp": true}`
    - Effects:
      - Heal default for 7 HP.
  - `tox_shot`: Sting for 4 and Infect 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Infection to default.
  - `catalyze`: Gain 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 1 Strength.

### Sludge Whelp (`sludge_whelp`)

- Faction: `helix_ward`
- Role / Tier: `fodder` / `normal`
- Max HP: `18`
- Tags: `summon`, `toxic`
- Bark Profile: `helix_ward`
- Summon IDs: None
- Special Mechanics: Infection, Death effect
- Phase Rules: None
- Death Effects:
  - Apply 1 Infection to player.
- Ally-Death Effects: None
- Moves:
  - `nibble`: Nibble for 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
  - `seep`: Seep for 2 and Infect 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 2 damage to default.
      - Apply 1 Infection to default.

### The Graft Saint (`graft_saint`)

- Faction: `helix_ward`
- Role / Tier: `boss` / `boss`
- Max HP: `155`
- Tags: `regenerate`, `horror`, `mutate`
- Bark Profile: `graft_saint`
- Summon IDs: None
- Special Mechanics: Burn, Strength gain, Phase change
- Phase Rules:
  - `martyr_form` at <= 0.5 HP ratio -> pattern ['violent_surge', 'devotional_crush', 'sealing_flesh', 'toxic_spasm']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `graft_wall`: Gain 12 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 12 Block.
  - `devotional_crush`: Crush for 14
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 14 damage to default.
  - `sealing_flesh`: Regenerate 12
    - Target: `self`
    - Cooldown: `2`
    - Conditions: `{"self_hp_below_ratio": 0.9}`
    - Effects:
      - Heal default for 12 HP.
  - `toxic_spasm`: Spasm for 9 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 9 damage to default.
      - Apply 1 Burn to default.
  - `violent_surge`: Surge for 18
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 18 damage to default.
      - Gain 1 Strength.

## legacy

### Corporate Enforcer (`enemy_elite_01`)

- Faction: `legacy`
- Role / Tier: `elite` / `elite`
- Max HP: `65`
- Tags: `legacy`
- Bark Profile: None
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `press`: Attack for 8
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
  - `brace`: Gain 7 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 7 Block.

### District Overlord (`enemy_boss_01`)

- Faction: `legacy`
- Role / Tier: `boss` / `boss`
- Max HP: `110`
- Tags: `legacy`
- Bark Profile: None
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `smash`: Attack for 12
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
  - `brace`: Gain 10 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
  - `crush`: Attack for 14
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 14 damage to default.

### Street Punk (`enemy_basic_01`)

- Faction: `legacy`
- Role / Tier: `basic` / `normal`
- Max HP: `40`
- Tags: `legacy`
- Bark Profile: None
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `jab`: Attack for 6
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 6 damage to default.
  - `brace`: Gain 5 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 5 Block.

## red_wastes

### Caravan Reaver (`caravan_reaver`)

- Faction: `red_wastes`
- Role / Tier: `bruiser` / `elite`
- Max HP: `50`
- Tags: `bleed`, `hunter`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Bleed
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `chain_hook`: Hook for 7 and Bleed 2
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.
      - Apply 2 Bleed to default.
  - `maul`: Maul for 11
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 11 damage to default.
  - `blood_scent`: Scent for 14
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"player_status_at_least": {"status": "bleed", "value": 1}}`
    - Effects:
      - Deal 14 damage to default.

### Carrion Hound (`carrion_hound`)

- Faction: `red_wastes`
- Role / Tier: `beast` / `normal`
- Max HP: `26`
- Tags: `pack`, `bleed`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Bleed
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `bite`: Bite for 6
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 6 damage to default.
  - `hamstring`: Hamstring for 4 and Bleed 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Bleed to default.

### Dune Raider (`dune_raider`)

- Faction: `red_wastes`
- Role / Tier: `skirmisher` / `normal`
- Max HP: `24`
- Tags: `fast`, `weak`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Weak
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `shiv`: Slash for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
  - `sand_throw`: Throw for 3 and Weak 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 3 damage to default.
      - Apply 1 Weak to default.

### Dust Saboteur (`dust_saboteur`)

- Faction: `red_wastes`
- Role / Tier: `support` / `normal`
- Max HP: `28`
- Tags: `clog`, `scavenger`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Status-card injection
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `scrap_dump`: Dump for 3 and add Junk to discard
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 3 damage to default.
      - Add 1 `status_junk_01` status card to the player's discard.
  - `cut_wire`: Cut for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
  - `duck_cover`: Gain 5 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 5 Block.

### Embersnout (`embersnout`)

- Faction: `red_wastes`
- Role / Tier: `bomber` / `normal`
- Max HP: `22`
- Tags: `burn`, `volatile`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Burn, Strength gain
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `cinder_spit`: Spit for 4 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Burn to default.
  - `flare_hide`: Gain 4 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 4 Block.
  - `fire_up`: Gain 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 1 Strength.

### Relay Vulture (`relay_vulture`)

- Faction: `red_wastes`
- Role / Tier: `ranged` / `normal`
- Max HP: `23`
- Tags: `mark`, `burst`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Marked
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `sightline`: Apply 1 Marked
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 1 Marked to default.
  - `dive_fire`: Fire for 8
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"player_status_at_least": {"status": "marked", "value": 1}}`
    - Effects:
      - Deal 8 damage to default.
  - `peck`: Peck for 5
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.

### Salvage Bulwark (`salvage_bulwark`)

- Faction: `red_wastes`
- Role / Tier: `frontline` / `normal`
- Max HP: `36`
- Tags: `guard`, `plated`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: None
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `brace_plate`: Gain 8 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 8 Block.
  - `ram`: Ram for 7
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.

### Sandpack Alpha (`sandpack_alpha`)

- Faction: `red_wastes`
- Role / Tier: `boss` / `boss`
- Max HP: `118`
- Tags: `beast`, `pack`, `bleed`, `summon`
- Bark Profile: `sandpack_alpha`
- Summon IDs: None
- Special Mechanics: Bleed, Strength gain, Summoning, Phase change
- Phase Rules:
  - `blood_moon` at <= 0.45 HP ratio -> pattern ['blood_surge', 'call_hound', 'alpha_maul', 'rake']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `call_hound`: Call a Carrion Hound
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `carrion_hound`.
  - `rake`: Rake for 8 and Bleed 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 8 damage to default.
      - Apply 1 Bleed to default.
  - `alpha_maul`: Maul for 13
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 13 damage to default.
  - `blood_surge`: Surge for 16
    - Target: `player`
    - Cooldown: `0`
    - Conditions: `{"any_other_ally_present": true}`
    - Effects:
      - Deal 16 damage to default.
  - `feral_focus`: Gain 1 Strength
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 1 Strength.

### Scrap Ticker (`scrap_ticker`)

- Faction: `red_wastes`
- Role / Tier: `utility` / `normal`
- Max HP: `18`
- Tags: `mark`, `machine`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Marked
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `target_ping`: Ping for 2 and Mark 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 2 damage to default.
      - Apply 1 Marked to default.
  - `buzz_saw`: Buzz for 4
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.

### Signal Junker (`signal_junker`)

- Faction: `red_wastes`
- Role / Tier: `controller` / `elite`
- Max HP: `44`
- Tags: `null`, `clog`, `tracker`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Status-card injection, Marked, Nullified
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `dead_channel`: Apply 1 Nullified
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply Nullified to default.
  - `lag_spike`: Spike for 5 and add Lag to discard
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 5 damage to default.
      - Add 1 `status_lag_01` status card to the player's discard.
  - `paint_lock`: Apply 1 Marked
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 1 Marked to default.

### Waste Leech (`waste_leech`)

- Faction: `red_wastes`
- Role / Tier: `parasite` / `normal`
- Max HP: `24`
- Tags: `infect`, `siphon`
- Bark Profile: `red_wastes`
- Summon IDs: None
- Special Mechanics: Infection
- Phase Rules: None
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `sip`: Sip for 4 and Infect 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 4 damage to default.
      - Apply 1 Infection to default.
  - `coil`: Gain 5 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 5 Block.
  - `gorge`: Heal 4
    - Target: `self`
    - Cooldown: `0`
    - Conditions: `{"self_hp_below_ratio": 0.7}`
    - Effects:
      - Heal self for 4 HP.

### Wastes Colossus (`wastes_colossus`)

- Faction: `red_wastes`
- Role / Tier: `boss` / `boss`
- Max HP: `124`
- Tags: `machine`, `mark`, `burn`, `summon`
- Bark Profile: `wastes_colossus`
- Summon IDs: None
- Special Mechanics: Burn, Marked, Summoning, Phase change
- Phase Rules:
  - `overdrive` at <= 0.5 HP ratio -> pattern ['flare_vent', 'searchlight', 'grinding_tread', 'loose_tickers', 'grinding_tread']
- Death Effects: None
- Ally-Death Effects: None
- Moves:
  - `sand_plating`: Gain 10 Block
    - Target: `self`
    - Cooldown: `0`
    - Effects:
      - Gain 10 Block.
  - `searchlight`: Apply 2 Marked
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Apply 2 Marked to default.
  - `grinding_tread`: Tread for 12
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 12 damage to default.
  - `flare_vent`: Vent for 7 and Burn 1
    - Target: `player`
    - Cooldown: `0`
    - Effects:
      - Deal 7 damage to default.
      - Apply 1 Burn to default.
  - `loose_tickers`: Loose a Scrap Ticker
    - Target: `self`
    - Cooldown: `1`
    - Conditions: `{"living_enemies_below": 5}`
    - Effects:
      - Summon 1 `scrap_ticker`.
