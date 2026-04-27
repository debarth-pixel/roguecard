# Events Master Reference

Generated from `data/events.json`.

- Total events: **91**

## common

### Ash Seller (`ash_seller_01`)

- Body: A vendor sells cooling ash from a barrel that is still burning inside.
- Visual Flavor: A masked ash vendor beside a smoking barrel, with black powder scooped into bright heatproof envelopes.
- Base Weight: `6`
- Tags: `burn`, `relic`, `tradeoff`
- Choices:
  - `Buy cooled ash` (`effect`): Spend 14 credits. Gain Ash Veil.
    - Requirements: `{"credits_at_least": 14}`
  - `Scoop free ash` (`effect`): Gain 10 credits. Next combat: start with 1 Burn.
  - `Let the dampener taste it` (`effect`): Next combat: start with 5 Block.
    - Requirements: `{"modifier_active": "field_dampener"}`

### Broken Firewall Kiosk (`broken_firewall_kiosk_01`)

- Body: An old security kiosk still prints defensive routines if you hit it correctly.
- Visual Flavor: A cracked public-security kiosk coughing blue firewall tickets from a jammed printer mouth.
- Base Weight: `9`
- Tags: `deck_edit`, `defense`, `merchant_style`
- Choices:
  - `Print a Firewall` (`effect`): Spend 7 credits. Add Firewall to your deck.
    - Requirements: `{"credits_at_least": 7}`
  - `Hotwire the printer` (`effect`): Take 4 damage. Increase Protocol Drift by 2%. Next combat: add a temporary Firewall to your hand.
  - `Kick it quiet` (`effect`): Gain 6 credits.

### Butcher Ledger (`butcher_ledger_01`)

- Body: A meat-shop terminal lists names, wounds, and unpaid cuts in the same column.
- Visual Flavor: A hanging butcher terminal beside steel hooks, with red ledger lines crawling across a greasy glass display.
- Base Weight: `6`
- Tags: `bleed`, `economy`, `synergy`
- Character IDs: `enforcer`
- Choices:
  - `Trace unpaid cuts` (`effect`): Gain 16 credits.
    - Requirements: `{"modifier_active": "butcher_hooks"}`
  - `Forge your name` (`effect`): Gain 22 credits. Next combat: start with 1 Bleed.
  - `Close the ledger` (`effect`): Move on.

### Cheap Implant Rack (`cheap_implant_rack_01`)

- Body: A rack of discount implants blinks with exactly enough power to be a mistake.
- Visual Flavor: A folding vendor rack of cheap implant chips, each sealed in cracked plastic with handwritten warning labels.
- Base Weight: `5`
- Tags: `relic`, `tradeoff`, `corruption`
- Character IDs: `operator`
- Choices:
  - `Install the queue clone` (`effect`): Gain Queue Mirror. Lose 5 HP. Increase Protocol Drift by 3%.
  - `Install the riot patch` (`effect`): Gain Riot Plating. Lose 7 HP.
  - `Keep your ports closed` (`effect`): Move on.

### Civic Checkpoint (`civic_checkpoint_01`)

- Body: A checkpoint scans your license, your face, and the parts of you that are still negotiable.
- Visual Flavor: A checkpoint gate with red civic lasers, enforcer silhouettes, and a scanner arch dripping rain.
- Base Weight: `8`
- Tags: `economy`, `marked`, `status_risk`
- Character IDs: `enforcer`
- Choices:
  - `Show papers` (`effect`): Spend 6 credits.
    - Requirements: `{"credits_at_least": 6}`
  - `Run the scan hot` (`effect`): Next combat: draw 1 extra card on turn 1. Next combat: start with 1 Marked.
  - `Fake the papers` (`effect`): Gain 8 credits. Increase Protocol Drift by 2%.
    - Requirements: `{"protocol_drift_below": 80}`
  - `Bypass authority` (`effect`): Gain 12 credits.
    - Requirements: `{"modifier_active": "authority_bypass"}`

### Credit Shakedown (`credit_shakedown_01`)

- Body: Two enforcers block the alley and ask for a tax.
- Visual Flavor: A narrow alley choke point with two enforcers, neon rain, and a demanded payment hanging in the air.
- Base Weight: `8`
- Tags: `economy`, `gamble`, `tradeoff`
- Choices:
  - `Pay the tax` (`effect`): Lose 12 credits.
    - Requirements: `{"credits_at_least": 12}`
  - `Refuse` (`effect`): Lose 6 HP.
  - `Hack their ledger` (`effect`): Gain 18 credits. Take 4 damage. Increase Protocol Drift by 3%.

### Dampener Repairman (`dampener_repairman_01`)

- Body: A repairman with magnetized fingers offers to patch the parts that absorb pain.
- Visual Flavor: A hunched repairman in a raincoat tuning a dampener puck with tiny magnetic tools.
- Base Weight: `6`
- Tags: `defense`, `relic`, `enemy_status`, `merchant_style`
- Choices:
  - `Buy a dampener puck` (`effect`): Spend 15 credits. Gain Field Dampener.
    - Requirements: `{"credits_at_least": 15}`
  - `Let him patch your rig` (`effect`): Next combat: start with 5 Block. Increase Protocol Drift by 2%.
  - `Ask for route advice` (`effect`): Reduce Protocol Drift by 2%.
    - Requirements: `{"modifier_active": "null_damper"}`

### Dead Drop (`dead_drop_01`)

- Body: A courier cache blinks beneath a tram bench.
- Visual Flavor: A tram-bench dead drop with a blinking courier cache tucked into urban grime and electric shadow.
- Base Weight: `10`
- Tags: `economy`, `narrative`
- Choices:
  - `Crack the cache` (`effect`): Gain 25 credits.
  - `Walk away` (`effect`): Move on.

### Grave Bell (`grave_bell_01`)

