# Relics Master Reference

Generated from `data/run_modifiers.json`.

- Total entries: **65**
- Track breakdown: `legacy/untracked` x19, `drop_in` x28, `advanced` x18
- Related files: see `blessings_master_reference.md` for **10** blessings and `curses_master_reference.md` for **9** curses.
- Non-relic modifier types excluded from this list: `blessing` x10, `curse` x9, `status` x6

## common

### Ash Veil (`ash_veil`)

- Description: The first time each combat you gain Burn, gain 5 Block.
- Visual Flavor: A soot-black veil catching ember sparks along its hem as it dulls incoming burn.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `burn`, `defense`
- Track: `drop_in`
- Synergies: `Cinder Jackals / Red Wastes encounters`, `Field Dampener`
- Notes: A simple anti-burn pickup that still feels useful even at low stack counts.
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `burn` Gain 5 Block.

### Butcher Hooks (`butcher_hooks`)

- Description: The first time each turn you apply Bleed, deal 3 damage to that enemy.
- Visual Flavor: A pair of industrial butcher hooks on a cable hub, stained steel with one sharp red accent. Keep the silhouette simple enough to read as a small cutout icon.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `bleed`, `offense`
- Track: `legacy/untracked`
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `bleed` Deal 3 damage to the triggering enemy.

### Carbon Weave (`carbon_weave`)

- Description: Start each combat with 5 Block.
- Visual Flavor: A beveled square of carbon-fiber weave with stitched or riveted corners. Preserve the simple plate silhouette from the current sheet.
- Rarity: `common`
- Base Weight: `9`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `defense`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `combat_start`
    - Gain 5 Block.

### Field Dampener (`field_dampener`)

- Description: The first time each combat you gain Burn, Bleed, Infect, Suppressed, or Nullified, gain 5 Block.
- Visual Flavor: A palm-sized dampening puck or collar coil with concentric rings that absorb hostile status energy. Show containment, not offense.
- Rarity: `common`
- Base Weight: `7`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `defense`, `enemy_status`
- Track: `legacy/untracked`
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `burn`, `bleed`, `infect`, `suppressed`, `nullified` Gain 5 Block.

### Flash Cache (`flash_cache`)

- Description: Draw 1 extra card on turn 1.
- Visual Flavor: A compact datastick with a bright cyan cache core. Simple 3/4 angle, cutout-friendly.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `turn_one`
    - Draw 1 card.

### Grave Static (`grave_static`)

- Description: The first time each turn you draw a status card, deal 2 damage to a random enemy.
- Visual Flavor: A tomb-radio handset crackling with dead signal and status noise over a dark speaker grille.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `offense`
- Track: `drop_in`
- Synergies: `Waste Recycler`, `Rot Harvest`, `Jam Cycler`
- Notes: Makes status-card matchups feel less dead even before the deck is fully online.
- Hooks:
  - `on_status_drawn`
    - First each turn Deal 2 damage to a random enemy.

### Grave Toll (`grave_toll`)

- Description: The first enemy that dies each combat heals you for 3 HP.
- Visual Flavor: A small iron toll bell on a chain, worn smooth by deaths counted one at a time.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `kill`, `heal`
- Track: `drop_in`
- Synergies: `Swarm fights`, `Enforcer kill pressure`, `Bio self-damage decks`
- Notes: Intended to make summon-heavy fights feel like an opportunity as well as a threat.
- Hooks:
  - `on_enemy_death`
    - First each combat Heal 3 HP.

### Marker Scrambler (`marker_scrambler`)

- Description: The first time each combat you gain Marked, draw 1 card.
- Visual Flavor: A jammer disc fuzzing target reticles with static rings and scrambled white brackets.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `marked`, `draw`
- Track: `drop_in`
- Synergies: `Blackwire / Red Wastes tracker enemies`
- Notes: Marked is scary because it front-loads future damage; drawing a card feels like a tactical scramble.
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `marked` Draw 1 card.

### Open-Circuit Brand (`open_circuit_brand`)

- Description: The first time each turn you apply Bleed, gain 2 Block.
- Visual Flavor: A heated branding iron with a broken-circuit sigil and a live orange seam down the center.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `bleed`, `defense`
- Track: `drop_in`
- Synergies: `Enforcer Bleed package`, `Butcher Hooks`
- Notes: Pairs naturally with Gouge / Bash Protocol / Breaker Line without spiking damage too hard.
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `bleed` Gain 2 Block.

### Parasite Seal (`parasite_seal`)

