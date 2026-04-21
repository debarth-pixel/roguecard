# Relics Master Reference

Generated from `data/run_modifiers.json`.

- Total relics: **19**
- Non-relic modifier types excluded from the main list: `blessing` x8, `curse` x9, `status` x6

## common

### Butcher Hooks (`butcher_hooks`)

- Description: The first time each turn you apply Bleed, deal 3 damage to that enemy.
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `bleed`, `offense`
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `bleed` Deal 3 damage to the triggering enemy.

### Carbon Weave (`carbon_weave`)

- Description: Start each combat with 5 Block.
- Base Weight: `9`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `defense`, `blessing`
- Hooks:
  - `combat_start`
    - Gain 5 Block.

### Field Dampener (`field_dampener`)

- Description: The first time each combat you gain Burn, Bleed, Infect, Suppressed, or Nullified, gain 5 Block.
- Base Weight: `7`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `defense`, `enemy_status`
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `burn`, `bleed`, `infect`, `suppressed`, `nullified` Gain 5 Block.

### Flash Cache (`flash_cache`)

- Description: Draw 1 extra card on turn 1.
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Hooks:
  - `turn_one`
    - Draw 1 card.

### Plated Grip (`plated_grip`)

- Description: Add Firewall to the starting deck.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `defense`, `blessing`
- Hooks:
  - `on_acquire`
    - Add `firewall_01`.

### Rot Battery (`rot_battery`)

- Description: The first time you draw a status card each turn, gain 3 Block.
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `defense`
- Hooks:
  - `on_status_drawn`
    - First each turn Gain 3 Block.

### Shard Seed (`shard_seed`)

- Description: Add Cache Draw to the starting deck.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Hooks:
  - `on_acquire`
    - Add `cache_draw_01`.

### Surge Fuse (`surge_fuse`)

- Description: Add Surge Strike to the starting deck.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `offense`, `blessing`
- Hooks:
  - `on_acquire`
    - Add `surge_strike_01`.

## rare

### Execution Array (`execution_array`)

- Description: The first time each turn you hit an enemy that has a combat status, deal 3 bonus damage and draw 1 card.
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `status`, `offense`, `draw`
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `weak`, `vulnerable`, `bleed`, `burn`, `infect` Deal 3 damage to the triggering enemy.
    - First each turn If target has `weak`, `vulnerable`, `bleed`, `burn`, `infect` Draw 1 card.

### Grave Lantern (`grave_lantern`)

- Description: Start each combat by applying 1 Weak and 1 Bleed to all enemies.
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `aoe`, `status`, `setup`
- Hooks:
  - `combat_start`
    - Apply 1 `weak` to all enemies.
    - Apply 1 `bleed` to all enemies.

### Signal Router (`signal_router`)

- Description: Card rewards show 1 extra choice.
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Hooks:
  - `on_reward`
    - Show 1 extra card reward choice.

## uncommon

### Clean Slate (`clean_slate`)

- Description: The first purge each run is free.
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `shop`, `blessing`
- Hooks:
  - `on_shop`
    - The first purge each run is free.

### Grave Pick (`grave_pick`)

- Description: The first enemy that dies each combat grants 1 Energy next turn.
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `kill`, `energy`
- Hooks:
  - `on_enemy_death`
    - First each combat Gain 1 Energy next turn.

### Jam Cycler (`jam_cycler`)

- Description: Whenever a status card is exhausted, deal 3 damage to a random enemy.
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `offense`
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Deal 3 damage to a random enemy.

### Market Key (`market_key`)

- Description: Shop card prices cost 15% less.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `economy`, `shop`, `blessing`
- Hooks:
  - `on_shop`
    - Reduce `card` prices by 15%.

### Null Damper (`null_damper`)

- Description: The first time each combat you would gain Suppressed or Nullified, prevent 1 stack and draw 1 card.
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `cleanse`
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `suppressed`, `nullified` Reduce the triggering player status by 1.
    - First each combat If status is `suppressed`, `nullified` Draw 1 card.

### Overclock Relay (`overclock_relay`)

- Description: Gain 1 extra Energy on turn 1.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `energy`, `blessing`
- Hooks:
  - `turn_one`
    - Gain 1 Energy.

### Pressure Sight (`pressure_sight`)

- Description: The first time each turn you apply Weak or Vulnerable, draw 1 card.
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `draw`
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `weak`, `vulnerable` Draw 1 card.

### Septic Reservoir (`septic_reservoir`)

- Description: At end of your turn, the enemy with the highest Infect gains 1 Infect.
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `infect`, `scaling`
- Hooks:
  - `turn_end`
    - The enemy with the highest `infect` gains 1 more `infect`.
