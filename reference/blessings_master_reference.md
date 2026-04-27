# Blessings Master Reference

Generated from `data/run_modifiers.json`.

- Total entries: **10**

## Common

### Champion Contract (`champion_contract`)

- Description: Heal 5 after elite victories.
- Visual Flavor: A victor's contract slate signed in gold and pinned with a medal ribbon and a clean white seal.
- Rarity: `common`
- Base Weight: `7`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `recovery`, `blessing`
- Hooks:
  - `post_victory`
    - Heal 5 HP.

### Deep Pockets (`deep_pockets`)

- Description: Start the run with 25 credits.
- Visual Flavor: A hardened chip wallet overstuffed with stacked credit slugs and zipper rings pulling at the seams.
- Rarity: `common`
- Base Weight: `6`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `economy`, `blessing`
- Hooks:
  - `on_acquire`
    - Gain 25 credits.

### Patch Priority (`patch_priority`)

- Description: Shop heal service costs 6 less.
- Visual Flavor: A clinic priority band or service token with green cross lights and fast-track chevrons.
- Rarity: `common`
- Base Weight: `7`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `recovery`, `shop`, `blessing`
- Hooks:
  - `on_shop`
    - Reduce `heal` price by 6.

### Salvage License (`salvage_license`)

- Description: Gain 6 extra credits after normal combats.
- Visual Flavor: A stamped salvage permit card clipped to a chain, with brass corners and payout marks scratched into the surface.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `economy`, `blessing`
- Hooks:
  - `post_victory`
    - Gain 6 credits after `combat`.

## Uncommon

### Adrenal Surge (`adrenal_surge`)

- Description: Start each combat with 1 extra Energy.
- Visual Flavor: A snap-in combat stim ampoule and injector pen glowing with reckless orange charge and first-turn heat.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `offense`, `blessing`
- Hooks:
  - `combat_start`
    - Gain 1 Energy.

### Ghost Warranty (`ghost_warranty`)

- Description: The first reroll in each shop is free.
- Visual Flavor: A translucent warranty chip flickering with ghosted receipt text and shop-terminal glow.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `shop`, `blessing`
- Hooks:
  - `on_shop`
    - The first reroll in each shop is free.

### High Roller (`high_roller`)

- Description: Gain 8 extra credits after combat.
- Visual Flavor: A sharp-edged casino marker plated in gold and hazard red, flashy enough to promise winnings and trouble.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `economy`, `shop`, `risk`, `blessing`
- Downside: All shop prices cost 15% more.
- Hooks:
  - `post_victory`
    - Gain 8 credits after `combat`, `elite`.
  - `on_shop`
    - Increase `all` prices by 15%.

### Leaking Cell (`spare_battery_leaking_cell`)

- Description: For the next 2 combats, gain 1 extra Energy on turn 1.
- Visual Flavor: A taped battery cell leaking blue charge through a cracked casing, useful for exactly the wrong reasons.
- Rarity: `uncommon`
- Base Weight: `0`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `event`, `risk`
- Duration: `{"type": "combat", "value": 2}`
- Hooks:
  - `turn_one`
    - Gain 1 Energy.

### Street Choir (`street_choir`)

- Description: Heal 3 after each event resolves.
- Visual Flavor: A harmonic street speaker medallion threaded with tiny antenna forks and warm recovery light.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `recovery`, `event`, `blessing`
- Hooks:
  - `on_event`
    - Heal 3 HP after each event.

## Special

### Cassette Feed (`protocol_eclipse_cassette_feed`)

- Description: For the next 3 combats, the first Glitch you draw grants 1 extra Energy.
- Visual Flavor: A corrupted cassette spool feeding glitch tape into an eclipse-shaped protocol reader.
- Rarity: `special`
- Base Weight: `0`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `status`, `corruption`, `event`
- Duration: `{"type": "combat", "value": 3}`
- Hooks:
  - `on_status_drawn`
    - First each combat If card is `status_glitch_01` Gain 1 Energy.