- Description: The first time each combat you gain Infect, heal 3 HP.
- Visual Flavor: A quarantine seal stamped over a specimen vial and leech silhouette, forcing the infection back under glass.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `infect`, `cleanse`
- Track: `drop_in`
- Synergies: `Helix Ward / Waste Leech fights`, `Patch Kit`
- Notes: Softens Infect matchups without removing the pressure entirely.
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `infect` Heal 3 HP.

### Plated Grip (`plated_grip`)

- Description: Add Firewall to the starting deck.
- Visual Flavor: A plated armored glove with chunky defensive knuckles. One glove, no hand attached.
- Rarity: `common`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `defense`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_acquire`
    - Add `firewall_01`.

### Pressure Mesh (`pressure_mesh`)

- Description: The first time each turn you apply Weak or Vulnerable, gain 3 Block.
- Visual Flavor: A tension-reading mesh plate threaded with weak-point lines and defensive sensor nodes.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `defense`
- Track: `drop_in`
- Synergies: `Operator Weak tools`, `Enforcer Vulnerable tools`, `Pressure Sight`
- Notes: Lets control cards defend without needing extra text on the cards themselves.
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `weak`, `vulnerable` Gain 3 Block.

### Queue Mirror (`queue_mirror`)

- Description: The first 0-cost card you play each turn draws 1 card.
- Visual Flavor: A polished queue token reflecting a zero-cost icon back at itself in perfect symmetry.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `zero_cost`, `draw`, `combo`
- Track: `advanced`
- Synergies: `Priority Queue`, `Pain Probe`, `Reclaimer`, `Quiet Cut`, `Overclock`
- Notes: Great glue relic for both Operator and self-damage micro-combo decks.
- Hooks:
  - `after_card_played`
    - First each turn If played cost is `0` Draw 1 card.

### Riot Plating (`riot_plating`)

- Description: Start each combat with 1 Strength.
- Visual Flavor: A riot plate pauldron with bold power chevrons and heavy red surface wear.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `strength`, `offense`
- Track: `drop_in`
- Synergies: `Enforcer attack spam`, `multi-hit cards`, `Operator poke decks`
- Notes: Clean universal power bump; great baseline common reward.
- Hooks:
  - `combat_start`
    - Gain 1 Strength.

### Rot Battery (`rot_battery`)

- Description: The first time you draw a status card each turn, gain 3 Block.
- Visual Flavor: A corroded battery canister or cell with verdant seepage and stitched casing seams. This should feel bio-hacker adjacent but still relic-simple.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `defense`
- Track: `legacy/untracked`
- Hooks:
  - `on_status_drawn`
    - First each turn Gain 3 Block.

### Rot Index (`rot_index`)

- Description: The first time each turn a status card is added to your discard pile, draw 1 card.
- Visual Flavor: An infected index wheel or septic filing spindle dripping green from carefully labeled slots.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `draw`
- Track: `advanced`
- Synergies: `Waste Recycler`, `Pain Circuit`, `enemy junk / lag insertion`
- Notes: Lets status injection become an engine input, not just a tax.
- Hooks:
  - `on_status_card_added_to_discard`
    - First each turn Draw 1 card.

### Septic Siphon (`septic_siphon`)

- Description: The first time each turn you apply Infect, heal 1 HP.
- Visual Flavor: A glass siphon pump with thick infected fluid returning through a narrow medical line.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `infect`, `heal`
- Track: `drop_in`
- Synergies: `Bio Hacker Infect package`, `Septic Reservoir`, `Parasite Fang / Leech Jab / Harvest Bite / Septic Round`
- Notes: Small sustain glue for Infect decks; deliberately modest because Infect already scales over time.
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `infect` Heal 1 HP.

### Shard Seed (`shard_seed`)

- Description: Add Cache Draw to the starting deck.
- Visual Flavor: A green crystal seed nested in a dark industrial housing. Bright center crystal, restrained outer casing.
- Rarity: `common`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_acquire`
    - Add `cache_draw_01`.

### Surge Fuse (`surge_fuse`)