- Body: A small iron bell rings before anyone touches it.
- Visual Flavor: A lonely grave bell hanging from a street sign, its rope made from cable and old name tags.
- Base Weight: `6`
- Tags: `kill`, `heal`, `relic`, `chain`
- Character IDs: `enforcer`
- Choices:
  - `Ring once` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Ring until it answers` (`effect`): Take 5 damage. Increase Protocol Drift by 3%. Gain Grave Toll.
  - `Stuff the bell` (`effect`): Move on.

### Junkyard Tollbooth (`junkyard_tollbooth_01`)

- Body: A salvage kid blocks the junkyard gate with a scanner made from three broken laws.
- Visual Flavor: A child-sized tollbooth welded from scrap plates, scanner arms, and dangling relic tags, backed by heaps of dead machines.
- Base Weight: `7`
- Tags: `economy`, `relic`, `tradeoff`
- Character IDs: `enforcer`
- Choices:
  - `Pay the salvage toll` (`effect`): Spend 12 credits. Gain a random common defense relic.
    - Requirements: `{"credits_at_least": 12}`
  - `Crash the gate` (`effect`): Gain 20 credits. Take 6 damage.
  - `Take the untagged relic` (`effect`): Take 5 damage. Increase Protocol Drift by 3%. Gain a random common relic.

### Low-Signal Shelter (`low_signal_shelter_01`)

- Body: A shelter blocks hostile signals, but its beds are wired to something hungry.
- Visual Flavor: A low concrete shelter with foil curtains, blue sleeping pads, and unplugged signal towers outside.
- Base Weight: `8`
- Tags: `recovery`, `corruption`, `tradeoff`
- Character IDs: `bio_hacker`
- Choices:
  - `Sleep offline` (`effect`): Heal 10.
  - `Sleep plugged in` (`effect`): Heal 15. Increase Protocol Drift by 3%.
  - `Stand guard` (`effect`): Gain 12 credits. Next combat: start with 4 Block.

### Market Price Oracle (`market_price_oracle_01`)

- Body: A coin-operated oracle predicts tomorrow's prices and today's bad decisions.
- Visual Flavor: A tiny fortune kiosk with price tags orbiting a green CRT face and coins jammed into its prediction slot.
- Base Weight: `7`
- Tags: `economy`, `shop`, `merchant_style`
- Character IDs: `operator`
- Choices:
  - `Buy the forecast` (`effect`): Spend 8 credits. Next combat: draw 1 extra card on turn 1.
    - Requirements: `{"credits_at_least": 8}`
  - `Break the oracle` (`effect`): Gain 14 credits.
  - `Ask for a ghost price` (`effect`): Gain 6 credits.
    - Requirements: `{"modifier_active": "market_ghost"}`

### Memory Scrubber (`memory_scrubber_01`)

- Body: A gray-market tech offers to scrub one routine from your stack.
- Visual Flavor: A gray-market scrub station of old recliner, surgical light, and data-erasing tools laid out like contraband dentistry.
- Base Weight: `8`
- Tags: `deck_edit`, `merchant_style`, `cleanse`, `corruption`
- Choices:
  - `Scrub a card` (`purge`): Remove 1 deck card.
    - Requirements: `{"deck_size_at_least": 2}`
  - `Deep scrub` (`purge`): Remove 1 deck card. Take 5 damage. Reduce Protocol Drift by 4%.
    - Requirements: `{"deck_size_at_least": 2}`
  - `Keep the stack intact` (`effect`): Leave it.

### Null Ticket Booth (`null_ticket_booth_01`)

- Body: The rail booth sells transit tickets, signal masks, and one obvious lie.
- Visual Flavor: A flickering metro booth with blank destination signs, null glyph tickets, and a turnstile sparking under the counter.
- Base Weight: `6`
- Tags: `control`, `cleanse`, `status_risk`, `chain`
- Character IDs: `operator`
- Choices:
  - `Buy a legal ticket` (`effect`): Spend 10 credits. Next combat: draw 1 extra card on turn 1.
    - Requirements: `{"credits_at_least": 10}`
  - `Ride the wrong line` (`effect`): Gain 15 credits. Next combat: start with 1 Nullified.
  - `Override the turnstile` (`effect`): Next combat: start with 6 Block. Increase Protocol Drift by 3%.

### Overpass Sleepers (`overpass_sleepers_01`)

- Body: A sleeping camp under the overpass guards a working med-blanket with knives and kindness.
- Visual Flavor: A huddled camp beneath concrete, med-blanket glow lighting tired faces and hidden blades.
- Base Weight: `8`
- Tags: `recovery`, `economy`, `morality`
- Choices:
  - `Share credits` (`effect`): Spend 10 credits. Heal 8 HP.
    - Requirements: `{"credits_at_least": 10}`
  - `Take watch duty` (`effect`): Next combat: start with 5 Block.
  - `Steal from the sleeping rig` (`effect`): Gain 18 credits. Next combat: start with 1 Marked.

### Plaza Antenna (`plaza_antenna_01`)

- Body: A bent plaza antenna catches battle forecasts in bursts of static.
- Visual Flavor: A crooked public antenna in a broken square, with neon signal rings bouncing between cracked tiles.
- Base Weight: `8`
- Tags: `combat_prep`, `draw`, `defense`, `chain`
- Choices:
  - `Tune the defense band` (`effect`): Next combat: start with 5 Block.
  - `Tune the draw band` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Leave it buzzing` (`effect`): Gain 8 credits.

### Quarantine Mask Vendor (`quarantine_mask_vendor_01`)

- Body: A mask vendor offers fresh filters, used filters, and a smile behind neither.
- Visual Flavor: A vendor wall of quarantine masks, cracked visors, green filter tubes, and handwritten contagion prices.
- Base Weight: `7`
- Tags: `infect`, `cleanse`, `relic`, `merchant_style`
- Character IDs: `bio_hacker`
- Choices:
  - `Buy a fresh filter` (`effect`): Spend 12 credits. Next combat: start with 6 Block.
    - Requirements: `{"credits_at_least": 12}`
  - `Wear the used mask` (`effect`): Take 4 damage. Gain Parasite Seal.
  - `Trade a sample` (`effect`): Gain 15 credits. Next combat: start with 1 Infect.

### Rainwater Condenser (`rainwater_condenser_01`)

- Body: A rooftop condenser drips clean water through a nest of illegal cooling fins.
- Visual Flavor: A jury-rigged rooftop water tank with copper fins, rain strings, and a clean blue drip glowing against dirty city haze.
- Base Weight: `8`
- Tags: `recovery`, `status_risk`
- Character IDs: `bio_hacker`
- Choices:
  - `Drink the filtered water` (`effect`): Heal 7 HP.
  - `Bottle the coolant` (`effect`): Next combat: start with 6 Block.
  - `Drink from the lower valve` (`effect`): Heal 13 HP. Next combat: start with 1 Infect.

### Scavenger Lunch (`scavenger_lunch_01`)

- Body: A scavenger offers three packets from a cooler that should not still be cold.
- Visual Flavor: A dented cooler under a tarp, with foil meal packets, cracked ice, and a scavenger watching your hands.
- Base Weight: `8`
- Tags: `recovery`, `status_risk`
- Choices:
  - `Eat slowly` (`effect`): Heal 6 HP.
  - `Pocket the protein` (`effect`): Gain 10 credits. Heal 2 HP.
  - `Eat the silver packet` (`effect`): Heal 12 HP. Next combat: start with 1 Infect.

### Scrap Lottery Box (`scrap_lottery_box_01`)

- Body: A dented prize box promises a relic, a burn, or proof that it was never honest.
- Visual Flavor: A rusted sidewalk prize box with claw-machine glass, scrap tokens, and a prize chute glowing wrong.
- Base Weight: `7`
- Tags: `gamble`, `relic`, `status_risk`
- Choices:
  - `Pull the scrap lever` (`risk`): Roll a small prize or injury.
    - Outcomes:
      - `loose_credits` (weight 45): Gain 18 credits.
      - `biting_slot` (weight 25): Take 5 damage.
      - `jammed_card` (weight 20): Gain `cache_draw_01`.
      - `buried_relic` (weight 10): adjust_protocol_drift None Roll a random modifier from `relic` with rarities `common` including `defense`, `offense`, `economy`, `draw`, `status`. Fallback: Gain 12 credits.
  - `Kick the refund tray` (`effect`): Gain 4 credits.

### Shredder Blessing (`shredder_blessing_01`)

- Body: A civic paper shredder has been converted into a machine that eats bad habits.
- Visual Flavor: A municipal shredder altar with card strips, prayer tape, and a green ready light shaped like a smile.
- Base Weight: `7`
- Tags: `deck_edit`, `recovery`, `tradeoff`
- Choices:
  - `Feed a routine` (`purge`): Spend 8 credits. Remove 1 deck card.
    - Requirements: `{"credits_at_least": 8, "deck_size_at_least": 2}`
  - `Feed a status` (`effect`): Heal 3 HP. Remove 1 Junk from your deck if present.
  - `Climb inside` (`purge`): Take 6 damage. Increase Protocol Drift by 2%. Remove 1 deck card.
    - Requirements: `{"deck_size_at_least": 2}`

### Signal Busker (`signal_busker_01`)

- Body: A speaker-masked busker plays a tune only your implants can hear.
- Visual Flavor: A lone busker under a rain-warped awning, face hidden behind a speaker mask, with signal notes bending neon puddles around them.
- Base Weight: `8`
- Tags: `blessing`, `economy`, `narrative`, `chain`
- Choices:
  - `Tip the busker` (`effect`): Spend 8 credits. Heal 5.
    - Requirements: `{"credits_at_least": 8}`
  - `Steal the amp fuse` (`effect`): Gain 14 credits. Next combat: gain 1 Suppressed and a temporary Mirror Cache.
  - `Sync to the chorus` (`effect`): Heal 4. Reduce Protocol Drift by 3%.
    - Requirements: `{"modifier_active": "street_choir"}`

### Smuggled Waterline (`smuggled_waterline_01`)

- Body: A busted utility pipe carries clean water through a route nobody official can find.
- Visual Flavor: A broken waterline behind a service wall, with clean water glowing through illegal valves and route chalk.
- Base Weight: `8`
- Tags: `recovery`, `economy`, `chain`
- Choices:
  - `Drink at the valve` (`effect`): Heal 8 HP.
  - `Patch the leak` (`effect`): Gain 10 credits.
  - `Sell the route` (`effect`): Gain 22 credits. Gain Debt Mark.

### Spare Battery Shrine (`spare_battery_shrine_01`)

- Body: A shrine of taped batteries hums with enough charge to make one fight sloppy and bright.
- Visual Flavor: A sidewalk altar stacked with disposable cells, prayer tags, warning stickers, and a single pulsing battery core.
- Base Weight: `7`
- Tags: `combat_prep`, `energy`, `status_risk`
- Choices:
  - `Slot the clean cell` (`effect`): Spend 10 credits. Next combat: gain 1 Energy on turn 1.
    - Requirements: `{"credits_at_least": 10}`
  - `Slot the leaking cell` (`effect`): Next two combats: gain 1 Energy on turn 1. Increase Protocol Drift by 4%.
  - `Leave the shrine intact` (`effect`): Move on.

