# Curses Master Reference

Generated from `data/run_modifiers.json`.

- Total entries: **9**

## Cursed

### Black Ice Scar (`black_ice_scar`)

- Description: Card rewards show 1 extra choice.
- Visual Flavor: A shard-black implant sliver with frosted blue edges and a permanent wound-line running through it.
- Rarity: `cursed`
- Base Weight: `2`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `draw`, `risk`, `curse`
- Downside: Lose 8 max HP.
- Hooks:
  - `on_acquire`
    - Adjust max HP by -8.
  - `on_reward`
    - Show 1 extra card reward choice.

### Blood Money (`blood_money`)

- Description: Gain 10 extra credits after every combat.
- Visual Flavor: A blood-smeared payout chit or brass coin purse with red ledger marks and a predatory shine.
- Rarity: `cursed`
- Base Weight: `3`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `economy`, `risk`, `curse`
- Downside: All healing is 25% weaker.
- Hooks:
  - `on_acquire`
    - Adjust healing multiplier by -25%.
  - `post_victory`
    - Gain 10 credits after `combat`, `elite`.

### Blood Pact (`blood_pact`)

- Description: Lose 8 HP. Reward cards show 1 extra choice.
- Visual Flavor: A ritual contract blade or oath tag tied with red cord and a still-wet thumbprint.
- Rarity: `cursed`
- Base Weight: `2`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `offense`, `risk`, `curse`
- Hooks:
  - `on_acquire`
    - Take 8 damage.
  - `on_reward`
    - Show 1 extra card reward choice.

### Debt Mark (`debt_mark`)

- Description: Lose 10 credits at each new floor.
- Visual Flavor: A stamped debtor brand plate with descending credit ticks and collection sigils.
- Rarity: `cursed`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `economy`, `risk`, `curse`
- Hooks:
  - `passive`
    - Lose 10 credits at each new floor.

### Debt Spike (`debt_spike`)

- Description: The first card purchase in each shop costs 8 more.
- Visual Flavor: A predatory finance spike or contract stylus with barbed edges and courier branding.
- Rarity: `cursed`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `shop`, `economy`, `curse`
- Hooks:
  - `on_shop`
    - The first card purchase in each shop costs 8 more.

### Fractured Armor (`fractured_armor`)

- Description: The first Block gain each combat is reduced by 4.
- Visual Flavor: A cracked armor plate held together by failing welds and stress braces.
- Rarity: `cursed`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `defense`, `risk`, `curse`
- Hooks:
  - `passive`
    - The first Block gain each combat is reduced by 4.

### Glass Engine (`glass_engine`)

- Description: Gain 1 extra Energy on turn 1.
- Visual Flavor: A fragile engine capsule of glass chambers and exposed pressure lines glowing with unstable power.
- Rarity: `cursed`
- Base Weight: `3`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `energy`, `risk`, `curse`
- Downside: Lose 12 max HP.
- Hooks:
  - `on_acquire`
    - Adjust max HP by -12.
  - `turn_one`
    - Gain 1 Energy.

### Lean Market (`lean_market`)

- Description: All shop prices cost 20% less.
- Visual Flavor: A bargain-market receipt roll wrapped around a cracked price gun and a starving little lockbox.
- Rarity: `cursed`
- Base Weight: `4`
- Draft Eligible: `False`
- Source Types: `run_start`
- Tags: `shop`, `economy`, `curse`
- Downside: Lose 10 max HP.
- Hooks:
  - `on_acquire`
    - Adjust max HP by -10.
  - `on_shop`
    - Reduce `all` prices by 20%.

### Overheat (`overheat`)

- Description: Cards cost 1 more after the first one each combat.
- Visual Flavor: A hazard-red heat regulator with warning needles buried in the danger zone.
- Rarity: `cursed`
- Base Weight: `5`
- Draft Eligible: `False`
- Source Types: `event`
- Tags: `energy`, `risk`, `curse`
- Hooks:
  - `passive`
    - Cards cost 1 more after the first one each combat.