- Description: Add Surge Strike to the starting deck.
- Visual Flavor: A glass fuse tube holding a bright blue electrical surge. Keep the icon slim and high contrast.
- Rarity: `common`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `offense`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_acquire`
    - Add `surge_strike_01`.

### Waste Filter (`waste_filter`)

- Description: The first time each turn you draw a status card, heal 1 HP.
- Visual Flavor: A grimy filter mask or purifier canister pulling poison through layered mesh and clear waste tubes.
- Rarity: `common`
- Base Weight: `8`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `heal`
- Track: `drop_in`
- Synergies: `Rot Harvest`, `status-heavy fights`, `self-damage decks that need cushion`
- Notes: A gentle safety valve that keeps status synergies from being all-or-nothing.
- Hooks:
  - `on_status_drawn`
    - First each turn Heal 1 HP.

## uncommon

### Blood Indexer (`blood_indexer`)

- Description: At end of your turn, the enemy with the highest Bleed gains 1 Bleed.
- Visual Flavor: A blood-stained index wheel with tally teeth and red markers advancing toward overflow.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `bleed`, `scaling`
- Track: `drop_in`
- Synergies: `Butcher Hooks`, `Double Tap / Riot Barrage / Gouge`
- Notes: Parallel to Septic Reservoir so Bleed has its own slow cooker relic.
- Hooks:
  - `turn_end`
    - If status is `bleed` Increase the highest enemy `bleed` by 1.

### Bone Receipt (`bone_receipt`)

- Description: The first time each turn you lose HP from your own card or relic, gain 5 Block.
- Visual Flavor: A rigid receipt spike threaded with bone-white tabs and pain turned into a formal tally.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `self_damage`, `defense`
- Track: `advanced`
- Synergies: `Spare Organs`, `Reclaimer`, `Pain Probe`, `Hard Commit`, `Blood Rush`
- Notes: Makes self-harm turns safer without deleting their cost.
- Hooks:
  - `on_self_damage`
    - First each turn Gain 5 Block.

### Cinder Feedback (`cinder_feedback`)

- Description: Whenever Burn deals damage to you, deal 4 damage to a random enemy.
- Visual Flavor: A heat-damaged feedback coil wrapped in ash cloth, ready to spit stored fire back at the room.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `burn`, `retaliation`
- Track: `advanced`
- Synergies: `Ash Veil`, `Quarantine Vault`, `Burn-heavy enemy routes`
- Notes: A neat route-specific counterpick that can still matter in boss fights.
- Hooks:
  - `on_player_burn_tick`
    - Deal 4 damage to a random enemy.

### Clean Slate (`clean_slate`)

- Description: The first purge each run is free.
- Visual Flavor: A handheld tablet with a clean blue screen and a physical eraser block clipped to one edge. Readable and simple; almost stationery-tech.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `shop`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_shop`
    - The first purge each run is free.

### Containment Loop (`containment_loop`)

- Description: The first time each turn you hit an Infected enemy, gain 3 Block.
- Visual Flavor: A sealed containment collar ring with clear vials and a calm green lock light holding infection at bay.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `infect`, `defense`
- Track: `drop_in`
- Synergies: `Bio Hacker attacks`, `Septic Crown`, `Septic Reservoir`
- Notes: Supports the “slow poison, stay alive” Infect gameplan.
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `infect` Gain 3 Block.

### Execution Relay (`execution_relay`)

- Description: The first time each turn you hit a Bleeding enemy, draw 1 card.
- Visual Flavor: A lean kill-switch router with an optic eye and a clean relay path from status marker to finishing strike.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `bleed`, `draw`
- Track: `drop_in`
- Synergies: `Enforcer multi-hit attacks`, `Blood Indexer`
- Notes: Bleed becomes a hand-quality engine instead of just a damage rider.
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `bleed` Draw 1 card.

### Exposure Grid (`exposure_grid`)

- Description: The first time each turn you hit a Weak or Vulnerable enemy, deal 3 bonus damage.
- Visual Flavor: A projector puck casting a weak-point lattice over armor seams and opened targets.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `offense`
- Track: `drop_in`
- Synergies: `Static Haze`, `Needle Ping`, `Crackdown`
- Notes: Lets light control packages translate into damage without forcing more attack density.
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `weak`, `vulnerable` Deal 3 damage to the triggering enemy.

### Fresh Kill Chain (`fresh_kill_chain`)

- Description: The first enemy that dies each turn reduces the next card you play by 1 and gives your next attack +3 damage.
- Visual Flavor: A trophy chain loaded with kill tokens and sharpened clasps, built to spin one death into the next advantage.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `kill`, `cost_reduction`, `offense`
- Track: `advanced`
- Synergies: `swarm fights`, `Enforcer kill chains`, `Operator burst turns`
- Notes: Makes cleanup lethal in a very Slay-the-Spire way.
- Hooks:
  - `on_enemy_death`
    - First each turn Your next card cost changes by -1.
    - First each turn Your next attack deals 3 more damage.

### Ghost Budget (`ghost_budget`)