### Split-Wire Courier (`split_wire_courier_01`)

- Body: A courier with two mirrored packages asks which version of the truth you can carry.
- Visual Flavor: A breathless courier holding twin wire-wrapped parcels, each blinking with a different route color.
- Base Weight: `7`
- Tags: `economy`, `deck_edit`, `chain`, `narrative`
- Choices:
  - `Deliver the blue parcel` (`effect`): Gain 15 credits.
  - `Open the red parcel` (`effect`): Increase Protocol Drift by 2%. Add Cache Draw to your deck.
  - `Drop both parcels` (`effect`): Move on.

### Street Charger (`street_charger_01`)

- Body: A vending charger offers safe juice and illegal juice.
- Visual Flavor: A sidewalk charging stand with three glowing cables, one clean, one sparking, and one sealed behind warning tape.
- Base Weight: `8`
- Tags: `combat_prep`, `energy`, `draw`, `status_risk`
- Choices:
  - `Charge clean` (`effect`): Spend 8 credits. Next combat: draw 1 extra card on turn 1.
    - Requirements: `{"credits_at_least": 8}`
  - `Overcharge` (`effect`): Take 3 damage. Next combat: gain 1 Energy on turn 1. Increase Protocol Drift by 2%.
  - `Leave the charger` (`effect`): Move on.

### Street Clinic (`street_clinic_01`)

- Body: A ripperdoc offers rough repairs under a neon sheet.
- Visual Flavor: A rough street clinic under a neon tarp with patched instruments, stained steel, and improvised mercy.
- Base Weight: `9`
- Tags: `recovery`, `merchant_style`, `cleanse`, `corruption`
- Choices:
  - `Pay for treatment` (`effect`): Spend 15 credits. Heal 15.
    - Requirements: `{"credits_at_least": 15, "missing_hp_at_least": 5}`
  - `Stabilize the protocol` (`effect`): Spend 20 credits. Reduce Protocol Drift by 8%.
    - Requirements: `{"credits_at_least": 20, "protocol_drift_at_least": 8}`
  - `Purge the corruption` (`effect`): Remove System Corruption. Heal 4.
    - Requirements: `{"modifier_active": "system_corruption"}`
  - `Decline` (`effect`): Move on.

### Trashfire Oracle (`trashfire_oracle_01`)

- Body: A burning barrel speaks in shop receipts, autopsy tags, and next-turn probabilities.
- Visual Flavor: A trashfire in an oil drum, flames forming receipt text and tiny skull-shaped sparks.
- Base Weight: `5`
- Tags: `narrative`, `gamble`, `chain`, `economy`
- Choices:
  - `Listen to the smoke` (`effect`): Gain 12 credits.
  - `Feed it credits` (`effect`): Spend 10 credits. Next combat: gain 1 Energy on turn 1.
    - Requirements: `{"credits_at_least": 10}`
  - `Feed it blood` (`effect`): Gain 25 credits. Take 6 damage. Increase Protocol Drift by 2%.

### Zero-Cost Graffito (`zero_cost_graffito_01`)

- Body: A wall tag rewrites itself whenever you think about doing something cheap.
- Visual Flavor: A neon graffito of a zero-cost glyph reflecting through wet brick and cheap camera eyes.
- Base Weight: `6`
- Tags: `zero_cost`, `draw`, `combo`, `chain`
- Character IDs: `operator`
- Choices:
  - `Study the tag` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Scrape conductive paint` (`effect`): Gain 12 credits.
  - `Trace the hidden queue` (`effect`): Next combat: add a temporary Overclock to your hand.
    - Requirements: `{"modifier_active": "queue_mirror"}`

## uncommon

### Auction Warm-Up (`auction_warmup_01`)

- Body: A back-room auction lets you pay now to see better futures later.
- Visual Flavor: A velvet back room with holographic bid paddles, card reward silhouettes, and a locked auction seedbox on display.
- Base Weight: `5`
- Tags: `reward`, `shop`, `economy`, `combo`
- Min Floor: `2`
- Choices:
  - `Buy a preview seat` (`effect`): Spend 18 credits. Add Cache Draw to your deck.
    - Requirements: `{"credits_at_least": 18}`
  - `Bribe the seed clerk` (`effect`): Spend 30 credits. Gain Signal Router.
    - Requirements: `{"credits_at_least": 30}`
  - `Exploit your discount shell` (`effect`): Gain 12 credits.
    - Requirements: `{"modifier_active": "market_key"}`

### Back-Alley Casino (`backalley_casino_01`)

- Body: A hidden pit boss offers fast winnings with strings attached.
- Visual Flavor: A cramped neon gambling den with folding tables, hidden cameras, and a pit boss smiling behind cheap velvet and dirty light.
- Base Weight: `5`
- Tags: `economy`, `gamble`, `status_risk`, `tradeoff`
- Choices:
  - `Take the odds` (`effect`): Gain High Roller.
  - `Take the advance` (`effect`): Gain 35 credits. Gain Debt Mark. Increase Protocol Drift by 2%.
  - `Cash out` (`effect`): Walk away.

### Black Ice Cache (`black_ice_cache_01`)

- Body: A locked shard still holds something worth stealing.
- Visual Flavor: A locked shard vault glowing cold blue in a dark alley, with frostlike data spikes crawling over its casing.
- Base Weight: `6`
- Tags: `deck_edit`, `gamble`
- Choices:
  - `Force the cache` (`effect`): Lose 6 HP. Gain Firewall.
  - `Leave it sealed` (`effect`): Leave it.

### Blackwire Broker (`blackwire_broker_01`)

- Body: A broker in a static-lined coat sells answers to control effects that have not happened yet.
- Visual Flavor: A blackwire broker beneath a flickering awning, opening a coat full of null coils and marked signal tags.
- Base Weight: `5`
- Tags: `control`, `relic`, `status_risk`, `corruption`
- Min Floor: `2`
- Character IDs: `operator`
- Choices:
  - `Buy the damper` (`effect`): Spend 24 credits. Gain Null Damper. Next combat: add a temporary Null Refund to hand.
    - Requirements: `{"credits_at_least": 24}`
  - `Buy the punitive spike` (`effect`): Gain Toll Spike. Next combat: start Suppressed. Increase Protocol Drift by 5%.
  - `Take only the names` (`effect`): Gain 18 credits.

### Bone Receipt Window (`bone_receipt_window_01`)

- Body: A clerk files pain receipts and pays out in block, credits, or silence.
- Visual Flavor: A narrow claims window stacked with bone-white receipts, red stamps, and a clerk wearing surgical gloves.
- Base Weight: `4`
- Tags: `self_damage`, `defense`, `relic`, `tradeoff`
- Min Floor: `2`
- Choices:
  - `File a pain claim` (`effect`): Gain Bone Receipt. Lose 8 HP. Increase Protocol Drift by 4%. Next combat: add a temporary Error Knife to hand.
  - `Cash out old injuries` (`effect`): Gain 20 credits. Heal 4.
    - Requirements: `{"current_hp_below_percent": 60}`
  - `Refuse the paperwork` (`effect`): Move on.

### Cache Bloom (`cache_bloom_01`)

- Body: A cache seed splits through concrete, offering draw now or draft power later.
- Visual Flavor: A glowing green cache crystal growing from cracked pavement, with data petals opening like a flower.
- Base Weight: `5`
- Tags: `draw`, `reward`, `relic`, `deck_edit`
- Min Floor: `2`
- Character IDs: `operator`
- Choices:
  - `Harvest the seed` (`effect`): Add Cache Draw to your deck. Gain Shard Seed.
  - `Let it bloom` (`effect`): Spend 22 credits. Gain Flash Cache.
    - Requirements: `{"credits_at_least": 22}`
  - `Cut the flower early` (`effect`): Gain 20 credits. Add Cache Draw to your deck.

### Cinder Contract (`cinder_contract_01`)

- Body: A heat debt collector offers retaliation in exchange for wearing the burn first.
- Visual Flavor: A contract tablet glowing ember-orange, with cinder coils wrapped around the signature line.
- Base Weight: `4`
- Tags: `burn`, `retaliation`, `relic`, `tradeoff`
- Min Floor: `2`
- Choices:
  - `Sign the cinder clause` (`effect`): Gain Cinder Feedback. Next combat: start with 1 Burn.
  - `Buy out the heat` (`effect`): Spend 18 credits. Gain Ash Veil.
    - Requirements: `{"credits_at_least": 18}`
  - `Let the vault contain it` (`effect`): Gain 12 credits. Heal 5 HP.
    - Requirements: `{"modifier_active": "quarantine_vault"}`

### Crash Chassis (`crash_chassis_01`)

- Body: A stripped combat frame still has lessons worth stealing.
- Visual Flavor: A stripped combat frame sprawled in a wreck bay, half-disassembled and still dangerous with live warning lights.
- Base Weight: `5`
- Tags: `combat_prep`, `economy`, `relic`, `tradeoff`
- Choices:
  - `Study the rhythm` (`effect`): Gain Momentum.
  - `Wear the broken plate` (`effect`): Gain Fractured Armor.
  - `Strip the parts` (`effect`): Gain 15 credits.
  - `Install the cracked gyro` (`effect`): Gain Riot Gyro. Take 8 damage. Increase Protocol Drift by 4%.
    - Requirements: `{"current_hp_at_least": 16}`

### Debt Spike (`debt_spike_01`)

- Body: A courier broker offers premium access with a nasty rider.
- Visual Flavor: A slick broker booth with premium courier branding, hidden fine print, and a needlelike contract device.
- Base Weight: `4`
- Tags: `curse`, `status_risk`, `merchant_style`
- Choices:
  - `Sign the advance` (`effect`): Gain Debt Spike.
  - `Decline` (`effect`): Decline it.

### Debt Witness (`debt_witness_01`)

- Body: A contract witness records debts with a camera that looks like a mouth.
- Visual Flavor: A polished debt booth with a witness camera, gold contract needles, and a receipt printer spitting black paper.
- Base Weight: `5`
- Tags: `curse`, `economy`, `chain`, `tradeoff`
- Min Floor: `2`
- Choices:
  - `Take witnessed credit` (`effect`): Gain 45 credits. Gain Debt Spike.
  - `Clear your name` (`effect`): Spend 30 credits. Remove Debt Mark if active.
    - Requirements: `{"credits_at_least": 30, "modifier_active": "debt_mark"}`
  - `Refuse the witness` (`effect`): Move on.

### Execution Rig (`execution_rig_01`)

- Body: A kill-switch rig wants proof that your enemies are already compromised.
- Visual Flavor: A compact execution rig with sensor eyes, blade rails, and status icons projected over a test dummy.
- Base Weight: `4`
- Tags: `status`, `offense`, `draw`, `relic`, `tradeoff`
- Min Floor: `3`
- Character IDs: `enforcer`
- Choices:
  - `Install execution relay` (`effect`): Spend 28 credits. Gain Execution Relay.
    - Requirements: `{"credits_at_least": 28}`
  - `Install the full array` (`effect`): Take 10 damage. Increase Protocol Drift by 7%. Gain Execution Array.
  - `Run a verdict test` (`effect`): Next combat: draw 1 extra card on turn 1.

### Field Trial Chamber (`field_trial_chamber_01`)

- Body: A lab chamber tests anti-status hardware by hurting you just enough to prove it works.
- Visual Flavor: A sealed test chamber with hostile status emitters, dampener rings, and a safe relic behind glass.
- Base Weight: `4`
- Tags: `enemy_status`, `cleanse`, `defense`, `relic`, `tradeoff`
- Min Floor: `3`
- Character IDs: `enforcer`
- Choices:
  - `Run the basic trial` (`effect`): Gain Field Dampener. Next combat: start with 1 Burn.
  - `Run the vault trial` (`effect`): Take 12 damage. Increase Protocol Drift by 6%. Gain Quarantine Vault.
  - `Refuse the chamber` (`effect`): Gain 10 credits.

### Ghost Market Turnstile (`ghost_market_turnstile_01`)

- Body: A turnstile appears where no shop exists, charging a fare in coins or future bargains.
- Visual Flavor: A translucent market entrance with a single turnstile, floating price tags, and ghost hands counting coins.
- Base Weight: `5`
- Tags: `shop`, `economy`, `relic`, `chain`
- Min Floor: `2`
- Character IDs: `operator`
- Choices:
  - `Pay the fare` (`effect`): Spend 25 credits. Gain Market Ghost.
    - Requirements: `{"credits_at_least": 25}`
  - `Take ghost credit` (`effect`): Gain 35 credits. Gain Debt Mark.
  - `Show the warranty chip` (`effect`): Gain 12 credits.
    - Requirements: `{"modifier_active": "ghost_warranty"}`

### Ghost Warranty (`ghost_warranty_01`)

- Body: A market ghost offers a free first reroll in every shop.
- Visual Flavor: A half-real market phantom leaning over a kiosk, offering a glowing warranty chip from behind static.
- Base Weight: `4`
- Tags: `blessing`, `merchant_style`
- Choices:
  - `Install the warranty` (`effect`): Gain Ghost Warranty.
  - `Decline` (`effect`): Decline it.

### Glitch Lottery (`glitch_lottery_01`)

- Body: A hacked terminal offers one corrupt spin.
- Visual Flavor: A hacked public terminal pulsing with corrupt icons, missing text blocks, and tempting jackpot screens.
- Base Weight: `6`
- Tags: `gamble`, `anomaly`, `corruption`
- Choices:
  - `Spin the daemon` (`risk`): Roll credits, damage, or a card.
    - Outcomes:
      - `jackpot_credits` (weight 40): Gain 35 credits.
      - `neural_burn` (weight 25): Take 7 damage.
      - `credit_skimmer` (weight 20): Lose 15 credits.
      - `hidden_payload` (weight 10): Gain `overclock_01`.
      - `protocol_echo` (weight 5): Gain 20 credits. adjust_protocol_drift None
  - `Ignore it` (`effect`): Walk past.

### Grave Census Clerk (`grave_census_clerk_01`)

- Body: A civic clerk counts the dead before the fight starts and asks how official you want it.
- Visual Flavor: A census desk in an empty street, skull tallies stamped onto glowing forms by a bored dead clerk.
- Base Weight: `4`
- Tags: `kill`, `energy`, `control`, `relic`, `chain`
- Min Floor: `2`
- Choices:
  - `Buy the grave pick` (`effect`): Spend 24 credits. Gain Grave Pick.
    - Requirements: `{"credits_at_least": 24}`
  - `Accept the sprinkler form` (`effect`): Take 5 damage. Gain Grave Sprinkler.
  - `Correct the count` (`effect`): Gain 10 credits. Heal 6 HP.
    - Requirements: `{"modifier_active": "grave_toll"}`

### Infection Gallery (`infection_gallery_01`)

- Body: A bio-artist displays living infections under glass, each one trained to obey applause.
- Visual Flavor: A gallery of green-lit specimen frames, living infection patterns blooming like street art behind glass.
- Base Weight: `5`
- Tags: `infect`, `heal`, `relic`, `status_risk`
- Min Floor: `2`
- Character IDs: `bio_hacker`
- Choices:
  - `Buy the siphon` (`effect`): Spend 22 credits. Gain Septic Siphon.
    - Requirements: `{"credits_at_least": 22}`
  - `Open the obedient frame` (`effect`): Take 6 damage. Gain Containment Loop. Next combat: start with 1 Infect.
  - `Let the gallery sketch you` (`effect`): Heal 12 HP. Increase Protocol Drift by 4%.

### Jammer Den (`jammer_den_01`)

- Body: Signal jammers chew status junk into power for anyone willing to breathe the smoke.
- Visual Flavor: A basement den full of spinning jammer drums, shredded status strips, and blue smoke curling from battery mouths.
- Base Weight: `5`
- Tags: `status`, `exhaust`, `relic`, `tradeoff`
- Min Floor: `2`
- Choices:
  - `Buy the battery block` (`effect`): Spend 26 credits. Gain Jam Battery.
    - Requirements: `{"credits_at_least": 26}`
  - `Buy the cycler teeth` (`effect`): Add Junk to your deck. Add Lag to your deck. Gain Jam Cycler.
  - `Sleep in the hum` (`effect`): Heal 10 HP. Next combat: add 1 Junk to your discard.

### Lag Harvester (`lag_harvester_01`)

- Body: A technician harvests delay from failing systems and sells it back as patience.
- Visual Flavor: A slow-turn capacitor with hourglass coils, lag strips, and a technician tapping stalled sparks into jars.
- Base Weight: `5`
- Tags: `status`, `energy`, `relic`, `tradeoff`
- Min Floor: `2`
- Character IDs: `operator`
- Choices:
  - `Buy stored lag` (`effect`): Spend 25 credits. Gain Lag Harvest.
    - Requirements: `{"credits_at_least": 25}`
  - `Harvest your own delay` (`effect`): Increase Protocol Drift by 3%. Add Junk to your deck. Add Lag to your deck. Gain Lag Harvest.
  - `Sell clean timing` (`effect`): Gain 25 credits.

### Null Confessional (`null_confessional_01`)

- Body: A blank-faced confessor listens to every positive effect you never received.
- Visual Flavor: A confession booth made of matte black panels, with null glyphs drifting like snow in the privacy glass.
- Base Weight: `4`
- Tags: `nullified`, `cleanse`, `energy`, `draw`, `corruption`
- Min Floor: `3`
- Choices:
  - `Confess the blocked gains` (`effect`): Next combat: gain 1 Energy on turn 1. Next combat: draw 2 extra cards on turn 1.
  - `Buy the evasion kit` (`effect`): Spend 32 credits. Gain Toll Evasion Kit.
    - Requirements: `{"credits_at_least": 32}`
  - `Let the booth blank you` (`effect`): Spend 12 credits. Reduce Protocol Drift by 5%.
    - Requirements: `{"credits_at_least": 12}`

### Pressure Optician (`pressure_optician_01`)

- Body: An optician fits lenses that make every weak seam feel personally insulting.
- Visual Flavor: A street optician booth with tactical lenses, weak-point reticles, and pressure maps reflected in rain glass.
- Base Weight: `5`
- Tags: `control`, `draw`, `offense`, `relic`
- Min Floor: `2`
- Character IDs: `enforcer`
- Choices:
  - `Fit pressure sight` (`effect`): Spend 24 credits. Gain Pressure Sight.
    - Requirements: `{"credits_at_least": 24}`
  - `Fit exposure grid` (`effect`): Gain Exposure Grid. Next combat: start with 1 Marked.
  - `Let the mesh calibrate` (`effect`): Next combat: draw 1 extra card on turn 1.
    - Requirements: `{"modifier_active": "pressure_mesh"}`

### Protocol Patch Bay (`protocol_patch_bay_01`)

- Body: A maintenance bay offers to patch instability, or sell you the thing causing it.
- Visual Flavor: A clean protocol repair bay with diagnostic arms, a corrupted cassette, and a price list under surgical light.
- Base Weight: `4`
- Tags: `corruption`, `cleanse`, `relic`, `tradeoff`
- Min Floor: `3`
- Choices:
  - `Stabilize the protocol` (`effect`): Spend 24 credits. Reduce Protocol Drift by 8%.
    - Requirements: `{"credits_at_least": 24, "protocol_drift_at_least": 8}`
  - `Install the drift cassette` (`effect`): Gain Protocol Drift. Take 10 damage. Gain Unsafe Overclock. Increase Protocol Drift by 5%.
  - `Patch around the damage` (`effect`): Heal 8. Next combat: add 1 Glitch to discard.

### Red Wastes Pumpjack (`red_wastes_pumpjack_01`)

- Body: A dry pumpjack coughs up heat, ash, and a relic wrapped in old warning tape.
- Visual Flavor: A rusted pumpjack in red dust, pumping ember-black oil into a cracked relic crate.
- Base Weight: `5`
- Tags: `burn`, `relic`, `tradeoff`
- Min Floor: `2`
- Choices:
  - `Take the cooled veil` (`effect`): Take 3 damage. Gain Ash Veil.
  - `Take the feedback coil` (`effect`): Gain Cinder Feedback. Next combat: start with 2 Burn.
  - `Sell the heat-map` (`effect`): Gain 28 credits.

### Relay Grafting Chair (`relay_grafting_chair_01`)

- Body: A mechanic offers to graft a relay directly into your timing nerves.
- Visual Flavor: A reclining graft chair surrounded by relay cubes, timing belts, and a surgeon-mechanic with insulated hands.
- Base Weight: `4`
- Tags: `energy`, `relic`, `corruption`, `tradeoff`
- Min Floor: `3`
- Choices:
  - `Install the overclock relay` (`effect`): Gain Overclock Relay. Take 7 damage. Increase Protocol Drift by 5%.
  - `Install the lag harvester` (`effect`): Gain Lag Harvest. Next combat: add 1 Glitch to discard.
  - `Ask for a harmless tune` (`effect`): Lose 12 credits. Next combat: gain 1 Energy on turn 1.
    - Requirements: `{"credits_at_least": 12}`

### Riot Drill Square (`riot_drill_square_01`)

- Body: A squad of riot trainers offers either discipline or a beating wearing the same helmet.
- Visual Flavor: A fenced training square with riot shields, gyro targets, and sparking baton drones.
- Base Weight: `4`
- Tags: `attack`, `strength`, `relic`, `combat_prep`
- Min Floor: `2`
- Character IDs: `enforcer`
- Choices:
  - `Run the attack cadence` (`effect`): Take 9 damage. Gain Riot Gyro.
  - `Train under plating` (`effect`): Spend 18 credits. Next combat: start with 5 Block.
    - Requirements: `{"credits_at_least": 18}`
  - `Show your plating` (`effect`): Gain 10 credits. Heal 5 HP.
    - Requirements: `{"modifier_active": "riot_plating"}`

### Rot Exchange (`rot_exchange_01`)

- Body: A recycler buys garbage routines and pays better for the ones still twitching.
- Visual Flavor: A rot recycler counter with green index wheels, status-card bins, and a clerk wearing sealed gloves.
- Base Weight: `5`
- Tags: `status`, `deck_edit`, `draw`, `relic`
- Min Floor: `2`
- Character IDs: `bio_hacker`
- Choices:
  - `Trade status for credits` (`effect`): Gain 10 credits. Remove 1 Junk from your deck if present. Remove 1 Lag from your deck if present.
  - `Buy the index wheel` (`effect`): Spend 26 credits. Gain Rot Index.
    - Requirements: `{"credits_at_least": 26}`
  - `Buy the old battery` (`effect`): Spend 18 credits. Gain Rot Battery.
    - Requirements: `{"credits_at_least": 18}`

### Scrap Choir Rehearsal (`scrap_choir_rehearsal_01`)

- Body: Tiny bells in a junk chapel sing only when something useless is destroyed.
- Visual Flavor: A chapel of scrap bells, speaker cones, and shredded status strips hanging like hymn sheets.
- Base Weight: `4`
- Tags: `status`, `heal`, `exhaust`, `relic`, `chain`
- Min Floor: `2`
- Choices:
  - `Join rehearsal` (`effect`): Spend 24 credits. Gain Scrap Choir.
    - Requirements: `{"credits_at_least": 24}`
  - `Feed the hymn` (`effect`): Heal 8 HP. Remove 1 Junk from your deck if present.
  - `Sing through static` (`effect`): Gain 18 credits. Next combat: add 1 Glitch to your discard.

### Septic Distillery (`septic_distillery_01`)

- Body: A hidden still brews infection down into something almost useful.
- Visual Flavor: A bio-still of green fluid coils, pressure gauges, and sealed parasite jars in a warm sewer alcove.
- Base Weight: `4`
- Tags: `infect`, `scaling`, `heal`, `relic`, `tradeoff`
- Min Floor: `2`
- Character IDs: `bio_hacker`
- Choices:
  - `Buy a reservoir vial` (`effect`): Spend 28 credits. Gain Septic Reservoir.
    - Requirements: `{"credits_at_least": 28}`
  - `Drink the distilled parasite` (`effect`): Heal 8 HP. Gain Septic Siphon. Next combat: start with 2 Infect.
  - `Overproof the sample` (`effect`): Gain 20 credits. Increase Protocol Drift by 3%.

### Smuggler Decoder (`smuggler_decoder_01`)

- Body: A decoder kiosk recognizes one of your courier keys and opens an older route.
- Visual Flavor: A smuggler decoder bolted into a service wall, with route glyphs crawling across a stolen transit map.
- Base Weight: `4`
- Tags: `economy`, `shop`, `chain`, `deck_edit`
- Min Floor: `2`
- Choices:
  - `Decode the counterkey` (`effect`): Gain 35 credits.
  - `Buy a market key copy` (`effect`): Spend 26 credits. Gain Market Key.
    - Requirements: `{"credits_at_least": 26}`
  - `Force the decoder` (`effect`): Gain 18 credits. Increase Protocol Drift by 3%.

### Stim Lab (`stim_lab_01`)

- Body: A cracked med-station still pushes live stimulants.
- Visual Flavor: A cracked med-station with open stimulant ports, hanging IV bags, and warning strips over broken clinical glass.
- Base Weight: `5`
- Tags: `combat_prep`, `status_gain`, `merchant_style`, `corruption`
- Choices:
  - `Take the clean stims` (`effect`): Roll a combat-prep status.
  - `Take the dirty stims` (`effect`): Gain 25 credits. Next combat: System Corruption. Increase Protocol Drift by 3%.
  - `Walk past` (`effect`): Walk past.

### Street Choir (`street_choir_01`)

- Body: A signal choir hums through a broken plaza.
- Visual Flavor: A broken plaza full of humming speakers and signal towers, where unseen voices ripple through dust and neon.
- Base Weight: `4`
- Tags: `blessing`, `status_gain`, `recovery`, `cleanse`
- Choices:
  - `Join the choir` (`effect`): Gain Street Choir.
  - `Let the choir retune you` (`effect`): Lose 8 credits. Heal 5. Reduce Protocol Drift by 4%.
    - Requirements: `{"credits_at_least": 8, "protocol_drift_at_least": 20}`
  - `Stay offline` (`effect`): Stay offline.

### Symbiont Soup Kitchen (`symbiont_soup_kitchen_01`)

- Body: A charity kitchen serves broth so alive it tries to remember your name.
- Visual Flavor: A steam-filled soup line under medical lamps, with living broth moving through clear tubing into bowls.
- Base Weight: `5`
- Tags: `heal`, `self_damage`, `offense`, `relic`, `status_risk`
- Min Floor: `2`
- Character IDs: `bio_hacker`
- Choices:
  - `Eat the warm bowl` (`effect`): Heal 14 HP.
  - `Eat the living bowl` (`effect`): Take 6 damage. Increase Protocol Drift by 4%. Gain Symbiont Spindle.
  - `Donate blood` (`effect`): Gain 35 credits. Take 7 damage.

### Warranty Voider (`warranty_voider_01`)

- Body: A ghostly technician offers to void your warranty for a better problem.
- Visual Flavor: A translucent technician peeling warranty stickers off relics while static moths orbit the workbench.
- Base Weight: `4`
- Tags: `shop`, `relic`, `chain`, `tradeoff`
- Min Floor: `3`
- Character IDs: `operator`
- Choices:
  - `Void the warranty` (`effect`): Gain 20 credits. Gain Market Ghost. Remove Ghost Warranty if active.
    - Requirements: `{"modifier_active": "ghost_warranty"}`
  - `Sell the sticker` (`effect`): Gain 26 credits.
  - `Let the ghost tune prices` (`effect`): Gain 18 credits. Increase Protocol Drift by 2%.

## rare

### Auction Seed Vault (`auction_seed_vault_01`)

- Body: A vault of auction seeds grows better choices in exchange for worse instincts.
- Visual Flavor: A gilded vault full of seedboxes, bid tabs, and card silhouettes branching like vines.
- Base Weight: `2`
- Tags: `reward`, `shop`, `economy`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Buy the auction seeder` (`effect`): Spend 50 credits. Gain Auction Seeder.
    - Requirements: `{"credits_at_least": 50}`
  - `Steal a seedbox` (`effect`): Take 10 damage. Increase Protocol Drift by 6%. Gain Auction Seeder.
  - `Take router cuttings` (`effect`): Gain Signal Router. Gain Debt Mark.