- Description: The first time each turn a card cost is reduced, gain 2 Block and your next attack deals 2 more damage.
- Visual Flavor: A translucent ledger chip with discount arrows, ghosted numerals, and a clean white spending lock.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `cost_reduction`, `defense`, `offense`
- Track: `advanced`
- Synergies: `Auto-Tuner`, `Backdoor`, `Priority Queue`, `Recompile Shot`, `Zero-Day Burst`
- Notes: A compact payoff for the Operator discount shell.
- Hooks:
  - `on_card_cost_reduced`
    - First each turn Gain 2 Block.
    - First each turn Your next attack deals 2 more damage.

### Grave Pick (`grave_pick`)

- Description: The first enemy that dies each combat grants 1 Energy next turn.
- Visual Flavor: A compact grave pick or powered miner's pick with a small energy cell in the shaft. Uncommon relic; simple but slightly mean.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `kill`, `energy`
- Track: `legacy/untracked`
- Hooks:
  - `on_enemy_death`
    - First each combat Gain 1 Energy next turn.

### Grave Sprinkler (`grave_sprinkler`)

- Description: The first enemy that dies each combat applies 1 Weak to all enemies.
- Visual Flavor: A funerary sprinkler head spraying red mist and pale weakening vapor in a cold circular pattern.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `kill`, `control`, `aoe`
- Track: `drop_in`
- Synergies: `Swarm fights`, `Operator tempo decks`, `Reaper Census`
- Notes: Rewards early cleanup and makes summon fights chain into safer turns.
- Hooks:
  - `on_enemy_death`
    - First each combat If status is `weak` Apply 1 `weak` to all enemies.

### Jam Battery (`jam_battery`)

- Description: Whenever a status card is exhausted, gain 2 Block.
- Visual Flavor: A thick battery block with spent status strips jammed into charging teeth along its spine.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `defense`
- Track: `drop_in`
- Synergies: `Rot Harvest`, `Cold Read / Overclock / status exhaust loops`
- Notes: Straightforward exhaust payoff with strong visual clarity.
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Gain 2 Block.

### Jam Cycler (`jam_cycler`)

- Description: Whenever a status card is exhausted, deal 3 damage to a random enemy.
- Visual Flavor: A grinder gearbox or cassette shredder with jammed status strips caught in its teeth. It should feel like it chews through status cards.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `offense`
- Track: `legacy/untracked`
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Deal 3 damage to a random enemy.

### Lag Harvest (`lag_harvest`)

- Description: The first time each turn you draw a status card, gain 1 Energy next turn.
- Visual Flavor: A slow-turn capacitor or hourglass battery fed by the drag and friction of status junk.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `energy`
- Track: `drop_in`
- Synergies: `Rot Harvest`, `Waste Recycler`, `enemy junk / lag pressure`
- Notes: Excellent in long fights; harmless in clean fights.
- Hooks:
  - `on_status_drawn`
    - First each turn Gain 1 Energy next turn.

### Market Ghost (`market_ghost`)

- Description: Shop relic prices cost 10% less.
- Visual Flavor: A phantom price tag or shop-spirit keyfob hovering with pale green markdown light.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `shop`
- Tags: `economy`, `shop`
- Track: `drop_in`
- Synergies: `Market Key`, `Clean Slate`, `long route planning`
- Notes: A distinct economy lane from Market Key so players can build shop-centric runs.
- Hooks:
  - `on_shop`
    - Reduce `relic` prices by 10%.

### Market Key (`market_key`)