### Authority Backdoor (`authority_backdoor_01`)

- Body: An abandoned authority terminal still recognizes one master password and hates everyone else.
- Visual Flavor: A high-security terminal in a dead civic office, three access lights reflected in broken riot glass.
- Base Weight: `2`
- Tags: `energy`, `attack`, `skill`, `power`, `boss_relic`, `corruption`
- Min Floor: `5`
- Choices:
  - `Install the bypass` (`effect`): Take 10 damage. Increase Protocol Drift by 10%. Gain Authority Bypass.
  - `Sell the password` (`effect`): Gain 70 credits.
  - `Route through Triune Module` (`effect`): Reduce Protocol Drift by 3%. Next combat: gain 1 Energy on turn 1.
    - Requirements: `{"modifier_active": "triune_module"}`

### Black Ice Scar (`black_ice_scar_01`)

- Body: A scarred shard promises power and leaves a mark.
- Visual Flavor: A black-ice shard hovering like a cursed sliver of glass, leaving a luminous wound-pattern in the air.
- Base Weight: `2`
- Tags: `curse`, `status_gain`, `anomaly`, `corruption`
- Choices:
  - `Take the scar` (`effect`): Gain Black Ice Scar. Take 6 damage. Increase Protocol Drift by 8%.
  - `Step back` (`effect`): Step back.

### Controlled Bleed Theater (`controlled_bleed_theater_01`)

- Body: A surgical theater teaches wounds to reopen on command.
- Visual Flavor: A red-lit surgical stage with pressure valves, arterial tanks, and a dummy endlessly bleeding in perfect rhythm.
- Base Weight: `2`
- Tags: `bleed`, `draw`, `scaling`, `relic`, `tradeoff`
- Min Floor: `4`
- Character IDs: `enforcer`
- Choices:
  - `Install the bleed valve` (`effect`): Take 8 damage. Gain Controlled Bleed Valve.
  - `Take the arterial tank` (`effect`): Increase Protocol Drift by 4%. Gain Arterial Reservoir. Next combat: start with 2 Bleed.
  - `Sell the technique` (`effect`): Gain 50 credits. Remove 1 Strike from your deck if present.

### Flesh Dividend Clinic (`flesh_dividend_clinic_01`)

- Body: A biotech clinic promises that pain can become profit if you sign before bleeding.
- Visual Flavor: A luxury clinic of blood meters, dividend tickers, and red pumps under spotless white light.
- Base Weight: `2`
- Tags: `self_damage`, `heal`, `strength`, `energy`, `boss_relic`, `tradeoff`
- Min Floor: `5`
- Character IDs: `bio_hacker`
- Choices:
  - `Sign the flesh dividend` (`effect`): Take 12 damage. Increase Protocol Drift by 6%. Gain Flesh Dividend.
  - `Take the recovery payout` (`effect`): Heal 18 HP. Gain Debt Spike.
  - `Audit the clinic` (`effect`): Gain 40 credits.
    - Requirements: `{"modifier_active": "bone_receipt"}`

### Grave Matrix Obelisk (`grave_matrix_obelisk_01`)

- Body: A black obelisk projects every enemy as already half buried.
- Visual Flavor: A grave-black obelisk casting weak and vulnerable grids over ghostly enemy silhouettes.
- Base Weight: `2`
- Tags: `setup`, `aoe`, `control`, `relic`, `chain`
- Min Floor: `4`
- Character IDs: `enforcer`
- Choices:
  - `Install the grave matrix` (`effect`): Spend 40 credits. Gain Grave Matrix.
    - Requirements: `{"credits_at_least": 40}`
  - `Light the grave lantern` (`effect`): Take 8 damage. Gain Grave Lantern.
  - `Offer the first tally` (`effect`): Take 8 damage. Gain Reaper Census.
    - Requirements: `{"modifier_active": "grave_toll"}`

### Mortuary Data Wake (`mortuary_data_wake_01`)