- Description: Shop card prices cost 15% less.
- Visual Flavor: A brass-steel key with a green chip insert and secure cut teeth. Keep the shape elegant and iconic.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `economy`, `shop`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_shop`
    - Reduce `card` prices by 15%.

### Null Damper (`null_damper`)

- Description: The first time each combat you would gain Suppressed or Nullified, prevent 1 stack and draw 1 card.
- Visual Flavor: A blanking muffler coil or nullifier puck with a muted signal emblem. Control relic; feel suppressive and defensive.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `cleanse`
- Track: `legacy/untracked`
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `suppressed`, `nullified` Reduce player `None` by 1.
    - First each combat If status is `suppressed`, `nullified` Draw 1 card.

### Overclock Relay (`overclock_relay`)

- Description: Gain 1 extra Energy on turn 1.
- Visual Flavor: A heavy relay cube with a cooling fan, cables, and a small orange status LED. Preserve the squat box silhouette from the current sheet.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `energy`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `turn_one`
    - Gain 1 Energy.

### Pressure Sight (`pressure_sight`)

- Description: The first time each turn you apply Weak or Vulnerable, draw 1 card.
- Visual Flavor: A cyber monocle or tactical lens projecting a weak-point reticle. Let the lens shape dominate; only small UI accents.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `control`, `draw`
- Track: `legacy/untracked`
- Hooks:
  - `on_enemy_status_applied`
    - First each turn If status is `weak`, `vulnerable` Draw 1 card.

### Riot Gyro (`riot_gyro`)

- Description: Every 3 Attack cards you play in a single turn, gain 1 Strength.
- Visual Flavor: A stabilizer gyro built from riot hardware, spinning heavier each time attack cadence builds.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `attack`, `strength`, `combo`
- Track: `advanced`
- Synergies: `Enforcer attack spam`, `Operator poke chains`, `Zero-Day Burst / Packet Storm / Riot Barrage`
- Notes: This is a direct cadence relic in the Slay the Spire tradition: easy to read, hard to maximize.
- Hooks:
  - `after_card_played`
    - If card type is `attack` Every `3` matching cards this turn Gain 1 Strength.

### Scrap Choir (`scrap_choir`)

- Description: Whenever a status card is exhausted, heal 1 HP.
- Visual Flavor: A choir of tiny scrap bells and speaker tubes singing through junk with a surprisingly warm tone.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `status`, `heal`
- Track: `drop_in`
- Synergies: `Rot Harvest`, `Jam Cycler`, `Bio self-damage packages`
- Notes: Creates compounding sustain when the deck learns to metabolize junk.
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Heal 1 HP.

### Septic Reservoir (`septic_reservoir`)

- Description: At end of your turn, the enemy with the highest Infect gains 1 Infect.
- Visual Flavor: A hanging septic fluid reservoir or vial bank filled with thick infected green fluid. Readable glass-and-liquid silhouette, not a full lab scene.
- Rarity: `uncommon`
- Base Weight: `5`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `infect`, `scaling`
- Track: `legacy/untracked`
- Hooks:
  - `turn_end`
    - If status is `infect` Increase the highest enemy `infect` by 1.

### Symbiont Spindle (`symbiont_spindle`)

- Description: Whenever you heal during combat, deal 2 damage to a random enemy.
- Visual Flavor: A living spindle threaded with flesh cable and bright blood flow, half industrial bobbin and half parasite.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `heal`, `offense`
- Track: `advanced`
- Synergies: `Symbiote Mesh`, `Blood Buffer`, `Triage Loop`, `Quarantine Vault`
- Notes: Turns recovery into pressure and gives Bio Hacker a more predatory identity.
- Hooks:
  - `on_heal`
    - Deal 2 damage to a random enemy.

### Toll Spike (`toll_spike`)

- Description: The first time each combat you gain Marked, Suppressed, or Nullified, deal 4 damage to a random enemy.
- Visual Flavor: A punitive spike or tax nail stamped with control sigils and meant to punish anyone already under pressure.
- Rarity: `uncommon`
- Base Weight: `6`
- Draft Eligible: `True`
- Source Types: `elite_reward`, `shop`
- Tags: `enemy_status`, `offense`
- Track: `drop_in`
- Synergies: `Blackwire-heavy routes`, `Marker Scrambler`, `Null Damper`
- Notes: Turns enemy control tools into a small punish packet.
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `marked`, `suppressed`, `nullified` Deal 4 damage to a random enemy.

## rare

### Arterial Reservoir (`arterial_reservoir`)

- Description: At end of your turn, the enemy with the highest Bleed gains 1 Bleed and takes 3 damage.
- Visual Flavor: A hanging arterial tank of dark red fluid with pressure dials and a bleed overflow pipe.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `bleed`, `scaling`, `offense`
- Track: `drop_in`
- Synergies: `Blood Indexer`, `Butcher Hooks`, `multi-hit decks`
- Notes: This is the “I am all-in on Bleed” relic. High payoff, narrow lane.
- Hooks:
  - `turn_end`
    - If status is `bleed` Increase the highest enemy `bleed` by 1.
    - If status is `bleed` Deal 3 damage to the enemy with the highest matching status.

### Auction Seeder (`auction_seeder`)

- Description: Card rewards show 1 extra choice. Shop relic prices cost 10% less.
- Visual Flavor: A gilded auction seedbox with bid tabs, sale lights, and branching price markers ready to bloom into more options.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `shop`
- Tags: `economy`, `reward`, `shop`
- Track: `drop_in`
- Synergies: `Signal Router`, `Market Ghost`, `long-form drafting`
- Notes: A meta relic aimed at players who want more agency rather than more raw combat stats.
- Hooks:
  - `on_reward`
    - Show 1 extra card reward choice.
  - `on_shop`
    - Reduce `relic` prices by 10%.

### Controlled Bleed Valve (`controlled_bleed_valve`)

- Description: The first time each turn Bleed bonus damage triggers, draw 1 card and reapply 1 Bleed.
- Visual Flavor: A surgical pressure valve with a crimson drip gauge and a return-feed tube for repeated cuts.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `bleed`, `draw`, `scaling`
- Track: `advanced`
- Synergies: `Gouge`, `Double Tap`, `Riot Barrage`, `Blood Indexer`
- Notes: Lets Bleed behave more like an engine resource instead of a purely per-hit decay counter.
- Hooks:
  - `on_bleed_trigger`
    - First each turn Draw 1 card.
    - First each turn If status is `bleed` Apply 1 `bleed` to the event target.

### Execution Array (`execution_array`)

- Description: The first time each turn you hit an enemy that has a combat status, deal 3 bonus damage and draw 1 card.
- Visual Flavor: A compact execution module with a sensor eye and three deployable blades or rails. Rare relic; make it elegant and dangerous.
- Rarity: `rare`
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `status`, `offense`, `draw`
- Track: `legacy/untracked`
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `weak`, `vulnerable`, `bleed`, `burn`, `infect` Deal 3 damage to the triggering enemy.
    - First each turn If target has `weak`, `vulnerable`, `bleed`, `burn`, `infect` Draw 1 card.

### Grave Lantern (`grave_lantern`)

- Description: Start each combat by applying 1 Weak and 1 Bleed to all enemies.
- Visual Flavor: A black lantern venting red bleed haze and pale green weakening fumes. Use one lantern silhouette and subtle dual-color vapor.
- Rarity: `rare`
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `aoe`, `status`, `setup`
- Track: `legacy/untracked`
- Hooks:
  - `combat_start`
    - If status is `weak` Apply 1 `weak` to all enemies.
    - If status is `bleed` Apply 1 `bleed` to all enemies.

### Grave Matrix (`grave_matrix`)

- Description: Start each combat by applying 1 Weak and 1 Vulnerable to all enemies.
- Visual Flavor: A black status lattice or grave-matrix frame humming with paired weakness and exposed-seam glyphs.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `setup`, `aoe`, `control`
- Track: `drop_in`
- Synergies: `Exposure Grid`, `Execution Array`, `Pressure Mesh`
- Notes: A high-impact opener relic that makes the first turn matter more.
- Hooks:
  - `combat_start`
    - If status is `weak` Apply 1 `weak` to all enemies.
    - If status is `vulnerable` Apply 1 `vulnerable` to all enemies.

### Mortuary Router (`mortuary_router`)

- Description: Whenever a status card is exhausted, deal 4 damage to a random enemy and draw 1 card.
- Visual Flavor: An embalmer router box with a red kill-light, card slots, and precise channels for weaponized cleanup.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `status`, `offense`, `draw`
- Track: `drop_in`
- Synergies: `Rot Harvest`, `Jam Battery`, `Scrap Choir`
- Notes: One of the spikiest status-payoff relics; watch for runaway loops with free status exhaust.
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Deal 4 damage to a random enemy.
    - If card type is `status` Draw 1 card.

### Mummified Wire (`mummified_wire`)

- Description: Whenever you play a Power, a random card in your hand costs 0 until it is played.
- Visual Flavor: A wrapped cable bundle with dried insulator strips, preserved nodes, and occult-looking power discipline.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `power`, `cost_reduction`, `combo`
- Track: `advanced`
- Synergies: `Auto-Tuner`, `Control Tower`, `Deep Cache`, `War Engine`, `Rot Harvest`
- Notes: Very strong, but your current card pool has a healthy, not absurd, Power density.
- Hooks:
  - `after_card_played`
    - If card type is `power` Set a random card in hand to cost 0 until played.

### Protocol Drift (`protocol_drift`)

- Description: Whenever you gain Suppressed or Nullified, add 1 Glitch to your discard. The first Glitch you draw each combat grants 1 Energy and Exhausts without penalty.
- Visual Flavor: A corrupted protocol cassette wrapped in glitch haze and crossed-out control glyphs.
- Rarity: `rare`
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `suppressed`, `nullified`, `status`, `corruption`
- Track: `advanced`
- Synergies: `corruption/theme work`, `Blackwire fights`, `Rot Harvest`
- Notes: This is a lore-forward relic that turns system interference into unstable fuel.
- Hooks:
  - `on_player_status_applied`
    - If status is `suppressed`, `nullified` Add 1 `status_glitch_01` status card.
  - `on_status_drawn`
    - First each combat If card is `status_glitch_01` Gain 1 Energy.
    - First each combat If card is `status_glitch_01` Exhaust the drawn status card.

### Quarantine Vault (`quarantine_vault`)

- Description: The first time each combat you would gain Burn, Bleed, Infect, Suppressed, or Nullified, prevent 1 stack, heal 2 HP, and draw 1 card.
- Visual Flavor: A locked anti-status vault canister with a green negative-pressure window and isolation clamps.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `cleanse`, `enemy_status`, `defense`, `draw`
- Track: `drop_in`
- Synergies: `Null Damper`, `Field Dampener`, `status-heavy routes`
- Notes: Premium anti-route tech; strong, but only once each combat.
- Hooks:
  - `on_player_status_applied`
    - First each combat If status is `burn`, `bleed`, `infect`, `suppressed`, `nullified` Reduce player `None` by 1.
    - First each combat If status is `burn`, `bleed`, `infect`, `suppressed`, `nullified` Heal 2 HP.
    - First each combat If status is `burn`, `bleed`, `infect`, `suppressed`, `nullified` Draw 1 card.

### Reaper Census (`reaper_census`)

- Description: The first enemy that dies each combat grants 1 Energy next turn and applies 1 Weak to all enemies.
- Visual Flavor: A census tablet etched with skull tallies, official seals, and one cold column reserved for the next dead enemy.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `kill`, `energy`, `control`
- Track: `drop_in`
- Synergies: `summon-heavy fights`, `grave_toll`, `grave_sprinkler`
- Notes: Lets aggressive decks turn the first kill into a full tempo swing.
- Hooks:
  - `on_enemy_death`
    - First each combat Gain 1 Energy next turn.
    - First each combat If status is `weak` Apply 1 `weak` to all enemies.

### Recycler Crown (`recycler_crown`)

- Description: Whenever a status card is exhausted, add a random temporary 0-cost common card to your hand.
- Visual Flavor: A jagged crown made of shredder teeth, ticket scraps, and improvised feed rollers.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `status`, `generation`, `combo`
- Track: `advanced`
- Synergies: `Rot Harvest`, `Mortuary Router`, `Jam Battery`, `Queue Mirror`
- Notes: This is a high-ceiling status-conversion relic; likely rare or boss-tier if it overperforms.
- Hooks:
  - `on_card_exhausted`
    - If card type is `status` Add a random temporary card to your hand.

### Septic Crown (`septic_crown`)

- Description: At end of your turn, the enemy with the highest Infect gains 1 Infect and you heal 1 HP.
- Visual Flavor: A regal corroded crown with hanging infected vials and slow verdant seepage.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `infect`, `scaling`, `heal`
- Track: `drop_in`
- Synergies: `Septic Reservoir`, `Bio Hacker infect package`
- Notes: Rare version of the Infect slow-burn package.
- Hooks:
  - `turn_end`
    - If status is `infect` Increase the highest enemy `infect` by 1.
    - If status is `infect` Heal 1 HP if any enemy has a matching status.

### Signal Router (`signal_router`)

- Description: Card rewards show 1 extra choice.
- Visual Flavor: A small router box with dual antennas and a bright signal display. Maintain the readable box-and-antennas silhouette.
- Rarity: `rare`
- Base Weight: `3`
- Draft Eligible: `True`
- Source Types: `run_start`
- Tags: `draw`, `blessing`
- Track: `legacy/untracked`
- Hooks:
  - `on_reward`
    - Show 1 extra card reward choice.

### Toll Evasion Kit (`toll_evasion_kit`)

- Description: The first time each combat Nullified blocks one of your positive gains, draw 2 cards and gain 1 Energy next turn.
- Visual Flavor: A smuggler's bypass kit packed with toll tokens, null tools, and one very illegal override pick.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `nullified`, `draw`, `energy`
- Track: `advanced`
- Synergies: `Operator discount shells`, `Null Damper`, `Quarantine Vault`
- Notes: Makes Nullified feel interactive instead of purely punitive.
- Hooks:
  - `on_positive_gain_blocked_by_nullified`
    - First each combat Draw 2 cards.
    - First each combat Gain 1 Energy next turn.

### Verdict Engine (`verdict_engine`)

- Description: The first time each turn you hit an enemy with 2 or more combat statuses, deal 6 bonus damage.
- Visual Flavor: A compact verdict engine stamping final judgment through a bright legal seal and a brutal execution line.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `status`, `offense`
- Track: `drop_in`
- Synergies: `multi-status decks`, `Grave Matrix`, `Execution Array`
- Notes: Rewards players for building layered debuff turns instead of single-axis status stacks.
- Hooks:
  - `on_attack_hit`
    - First each turn If target has `weak`, `vulnerable`, `bleed`, `infect`, `burn` At least `2` matching statuses Deal 6 damage to the triggering enemy.

### Viral Relay (`viral_relay`)

- Description: Whenever Infect bursts at 6 or more and resets to 3, apply 1 Infect to all other enemies.
- Visual Flavor: A spore-dispensing relay node with branching infection lines and a contagion pulse ready to jump targets.
- Rarity: `rare`
- Base Weight: `4`
- Draft Eligible: `True`
- Source Types: `boss_reward`, `elite_reward`
- Tags: `infect`, `aoe`, `scaling`
- Track: `advanced`
- Synergies: `Parasite Fang`, `Septic Crown`, `Septic Reservoir`
- Notes: This is the “plague outbreak” relic for infect-focused runs.
- Hooks:
  - `on_infect_burst`
    - If status is `infect` Apply 1 `infect` to all other enemies.

## boss

### Authority Bypass (`authority_bypass`)

- Description: The first Attack, first Skill, and first Power you play each turn each refund 1 Energy.
- Visual Flavor: A tri-channel bypass module with three keyed faces and an illicit jumper wire bridging all of them at once.
- Rarity: `boss`
- Base Weight: `2`
- Draft Eligible: `True`
- Source Types: `boss_reward`
- Tags: `attack`, `skill`, `power`, `energy`
- Track: `advanced`
- Synergies: `Triune Module`, `Operator mixed sequencing`, `cheap combo turns`
- Notes: Potentially explosive; this is intentionally boss-only and should be watched for infinite turns.
- Hooks:
  - `after_card_played`
    - First each turn If card type is `attack` Gain 1 Energy.
    - First each turn If card type is `skill` Gain 1 Energy.
    - First each turn If card type is `power` Gain 1 Energy.

### Flesh Dividend (`flesh_dividend`)

- Description: The first time each turn you lose HP on your turn, the next time you heal that turn, gain 1 Strength and 1 Energy.
- Visual Flavor: A biotech dividend engine of pumps, blood meters, and profit needles turning self-harm into a payout.
- Rarity: `boss`
- Base Weight: `2`
- Draft Eligible: `True`
- Source Types: `boss_reward`
- Tags: `self_damage`, `heal`, `strength`, `energy`
- Track: `advanced`
- Synergies: `Symbiote Mesh`, `Blood Buffer`, `Triage Loop`, `Spare Organs`, `Reclaimer`
- Notes: A boss-tier self-harm/recovery engine piece. Watch carefully with Bio Hacker sustain loops.
- Hooks:
  - `on_self_damage`
    - First each turn Set modifier flag `armed`.
  - `on_heal`
    - If modifier flag `armed` is set Gain 1 Strength.
    - If modifier flag `armed` is set Gain 1 Energy.
    - If modifier flag `armed` is set Clear modifier flag `armed`.

### Spine Script (`spine_script`)

- Description: At the start of turn 3 and every 3 turns after, draw 1 card and gain 1 Energy.
- Visual Flavor: A civic control script ribbon or foldout chip etched with ancient Spine Core directives and timed power pulses.
- Rarity: `boss`
- Base Weight: `2`
- Draft Eligible: `True`
- Source Types: `boss_reward`
- Tags: `turn_counter`, `draw`, `energy`
- Track: `advanced`
- Synergies: `stall decks`, `boss fights`, `Overclock Relay`
- Notes: A clean cadence relic: easy to understand, exciting to plan around.
- Hooks:
  - `on_turn_start`
    - Every `3` turns starting after offset `0` Draw 1 card.
    - Every `3` turns starting after offset `0` Gain 1 Energy.

### Triune Module (`triune_module`)

- Description: If you play an Attack, Skill, and Power in the same turn, gain 1 Energy next turn and draw 1 card.
- Visual Flavor: A three-lobed module with attack, skill, and power faces feeding a shared luminous core.
- Rarity: `boss`
- Base Weight: `2`
- Draft Eligible: `True`
- Source Types: `boss_reward`
- Tags: `attack`, `skill`, `power`, `energy`, `draw`
- Track: `advanced`
- Synergies: `Operator power shells`, `mixed-value turns`, `Mummified Wire`
- Notes: A run-defining boss relic that asks for real sequencing decisions.
- Hooks:
  - `after_card_played`
    - First each turn If played types include `attack`, `skill`, `power` Gain 1 Energy next turn.
    - First each turn If played types include `attack`, `skill`, `power` Draw 1 card.