- Body: A funeral for corrupted data invites you to inherit what the dead routines left behind.
- Visual Flavor: A mortuary table covered with data candles, embalmer routers, and status cards folded like mourning paper.
- Base Weight: `2`
- Tags: `status`, `exhaust`, `draw`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Inherit the router` (`effect`): Add Junk to your deck. Add Lag to your deck. Gain Mortuary Router.
  - `Read the wake list` (`effect`): Gain 35 credits.
  - `Pay respects` (`effect`): Heal 6 HP. Remove 1 Junk from your deck if present.

### Mummified Server (`mummified_server_01`)

- Body: A wrapped server stack exhales old power routines through dry cable lungs.
- Visual Flavor: A mummified server cabinet wrapped in insulator strips, with power glyphs glowing beneath the bindings.
- Base Weight: `2`
- Tags: `power`, `cost_reduction`, `combo`, `relic`, `corruption`
- Min Floor: `4`
- Character IDs: `operator`
- Choices:
  - `Unwrap the power wire` (`effect`): Increase Protocol Drift by 6%. Add Glitch to your deck. Gain Mummified Wire.
  - `Harvest the bindings` (`effect`): Gain 40 credits.
  - `Leave the dead server` (`effect`): Reduce Protocol Drift by 2%.

### Protocol Drift Cradle (`protocol_drift_cradle_01`)

- Body: A cradle of corrupted cassettes rocks itself with every hostile signal in the room.
- Visual Flavor: A suspended cradle holding a corrupted protocol cassette, crossed-out control glyphs, and glitch haze leaking downward.
- Base Weight: `2`
- Tags: `corruption`, `status`, `energy`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Take the drift cassette` (`effect`): Take 10 damage. Increase Protocol Drift by 10%. Gain Protocol Drift.
  - `Tune the cassette you already carry` (`effect`): Reduce Protocol Drift by 5%. Add Glitch to your deck.
    - Requirements: `{"modifier_active": "protocol_drift"}`
  - `Seal the cradle` (`effect`): Gain 15 credits. Reduce Protocol Drift by 7%.

### Quarantine Auction (`quarantine_auction_01`)

- Body: Two bidders fight over a sealed vault: one wants safety, the other wants leverage.
- Visual Flavor: An auction stage around a sealed quarantine canister, with green pressure lights and ghostly bid paddles.
- Base Weight: `2`
- Tags: `cleanse`, `reward`, `shop`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Bid on the vault` (`effect`): Spend 45 credits. Gain Quarantine Vault.
    - Requirements: `{"credits_at_least": 45}`
  - `Steal the seed catalog` (`effect`): Take 8 damage. Increase Protocol Drift by 5%. Gain Auction Seeder.
  - `Sell your antibodies` (`effect`): Gain 55 credits. Next combat: start with 1 Infect.

### Recycler Crown Yard (`recycler_crown_yard_01`)

- Body: A crown of shredder teeth rises from the yard, hungry for junk and useful accidents.
- Visual Flavor: A scrap yard throne made of shredder teeth, ticket scraps, and feed rollers glowing with temporary-card light.
- Base Weight: `2`
- Tags: `status`, `generation`, `combo`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Wear the recycler crown` (`effect`): Increase Protocol Drift by 5%. Add Junk to your deck. Add Lag to your deck. Add Glitch to your deck. Gain Recycler Crown.
  - `Sell the teeth` (`effect`): Gain 55 credits.
  - `Feed the old router` (`effect`): Add Control Tower to your deck. Remove 1 Junk from your deck if present.
    - Requirements: `{"modifier_active": "mortuary_router"}`

### Relay Tuner (`relay_tuner_01`)

- Body: A quiet tuner offers to rewrite your stack timing.
- Visual Flavor: A quiet tuning bench filled with signal meters, cable reels, and one delicately calibrated relay core.
- Base Weight: `3`
- Tags: `status_gain`, `combat_prep`, `anomaly`, `corruption`
- Choices:
  - `Optimize the flow` (`effect`): Roll a tuned utility status.
  - `Install echo routing` (`effect`): Gain Echo. Increase Protocol Drift by 3%.
  - `Keep it stock` (`effect`): Keep it stock.

### Spine Core Vespers (`spine_core_vespers_01`)

- Body: A civic prayer service runs on a timer older than the city and twice as strict.
- Visual Flavor: A cathedral-like relay hall with timed civic script ribbons pulsing every third beat.
- Base Weight: `2`
- Tags: `turn_counter`, `draw`, `energy`, `boss_relic`, `corruption`
- Min Floor: `5`
- Choices:
  - `Accept the spine script` (`effect`): Take 8 damage. Increase Protocol Drift by 8%. Gain Spine Script.
  - `Copy one verse` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Interrupt the sermon` (`effect`): Gain 30 credits. Next combat: start with 1 Suppressed.

### Toll Evasion Run (`toll_evasion_run_01`)

- Body: Smugglers offer a full-speed run through null tolls while the city tries to erase your gains.
- Visual Flavor: A speeding smuggler van under null toll arches, with evasion tools sparking across the dashboard.
- Base Weight: `2`
- Tags: `nullified`, `draw`, `energy`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Take the evasion kit` (`effect`): Increase Protocol Drift by 4%. Gain Toll Evasion Kit. Next combat: start with 1 Nullified.
  - `Ride shotgun` (`effect`): Gain 45 credits. Next combat: start with 1 Nullified.
  - `Flash your bypass` (`effect`): Gain 25 credits. Next combat: draw 1 extra card on turn 1.
    - Requirements: `{"modifier_active": "authority_bypass"}`

### Triune Gate (`triune_gate_01`)

- Body: A three-lobed gate opens only when offense, defense, and power arrive in the same breath.
- Visual Flavor: A luminous three-lobed gate with attack, skill, and power faces feeding one central core.
- Base Weight: `2`
- Tags: `attack`, `skill`, `power`, `draw`, `energy`, `boss_relic`
- Min Floor: `5`
- Choices:
  - `Take the triune module` (`effect`): Take 15 damage. Increase Protocol Drift by 8%. Gain Triune Module.
  - `Practice the sequence` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Break one lobe loose` (`effect`): Spend 20 credits. Add Control Tower to your deck.
    - Requirements: `{"credits_at_least": 20}`

### Unstable Chip (`unstable_chip_01`)

- Body: An illicit chip hums with hot, unstable power.
- Visual Flavor: An illicit combat chip resting in shock foam, glowing too hot and unstable for any legal hardware bay.
- Base Weight: `3`
- Tags: `status_risk`, `combat_prep`, `anomaly`, `corruption`
- Choices:
  - `Install the chip` (`effect`): Gain Adrenal Surge. Gain Overheat. Take 7 damage. Increase Protocol Drift by 5%.
  - `Leave it alone` (`effect`): Leave it.

### Verdict Tribunal (`verdict_tribunal_01`)

- Body: A tribunal of obsolete law engines judges targets by how many problems they already have.
- Visual Flavor: A circular tribunal chamber of cracked legal screens, verdict stamps, and execution rails pointed at an empty chair.
- Base Weight: `2`
- Tags: `status`, `offense`, `relic`, `tradeoff`
- Min Floor: `4`
- Choices:
  - `Accept the verdict engine` (`effect`): Take 9 damage. Gain Verdict Engine. Next combat: start with 1 Marked.
  - `Present grave evidence` (`effect`): Gain 30 credits.
    - Requirements: `{"modifier_active": "grave_matrix"}`
  - `Reject jurisdiction` (`effect`): Move on.

### Viral Crown Lab (`viral_crown_lab_01`)

- Body: A crown-shaped culture blooms in a lab that was sealed from the outside.
- Visual Flavor: A sealed biotech lab with a regal infected crown floating in green fluid and warning glyphs scratched into glass.
- Base Weight: `2`
- Tags: `infect`, `aoe`, `scaling`, `heal`, `relic`, `corruption`
- Min Floor: `4`
- Character IDs: `bio_hacker`
- Choices:
  - `Crown the outbreak` (`effect`): Take 8 damage. Increase Protocol Drift by 6%. Gain Viral Relay.
  - `Take the septic crown` (`effect`): Take 7 damage. Gain Septic Crown.
  - `Sterilize the tank` (`effect`): Gain 20 credits. Reduce Protocol Drift by 6%.

## special

### Black Ice Heart (`black_ice_heart_01`)

- Body: The splinter from the cache points toward a beating shard under the city.
- Visual Flavor: A subterranean black-ice heart suspended in frozen data veins, pulsing through blue-black glass.
- Base Weight: `1`
- Tags: `anomaly`, `corruption`, `relic`, `chain`, `special`
- Min Floor: `6`
- Requirements: `{"modifier_active": "protocol_drift"}`
- Choices:
  - `Take the heart shard` (`effect`): Gain a random rare relic. Take 14 damage. Increase Protocol Drift by 12%.
  - `Seal it in a vault` (`effect`): Reduce Protocol Drift by 8%. Gain Quarantine Vault.
  - `Leave the heart beating` (`effect`): Heal 10 HP.

### Choir Beneath the City (`choir_beneath_city_01`)

- Body: Every broken speaker in the undercity sings the same note and waits for you to harmonize.
- Visual Flavor: A vast undercity chamber full of stacked speakers, scrap bells, and signal towers singing into green fog.
- Base Weight: `1`
- Tags: `blessing`, `heal`, `status`, `chain`, `special`
- Min Floor: `5`
- Requirements: `{"modifier_active": "street_choir"}`
- Choices:
  - `Harmonize cleanly` (`effect`): Heal 15 HP. Reduce Protocol Drift by 10%.
  - `Let the scrap choir answer` (`effect`): Add Junk to your deck. Gain Scrap Choir.
  - `Sing the unstable note` (`effect`): Increase Protocol Drift by 6%. Gain Symbiont Spindle. Next combat: start with 1 Infect.

### Debt Court (`debt_court_01`)

- Body: Your debts are tried by a court where the judge is a contract and the jury is interest.
- Visual Flavor: A courtroom of contract paper, debt needles, and credit counters stacked like witness stands.
- Base Weight: `1`
- Tags: `curse`, `economy`, `chain`, `special`
- Min Floor: `5`
- Requirements: `{"modifier_active": "debt_mark"}`
- Choices:
  - `Pay judgment` (`effect`): Spend 45 credits. Remove Debt Mark if active. Remove Debt Spike if active. Reduce Protocol Drift by 4%.
    - Requirements: `{"credits_at_least": 45}`
  - `Declare violent bankruptcy` (`effect`): Take 12 damage. Remove Debt Mark if active. Remove Debt Spike if active. Gain 20 credits.
  - `Accept the court dividend` (`effect`): Increase Protocol Drift by 8%. Gain Flesh Dividend. Gain Debt Spike.

### Glitch Shrine (`glitch_shrine_01`)

- Body: A shrine of scavenged monitors flickers between blessing and malfunction.
- Visual Flavor: A shrine of stacked scavenged monitors, candles of static, and looping error prayers flickering between grace and failure.
- Base Weight: `2`
- Tags: `anomaly`, `status_risk`, `narrative`, `corruption`
- Min Floor: `3`
- Exclusion Tags: `anomaly`
- Choices:
  - `Embrace the glitch` (`effect`): Roll a volatile anomaly status. Increase Protocol Drift by 6%.
  - `Sign in blood` (`effect`): Gain Blood Pact.
  - `Leave it alone` (`effect`): Leave it.

### Grave Census Final (`grave_census_final_01`)

- Body: The census clerk finds the missing column: your name, written before the fight.
- Visual Flavor: A final census hall with skull tablets, grave lanterns, and a black ledger opened to the player line.
- Base Weight: `1`
- Tags: `kill`, `control`, `energy`, `chain`, `special`
- Min Floor: `6`
- Requirements: `{"modifier_active": "reaper_census"}`
- Choices:
  - `Accept official count` (`effect`): Refresh Reaper Census. Take 8 damage. Gain 25 credits.
  - `Light every lantern` (`effect`): Gain Grave Lantern.
  - `Erase your line` (`effect`): Spend 20 credits. Heal 18 HP. Reduce Protocol Drift by 6%.
    - Requirements: `{"credits_at_least": 20}`

### Infection Bloom Parade (`infection_bloom_parade_01`)

- Body: A parade of infected lanterns blooms through the district, spreading celebration like a symptom.
- Visual Flavor: A festival street of green infection lanterns, masked dancers, and spore-light drifting over wet asphalt.
- Base Weight: `1`
- Tags: `infect`, `aoe`, `heal`, `chain`, `special`
- Min Floor: `6`
- Requirements: `{"modifier_active": "septic_crown"}`
- Character IDs: `bio_hacker`
- Choices:
  - `Crown the parade` (`effect`): Refresh Septic Crown. Heal 12 HP. Take 7 damage.
  - `Release the relay spores` (`effect`): Increase Protocol Drift by 6%. Gain Viral Relay. Next combat: start with 1 Infect.
  - `Wear the parasite seal` (`effect`): Heal 18 HP.

### Market Ghost Reunion (`market_ghost_reunion_01`)

- Body: The market ghost meets its own warranty clerk and both insist the other one died owing you money.
- Visual Flavor: A midnight market stall where a ghost clerk and warranty phantom argue over one glowing receipt.
- Base Weight: `1`
- Tags: `shop`, `economy`, `chain`, `special`
- Min Floor: `5`
- Requirements: `{"modifier_active": "market_ghost"}`
- Choices:
  - `Settle the receipt` (`effect`): Refresh Market Ghost. Gain 25 credits.
  - `Audit the ghosts` (`effect`): Gain 60 credits. Remove Ghost Warranty if active.
  - `Sign the spectral ledger` (`effect`): Increase Protocol Drift by 7%. Gain Auction Seeder. Gain Debt Mark.

### Protocol Eclipse (`protocol_eclipse_01`)

- Body: Your protocol shadow moves a second before you do, and the city briefly follows it instead.
- Visual Flavor: A total eclipse of UI glyphs around the player silhouette, with corrupted duplicates moving out of sync.
- Base Weight: `1`
- Tags: `corruption`, `anomaly`, `relic`
- Min Floor: `6`
- Requirements: `{"protocol_drift_at_least": 50}`
- Choices:
  - `Anchor yourself` (`effect`): Lose 25 credits. Reduce Protocol Drift by 20%. Remove 1 Glitch from your deck if present.
    - Requirements: `{"credits_at_least": 25}`
  - `Take the eclipse core` (`effect`): Gain a rare corruption relic. Take 18 damage. Increase Protocol Drift by 12%. Add Glitch and Black Ice Bloom to your deck.
  - `Let the cassette feed` (`effect`): The first Glitch you draw in the next three combats grants 1 extra Energy. Increase Protocol Drift by 5%.
    - Requirements: `{"modifier_active": "protocol_drift"}`

### Quarantine Saint (`quarantine_saint_01`)

- Body: A saint of sealed doors offers mercy only after proving you can survive the lock.
- Visual Flavor: A luminous quarantine figure behind green pressure glass, surrounded by masks, dampeners, and sealed relic cases.
- Base Weight: `1`
- Tags: `cleanse`, `enemy_status`, `heal`, `chain`, `special`
- Min Floor: `6`
- Requirements: `{"protocol_drift_at_least": 35}`
- Choices:
  - `Accept containment` (`effect`): Take 10 damage. Increase Protocol Drift by 5%. Gain Quarantine Vault.
  - `Receive absolution` (`effect`): Heal 20 HP. Reduce Protocol Drift by 15%.
  - `Weaponize the seal` (`effect`): Gain Toll Spike. Gain Null Damper. Next combat: start with 1 Suppressed.

### Spine Breach (`spine_breach_01`)

- Body: The Spine Core opens a service hatch and asks whether you want timing, authority, or escape.
- Visual Flavor: A breached civic core corridor with tri-channel locks, authority keys, and timed script pulses receding into darkness.
- Base Weight: `1`
- Tags: `energy`, `draw`, `boss_relic`, `chain`, `special`
- Min Floor: `7`
- Requirements: `{"modifier_active": "authority_bypass"}`
- Choices:
  - `Claim civic authority` (`effect`): Refresh Authority Bypass. Gain 30 credits. Increase Protocol Drift by 6%.
  - `Claim perfect timing` (`effect`): Increase Protocol Drift by 6%. Gain Spine Script.
  - `Escape through the breach` (`effect`): Gain 75 credits. Reduce Protocol Drift by 8%.

### Zero-Day Masquerade (`zero_day_masquerade_01`)

- Body: Every guest wears the same mask: zero cost, no receipt, no memory.
- Visual Flavor: A neon masquerade where masks are shaped like zero-cost glyphs and power wires hang like streamers.
- Base Weight: `1`
- Tags: `zero_cost`, `cost_reduction`, `combo`, `chain`, `special`
- Min Floor: `6`
- Requirements: `{"modifier_active": "queue_mirror"}`
- Choices:
  - `Dance the free sequence` (`effect`): Next combat: draw 1 extra card on turn 1.
  - `Steal a power mask` (`effect`): Increase Protocol Drift by 8%. Add Glitch to your deck. Gain Mummified Wire.
  - `Sell the invitation` (`effect`): Gain 65 credits.
