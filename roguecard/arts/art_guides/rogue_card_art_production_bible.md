# Rogue Card Art Production Bible

This document is a production brief for generating **card art atlases** and **relic icon atlases** that Codex can slice into the game. It is built around the updated data references: **63 cards** grouped across `bio_hacker`, `enforcer`, `operator`, and `shared`, plus **19 relics** across common, uncommon, and rare tiers. The goal is to keep the functional readability of *Slay the Spire* card/relic art while making the visuals distinctly **cyberpunk**, **faction-driven**, and **cutout-friendly**.

## 1. Core art direction

- **Cards** should read like *Slay the Spire*-style illustration panels: one strong focal subject, limited background clutter, readable silhouette at small size, and original cyberpunk faction motifs. Do **not** render the card frame, text box, cost gem, rarity pips, or type line on the sheet. The atlas should contain the **art crop only**.
- **Relics** should be even simpler: a single centered icon/object on a dark background, with minimal ambient FX. Think “cutout-friendly relic sprite” first, scene painting second. Effects such as Bleed, Burn, Infect, Suppressed, or Nullified should mostly be added **in-game** as separate FX, not baked into the relic icon as giant halos.
- **Do not copy Slay the Spire art directly.** Borrow the readability, restraint, and gameplay clarity, but keep the object design, materials, faction styling, and color language original to *Rogue Card*.

### Material / micro-style language

- **signal_mesh** = cleaner support/control look; scanners, grids, shields, data mesh, calmer compositions.
- **patch_grid** = rough patched look; stitched tech, scavenged hardware, body-mod pain, organs, jury-rigged machinery.
- **circuit_burst** = high-energy attack look; brighter motion arcs, muzzle flash, discharge, sharper impact silhouettes.

### Faction palette pillars

- **Bio Hacker**: Use toxic verdant greens, bruised flesh tones, amber serum glass, and oily black hardware. Organic biotech forms should feel invasive but readable.
- **Enforcer**: Use crimson, rust, warning amber, soot black, and battered steel. Shapes should be blunt, heavy, and riot-gear adjacent.
- **Operator**: Use cool teal, cyan, slate navy, white UI glow, and sparse electric blue accents. Shapes should feel sleek, precise, and high-control.
- **Shared**: Use neutral steel, muted amber, off-white, and small cyan accents. Shared cards should feel universal, modular, and less faction-specific.

### Enemy / status motif appendix for visual consistency

- **Blackwire Directorate**: compliance tech, drones, signal towers, reticles, suppression batons, null-tech, cold navy/cyan/white.
- **Cinder Jackals**: road dust, chain weapons, scrap guns, furnace heat, ember orange, rust red, gang brutality.
- **Helix Ward**: biotech flesh, serum glass, organ grafts, parasite tubing, verdant infect glow, wet medical horror.
- **Red Wastes**: carrion hunters, desert scrap, bone, sand, bleeding cuts, ochre dust, survivalist brutality.
- **Grayspine General**: austere military machine design, gatehouse armor, grey-white suppression technology.

### Core status FX language

- **Bleed**: razor-red slashes, droplets, cable cuts, meat-hook marks.
- **Weak**: unstable yellow/cyan reticle wobble, blurred waveform, staggered posture lines.
- **Vulnerable**: cracked armor, exposed seam, fracture highlight, opened target plate.
- **Infect**: verdant spores, biotech fluid, septic bubbles, invasive growth.
- **Burn**: ember orange, ash flecks, heated metal, scorched ticket residue.
- **Marked**: reticle brackets, white compliance tags, target ping circles.
- **Suppressed**: muted waveform, crossed muzzle, compression rings, downward-force lines.
- **Nullified**: empty hex, slashed circuit glyph, deadened glow, blanking field.

## 2. Atlas recommendations

### Relic atlas

- Keep the **existing relic sheet visual format**: dark navy background, gold slot frames, item name above, coordinate label below, and one centered object per slot.
- Preserve slots **000-008** so the current Codex slicing/mapping remains stable. Append the 10 new relics as **009-018** on the same atlas.
- Continue using the current relic slot footprint: **220 x 220** art windows with **18 px gutters** and the current offset pattern (x starts at 28, y starts at 112).
- Do not over-decorate the icon. A tiny spark, spore, heat ribbon, or signal ring is fine; a giant aura is not.

### Card atlases

- Preferred pipeline: **one sheet per owner**: Bio-Hacker, Enforcer, Operator, and Shared. This keeps palette drift under control and makes Codex slicing simpler.
- Recommended reference layout: **5 columns**, **320 x 240** art windows, **24 px gutters**, dark navy sheet background, and slot metadata outside the art crop if needed.
- The art window should contain **only the illustration panel**. No card frame, no text, no cost circles, no rules text, and no logos.
- Each panel should fit a **single clear focal subject** or **very tight action vignette**. Avoid crowd scenes, tiny secondary figures, or large perspective backgrounds that collapse at card size.

### Card sheet grouping

- **Bio-Hacker card sheet**: 17 cards.
- **Enforcer card sheet**: 17 cards.
- **Operator card sheet**: 17 cards.
- **Shared / starter / status card sheet**: 12 cards.

## 3. Relic atlas manifest and art briefs

**Status key**: `Existing` = already represented on the current relic sprite sheet reference. `New` = should be added on the expanded atlas.

### R000 — Carbon Weave (`carbon_weave`) — Existing

- **Rarity / sources**: common; run_start
- **Gameplay read**: Start each combat with 5 Block.
- **Visual brief**: A beveled square of carbon-fiber weave with stitched or riveted corners.
- **Cutout note**: Preserve the simple plate silhouette from the current sheet.
- **Tags**: defense, blessing

### R001 — Flash Cache (`flash_cache`) — Existing

- **Rarity / sources**: common; run_start
- **Gameplay read**: Draw 1 extra card on turn 1.
- **Visual brief**: A compact datastick with a bright cyan cache core.
- **Cutout note**: Simple 3/4 angle, cutout-friendly.
- **Tags**: draw, blessing

### R002 — Plated Grip (`plated_grip`) — Existing

- **Rarity / sources**: common; run_start
- **Gameplay read**: Add Firewall to the starting deck.
- **Visual brief**: A plated armored glove with chunky defensive knuckles.
- **Cutout note**: One glove, no hand attached.
- **Tags**: defense, blessing

### R003 — Shard Seed (`shard_seed`) — Existing

- **Rarity / sources**: common; run_start
- **Gameplay read**: Add Cache Draw to the starting deck.
- **Visual brief**: A green crystal seed nested in a dark industrial housing.
- **Cutout note**: Bright center crystal, restrained outer casing.
- **Tags**: draw, blessing

### R004 — Surge Fuse (`surge_fuse`) — Existing

- **Rarity / sources**: common; run_start
- **Gameplay read**: Add Surge Strike to the starting deck.
- **Visual brief**: A glass fuse tube holding a bright blue electrical surge.
- **Cutout note**: Keep the icon slim and high contrast.
- **Tags**: offense, blessing

### R005 — Signal Router (`signal_router`) — Existing

- **Rarity / sources**: rare; run_start
- **Gameplay read**: Card rewards show 1 extra choice.
- **Visual brief**: A small router box with dual antennas and a bright signal display.
- **Cutout note**: Maintain the readable box-and-antennas silhouette.
- **Tags**: draw, blessing

### R006 — Clean Slate (`clean_slate`) — Existing

- **Rarity / sources**: uncommon; run_start
- **Gameplay read**: The first purge each run is free.
- **Visual brief**: A handheld tablet with a clean blue screen and a physical eraser block clipped to one edge.
- **Cutout note**: Readable and simple; almost stationery-tech.
- **Tags**: shop, blessing

### R007 — Market Key (`market_key`) — Existing

- **Rarity / sources**: uncommon; run_start
- **Gameplay read**: Shop card prices cost 15% less.
- **Visual brief**: A brass-steel key with a green chip insert and secure cut teeth.
- **Cutout note**: Keep the shape elegant and iconic.
- **Tags**: economy, shop, blessing

### R008 — Overclock Relay (`overclock_relay`) — Existing

- **Rarity / sources**: uncommon; run_start
- **Gameplay read**: Gain 1 extra Energy on turn 1.
- **Visual brief**: A heavy relay cube with a cooling fan, cables, and a small orange status LED.
- **Cutout note**: Preserve the squat box silhouette from the current sheet.
- **Tags**: energy, blessing

### R009 — Butcher Hooks (`butcher_hooks`) — New

- **Rarity / sources**: common; elite_reward, shop
- **Gameplay read**: The first time each turn you apply Bleed, deal 3 damage to that enemy.
- **Visual brief**: A pair of industrial butcher hooks on a cable hub, stained steel with one sharp red accent.
- **Cutout note**: Keep the silhouette simple enough to read as a small cutout icon.
- **Tags**: bleed, offense

### R010 — Field Dampener (`field_dampener`) — New

- **Rarity / sources**: common; elite_reward, shop
- **Gameplay read**: The first time each combat you gain Burn, Bleed, Infect, Suppressed, or Nullified, gain 5 Block.
- **Visual brief**: A palm-sized dampening puck or collar coil with concentric rings that absorb hostile status energy.
- **Cutout note**: Show containment, not offense.
- **Tags**: defense, enemy_status

### R011 — Rot Battery (`rot_battery`) — New

- **Rarity / sources**: common; elite_reward, shop
- **Gameplay read**: The first time you draw a status card each turn, gain 3 Block.
- **Visual brief**: A corroded battery canister or cell with verdant seepage and stitched casing seams.
- **Cutout note**: This should feel bio-hacker adjacent but still relic-simple.
- **Tags**: status, defense

### R012 — Execution Array (`execution_array`) — New

- **Rarity / sources**: rare; boss_reward, elite_reward
- **Gameplay read**: The first time each turn you hit an enemy that has a combat status, deal 3 bonus damage and draw 1 card.
- **Visual brief**: A compact execution module with a sensor eye and three deployable blades or rails.
- **Cutout note**: Rare relic; make it elegant and dangerous.
- **Tags**: status, offense, draw

### R013 — Grave Lantern (`grave_lantern`) — New

- **Rarity / sources**: rare; boss_reward, elite_reward
- **Gameplay read**: Start each combat by applying 1 Weak and 1 Bleed to all enemies.
- **Visual brief**: A black lantern venting red bleed haze and pale green weakening fumes.
- **Cutout note**: Use one lantern silhouette and subtle dual-color vapor.
- **Tags**: aoe, status, setup

### R014 — Grave Pick (`grave_pick`) — New

- **Rarity / sources**: uncommon; elite_reward, shop
- **Gameplay read**: The first enemy that dies each combat grants 1 Energy next turn.
- **Visual brief**: A compact grave pick or powered miner’s pick with a small energy cell in the shaft.
- **Cutout note**: Uncommon relic; simple but slightly mean.
- **Tags**: kill, energy

### R015 — Jam Cycler (`jam_cycler`) — New

- **Rarity / sources**: uncommon; elite_reward, shop
- **Gameplay read**: Whenever a status card is exhausted, deal 3 damage to a random enemy.
- **Visual brief**: A grinder gearbox or cassette shredder with jammed status strips caught in its teeth.
- **Cutout note**: It should feel like it chews through status cards.
- **Tags**: status, offense

### R016 — Null Damper (`null_damper`) — New

- **Rarity / sources**: uncommon; elite_reward, shop
- **Gameplay read**: The first time each combat you would gain Suppressed or Nullified, prevent 1 stack and draw 1 card.
- **Visual brief**: A blanking muffler coil or nullifier puck with a muted signal emblem.
- **Cutout note**: Control relic; feel suppressive and defensive.
- **Tags**: control, cleanse

### R017 — Pressure Sight (`pressure_sight`) — New

- **Rarity / sources**: uncommon; elite_reward, shop
- **Gameplay read**: The first time each turn you apply Weak or Vulnerable, draw 1 card.
- **Visual brief**: A cyber monocle or tactical lens projecting a weak-point reticle.
- **Cutout note**: Let the lens shape dominate; only small UI accents.
- **Tags**: control, draw

### R018 — Septic Reservoir (`septic_reservoir`) — New

- **Rarity / sources**: uncommon; elite_reward, shop
- **Gameplay read**: At end of your turn, the enemy with the highest Infect gains 1 Infect.
- **Visual brief**: A hanging septic fluid reservoir or vial bank filled with thick infected green fluid.
- **Cutout note**: Readable glass-and-liquid silhouette, not a full lab scene.
- **Tags**: infect, scaling

## 4. Card sheet manifests and art briefs

## Bio-Hacker card sheet

- **Palette guide**: Use toxic verdant greens, bruised flesh tones, amber serum glass, and oily black hardware. Organic biotech forms should feel invasive but readable.
- **Recommended sheet label**: `bio_card_sheet_reference`
- **Slot count**: 17

### BIO000 — Blood Buffer (`bio_blood_buffer_01`)

- **Type / cost / gameplay**: skill / 1 — Heal 3 HP. Gain 5 Block.
- **Visual brief**: A suspended blood-buffer canister swelling into a protective bio-shield, with green-lit tubing and a semi-translucent crimson fluid core.
- **Composition note**: Keep it as one centered medical object with a readable shield silhouette.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### BIO001 — Coagulate (`bio_coagulate_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 7 Block. Heal 2 HP.
- **Visual brief**: A clotting spray or gel cartridge hardening into a dark biogel plate over an arm or rib panel.
- **Composition note**: Show flesh-and-tech sealing together instead of a full character scene.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### BIO002 — Harvest Bite (`bio_harvest_bite_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 4 damage 2 times. Apply 1 Infect.
- **Visual brief**: A biomech jaw or injector-fang assembly snapping shut twice, spitting infected green droplets.
- **Composition note**: Lean into predatory biotech rather than a normal knife attack.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO003 — Hemorrhage (`bio_hemorrhage_01`)

- **Type / cost / gameplay**: attack / 1 — Lose 2 HP. Deal 11 damage.
- **Visual brief**: A self-piercing injector blade or puncture gun drawing neon blood to fuel a violent forward strike.
- **Composition note**: The self-damage cost should read through a small blood pull, not a gore splash.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO004 — Leech Jab (`bio_leech_jab_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 5 damage. Apply 1 Infect. Heal 1 HP.
- **Visual brief**: A narrow syringe gauntlet punching in and siphoning glowing fluid back through clear tubing.
- **Composition note**: One strong jab shape plus return-flow hose is enough.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO005 — Pain Circuit (`bio_pain_circuit_01`)

- **Type / cost / gameplay**: power / 1 — `turn_start` -> Gain 1 Strength. Add 1 `status_junk_01` status card to discard.
- **Visual brief**: A rib-mounted pain-feedback circuit board with exposed leads, one junk cartridge, and a harsh green pulse.
- **Composition note**: Make it feel like a permanent body mod, not a handheld item.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO006 — Pain Probe (`bio_pain_probe_01`)

- **Type / cost / gameplay**: attack / 0 — Lose 1 HP. Deal 6 damage.
- **Visual brief**: A slim biopsy spike or shock-lancet thrusting forward with a sharp green flash.
- **Composition note**: Fast, compact, and needle-like.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO007 — Parasite Fang (`bio_parasite_fang_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 8 damage. Apply 2 Infect. Heal 2 HP.
- **Visual brief**: A heavier parasite harpoon or injector-fang with hooked mandibles and pumping serum canisters.
- **Composition note**: This should read as a premium infect finisher.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### BIO008 — Reclaimer (`bio_reclaimer_01`)

- **Type / cost / gameplay**: skill / 0 — Lose 2 HP. Gain 1 Energy.
- **Visual brief**: A cracked stim canister or recycler pump feeding reclaimed charge into a gauntlet.
- **Composition note**: Show loss-for-power conversion rather than a heal effect.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO009 — Rot Harvest (`bio_rot_harvest_01`)

- **Type / cost / gameplay**: power / 1 — `on_status_drawn` -> Gain 1 Energy. Heal 1 HP. Exhaust the drawn card.
- **Visual brief**: A grimy rot harvester crucible converting burned status scraps into green energy and a heartbeat pulse.
- **Composition note**: Use a small furnace or grinder silhouette with status trash being consumed.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### BIO010 — Rot Slash (`bio_rot_slash_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 7 damage. Add 1 `status_burn_01` status card to discard.
- **Visual brief**: A corroded scalpel or mono-blade leaving a toxic ember slash and a burning residue ticket behind it.
- **Composition note**: The burn-status tie-in should be visible as residue, ash, or a cursed scrap.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### BIO011 — Scar Tissue (`bio_scar_tissue_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 7 Block.
- **Visual brief**: Layered scar tissue and synthetic mesh knitting into a hard defensive patch.
- **Composition note**: Favor close-up body-tech texture over a scene.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### BIO012 — Septic Round (`bio_septic_round_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 4 damage. Apply 2 Infect.
- **Visual brief**: A toxic syringe round or septic casing rupturing with thick green droplets.
- **Composition note**: Read as ammunition with infection, not generic poison.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### BIO013 — Spare Organs (`bio_spare_organs_01`)

- **Type / cost / gameplay**: skill / 0 — Lose 2 HP. Draw 2 cards.
- **Visual brief**: A field cooler of cloned organs and preserved tissue packs ready for emergency use.
- **Composition note**: Keep the silhouette tidy and game-readable.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### BIO014 — Symbiote Mesh (`bio_symbiote_mesh_01`)

- **Type / cost / gameplay**: power / 1 — `on_self_damage` -> Heal 2 HP.
- **Visual brief**: A living symbiote mesh wrapping an arm or torso and pulsing with mutual healing light.
- **Composition note**: Make the mesh feel alive but not monstrous.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### BIO015 — Triage Loop (`bio_triage_loop_01`)

- **Type / cost / gameplay**: skill / 1 — Heal 4 HP. Draw 1 card.
- **Visual brief**: A compact auto-doc halo cycling syringes around a medical ring and heart monitor pulse.
- **Composition note**: This should feel like clinical speed and efficiency.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### BIO016 — Waste Recycler (`bio_waste_recycler_01`)

- **Type / cost / gameplay**: skill / 0 — Add 1 `status_junk_01` status card to discard. Gain 1 Energy. Draw 1 card.
- **Visual brief**: A stained recycler grinder chewing junk into charge and card flow.
- **Composition note**: One junk chute, one spinning chamber, one output glow.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

## Enforcer card sheet

- **Palette guide**: Use crimson, rust, warning amber, soot black, and battered steel. Shapes should be blunt, heavy, and riot-gear adjacent.
- **Recommended sheet label**: `enf_card_sheet_reference`
- **Slot count**: 17

### ENF000 — Bash Protocol (`enforcer_bash_protocol_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 7 damage. Apply 1 Bleed.
- **Visual brief**: An armored baton or steel fist impact with fresh red slash trails and a brutal bleed marker.
- **Composition note**: Heavy contact frame; no fancy environment.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### ENF001 — Battle Roar (`enforcer_battle_roar_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 1 Strength. Draw 1 card.
- **Visual brief**: A masked enforcer barking through a vox grille, projecting a crimson shockwave.
- **Composition note**: The voice burst should be the main shape.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### ENF002 — Blood Rush (`enforcer_blood_rush_01`)

- **Type / cost / gameplay**: attack / 1 — Lose 3 HP. Deal 12 damage.
- **Visual brief**: A reckless forward lunge driven by a self-cut palm and a brutal cleaver or stock strike.
- **Composition note**: Show commitment and momentum, not finesse.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF003 — Breaker Line (`enforcer_breaker_line_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 11 damage. Apply 2 Bleed.
- **Visual brief**: A breach maul or breaker hammer splitting armor in a single harsh line.
- **Composition note**: This should feel like armor-breaking force.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### ENF004 — Chain Assault (`enforcer_chain_assault_01`)

- **Type / cost / gameplay**: power / 1 — `turn_start` -> Modify the next attack damage by 3.
- **Visual brief**: A chain-fed attack rig, shell feeder, or strike counter spooling up the next hit.
- **Composition note**: Use machinery and repetition instead of a character pose.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### ENF005 — Crackdown (`enforcer_crackdown_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 6 damage. Apply 2 Vulnerable.
- **Visual brief**: A stun baton and lock-on reticle pinning the target into a vulnerable opening.
- **Composition note**: The vulnerability setup is more important than raw impact.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### ENF006 — Double Tap (`enforcer_double_tap_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 4 damage 2 times.
- **Visual brief**: Two quick muzzle flares or mirrored baton strikes hitting in immediate succession.
- **Composition note**: Keep the composition symmetric and punchy.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### ENF007 — Feed Aggression (`enforcer_feed_aggression_01`)

- **Type / cost / gameplay**: skill / 0 — Modify the next attack damage by 5.
- **Visual brief**: A red stimulant injector or adrenal canister slammed into an armored gauntlet.
- **Composition note**: The buff source should read instantly.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### ENF008 — Gouge (`enforcer_gouge_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 5 damage. Apply 2 Bleed.
- **Visual brief**: A hooked blade tearing across armor with a mean red bleed trail.
- **Composition note**: Sharper and nastier than Bash Protocol.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF009 — Guard Stance (`enforcer_guard_stance_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 8 Block.
- **Visual brief**: A riot shield braced low with sparks skipping off its edge.
- **Composition note**: Pure defensive silhouette, simple and iconic.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### ENF010 — Hard Commit (`enforcer_hard_commit_01`)

- **Type / cost / gameplay**: skill / 0 — Lose 2 HP. Gain 2 Energy.
- **Visual brief**: A danger-marked overdrive switch rammed fully forward.
- **Composition note**: This is a decision image: one switch, one surge, no scene clutter.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF011 — Open Wound (`enforcer_open_wound_01`)

- **Type / cost / gameplay**: skill / 0 — Lose 2 HP. Gain 1 Strength.
- **Visual brief**: A deliberate palm slash or wound-port being opened to feed strength.
- **Composition note**: Controlled self-harm, not gore.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF012 — Ram Guard (`enforcer_ram_guard_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 6 Block. Draw 1 card.
- **Visual brief**: A shield-first shoulder rush keeping a defensive plate between user and target.
- **Composition note**: Blend protection and impact in one silhouette.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### ENF013 — Redline Core (`enforcer_redline_core_01`)

- **Type / cost / gameplay**: power / 2 — `turn_start` -> Lose 2 HP. Gain 2 Strength.
- **Visual brief**: A glowing reactor heart with hazard needles, red gauges, and overheating vents.
- **Composition note**: One clear core object; it should feel dangerous to run.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF014 — Riot Barrage (`enforcer_riot_barrage_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 5 damage 3 times.
- **Visual brief**: A triple-hit barrage of shotgun blasts, shells, or baton flashes in a hard rhythm.
- **Composition note**: Use three beats of motion, not a busy firefight.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### ENF015 — Spiked Harness (`enforcer_spiked_harness_01`)

- **Type / cost / gameplay**: power / 1 — `on_self_damage` -> Gain 3 Block.
- **Visual brief**: A brutal chest harness of spikes and reactive plates that flash when struck.
- **Composition note**: Show defensive retaliation through spikes and short red sparks.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### ENF016 — War Engine (`enforcer_war_engine_01`)

- **Type / cost / gameplay**: power / 1 — `turn_start` -> Gain 1 Strength.
- **Visual brief**: A compact war engine or piston heart building pressure every turn.
- **Composition note**: Mechanical strength-gain icon rather than a full mech.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

## Operator card sheet

- **Palette guide**: Use cool teal, cyan, slate navy, white UI glow, and sparse electric blue accents. Shapes should feel sleek, precise, and high-control.
- **Recommended sheet label**: `opr_card_sheet_reference`
- **Slot count**: 17

### OPR000 — Auto-Tuner (`operator_auto_tuner_01`)

- **Type / cost / gameplay**: power / 1 — `turn_start` -> Modify the next card cost by -1.
- **Visual brief**: A sleek tuning module with dial, waveform, and cost bars dropping into perfect alignment.
- **Composition note**: Calm precision, teal UI glow, one device.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR001 — Backdoor (`operator_backdoor_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 7 damage. Modify the next card cost by -1.
- **Visual brief**: A data knife or exploit spike plugged into a secure port.
- **Composition note**: The hack-insertion moment should be the image.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR002 — Cache Cycle (`operator_cache_cycle_01`)

- **Type / cost / gameplay**: skill / 1 — Draw 2 cards.
- **Visual brief**: A rotating holo-cache carousel or stack of smart cartridges cycling forward.
- **Composition note**: This should read as elegant card flow.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR003 — Cold Read (`operator_cold_read_01`)

- **Type / cost / gameplay**: skill / 1 — Draw 3 cards.
- **Visual brief**: A wafer-thin dossier or holographic case file opening into a pale blue scan.
- **Composition note**: Keep it cool, analytical, and slightly detached.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery
- **Keyword emphasis**: `exhaust`

### OPR004 — Control Tower (`operator_control_tower_01`)

- **Type / cost / gameplay**: power / 1 — `after_card_played` -> Gain 1 Block.
- **Visual brief**: A compact antenna tower or drone uplink with concentric signal rings.
- **Composition note**: The tower silhouette should dominate.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR005 — Deep Cache (`operator_deep_cache_01`)

- **Type / cost / gameplay**: power / 1 — `turn_start` -> Draw 1 card.
- **Visual brief**: A hidden vault drawer or encrypted memory block opening one layer deeper.
- **Composition note**: Less action, more hidden value.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### OPR006 — Deflect Mesh (`operator_deflect_mesh_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 6 Block. Draw 1 card.
- **Visual brief**: A clean hex-mesh barrier unfolding from a wrist projector.
- **Composition note**: Emphasize the mesh pattern and neat geometry.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR007 — Lock In (`operator_lock_in_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 4 Block. Draw 1 card.
- **Visual brief**: A targeting clamp or software lock icon freezing a decision in place.
- **Composition note**: Stable composition; nothing chaotic.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions
- **Keyword emphasis**: `retain`

### OPR008 — Needle Ping (`operator_needle_ping_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 4 damage. Apply 1 Weak.
- **Visual brief**: A precision flechette or needle round tagged with a weakening signal blip.
- **Composition note**: Small shot, smart debuff, teal ping line.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR009 — Packet Storm (`operator_packet_storm_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 3 damage 2 times. Draw 1 card.
- **Visual brief**: A swarm of data packets or micro-drones flooding a target lane.
- **Composition note**: The storm should feel controlled, not messy.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### OPR010 — Priority Queue (`operator_priority_queue_01`)

- **Type / cost / gameplay**: skill / 0 — Modify the next card cost by -1. Draw 1 card.
- **Visual brief**: Stacked priority bars, arrow tracks, and a queue chip bubbling to the top.
- **Composition note**: Simple UI-object composition is ideal.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR011 — Quiet Cut (`operator_quiet_cut_01`)

- **Type / cost / gameplay**: attack / 0 — Deal 5 damage.
- **Visual brief**: A matte-black vibro knife slicing cleanly with minimal flare.
- **Composition note**: Short, silent, and efficient.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### OPR012 — Recompile Shot (`operator_recompile_shot_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 10 damage. Modify the next card cost by -1.
- **Visual brief**: A charged rifle shot breaking into teal code fragments as the next move gets cheaper.
- **Composition note**: One rifle/beam plus code breakup is enough.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### OPR013 — Relay Shot (`operator_relay_shot_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 7 damage. Draw 1 card.
- **Visual brief**: A shot bouncing through relay nodes or a signal repeater sightline.
- **Composition note**: Use one projectile path with relay beacons.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR014 — Reroute (`operator_reroute_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 8 Block.
- **Visual brief**: A cable junction panel bending current into a new path.
- **Composition note**: Readable block/arrow silhouette over flashy effects.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### OPR015 — Static Haze (`operator_static_haze_01`)

- **Type / cost / gameplay**: skill / 1 — Apply 2 Weak. Draw 1 card.
- **Visual brief**: A fog of screen snow and teal static arcs clouding the target’s output.
- **Composition note**: The weak effect should feel electronic, not mystical.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### OPR016 — Zero-Day Burst (`operator_zero_day_burst_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 2 damage 3 times. Modify the next card cost by -1.
- **Visual brief**: A burst of exploit shards or digital bugs striking three times in sequence.
- **Composition note**: Three crisp beats of impact and teal fragments.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

## Shared / starter / status card sheet

- **Palette guide**: Use neutral steel, muted amber, off-white, and small cyan accents. Shared cards should feel universal, modular, and less faction-specific.
- **Recommended sheet label**: `shr_card_sheet_reference`
- **Slot count**: 12

### SHR000 — Burn (`status_burn_01`)

- **Type / cost / gameplay**: status / 0 — `on_draw` -> Lose 2 HP.
- **Visual brief**: A burning warning chit or ember-eaten scrap ticket with a small orange glow.
- **Composition note**: Keep status cards simpler and more symbolic than normal cards.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes
- **Keyword emphasis**: `combat_only`, `exhaust`

### SHR001 — Cache Draw (`cache_draw_01`)

- **Type / cost / gameplay**: skill / 1 — Draw 2 cards.
- **Visual brief**: A generic data cache chip stack or magazine of blank cards.
- **Composition note**: Utility icon with readable shape.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### SHR002 — Defend (`defend_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 5 Block.
- **Visual brief**: A simple compact shield module or forearm plate.
- **Composition note**: Starter cards should be plain and universal.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### SHR003 — Firewall (`firewall_01`)

- **Type / cost / gameplay**: skill / 1 — Gain 8 Block.
- **Visual brief**: A reinforced thermal shield wall or burning security barrier.
- **Composition note**: One barricade silhouette with contained flame.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions

### SHR004 — Glitch (`status_glitch_01`)

- **Type / cost / gameplay**: status / 0 — `on_draw` -> Random one of: Glitch drains power. | Glitch bites back.
- **Visual brief**: A broken display mask or error face with scrambled pixels and torn scanlines.
- **Composition note**: Status card art should feel like a hazard ticket, not a full scene.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions
- **Keyword emphasis**: `combat_only`, `exhaust`

### SHR005 — Junk (`status_junk_01`)

- **Type / cost / gameplay**: status / 0 — No direct effect.
- **Visual brief**: A pile of bolts, broken chips, bent plates, and useless machine trash.
- **Composition note**: Simple pile silhouette, easy to read.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery
- **Keyword emphasis**: `combat_only`

### SHR006 — Lag (`status_lag_01`)

- **Type / cost / gameplay**: status / 0 — `on_draw` -> Modify the next card cost by 1.
- **Visual brief**: A buffering ring or progress bar frozen mid-load with drag arrows.
- **Composition note**: Abstract UI hazard imagery is fine here.
- **Theme lens**: `signal_mesh` — cleaner support/control look; scanners, grids, shields, data mesh, and calmer compositions
- **Keyword emphasis**: `combat_only`, `exhaust`

### SHR007 — Overclock (`overclock_01`)

- **Type / cost / gameplay**: skill / 0 — Gain 1 Energy. Draw 1 card.
- **Visual brief**: A compact booster chip or battery tap flaring blue-white.
- **Composition note**: Shared tech power-up; no class bias.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes
- **Keyword emphasis**: `exhaust`

### SHR008 — Patch Kit (`patch_kit_01`)

- **Type / cost / gameplay**: skill / 1 — Heal 4 HP. Cleanse 1 `burn`. Cleanse 1 `bleed`. Cleanse 1 `infect`. Remove Nullified.
- **Visual brief**: A med-and-repair kit with cleanser spray, bandage tape, and neutral serum ampoules.
- **Composition note**: Utility item shot, not a character scene.
- **Theme lens**: `patch_grid` — rougher patched look; stitched tech, scavenged hardware, self-damage, organs, or improvised machinery

### SHR009 — Strike (`strike_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 6 damage.
- **Visual brief**: A clean generic strike: blade edge, baton hit, or muzzle impact with no class bias.
- **Composition note**: The most neutral attack art in the set.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### SHR010 — Surge Strike (`surge_strike_01`)

- **Type / cost / gameplay**: attack / 2 — Deal 12 damage.
- **Visual brief**: A harder-hitting charged strike wrapped in blue electrical force.
- **Composition note**: Shared offense, larger and brighter than Strike.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

### SHR011 — Volley (`volley_01`)

- **Type / cost / gameplay**: attack / 1 — Deal 8 damage.
- **Visual brief**: A quick burst of multiple rounds or repeated muzzle flashes.
- **Composition note**: Three short beats, neutral tech palette.
- **Theme lens**: `circuit_burst` — high-energy attack look; brighter motion arcs, weapon discharge, clearer impact silhouettes

## 5. Image-generation prompt templates

These are the **sheet-level prompts** to use with an image generator after the atlas layout is finalized. They are intentionally phrased for clean, slot-based output and easy Codex slicing.

### Relic atlas prompt

Create a relic sprite sheet reference atlas for a cyberpunk roguelike deckbuilder.

Style goals:
- simple readable relic icons in the gameplay-friendly spirit of Slay the Spire relic art, but with wholly original cyberpunk designs
- dark navy presentation sheet
- cutout-friendly single-object icons
- minimal ambient FX only
- no scene backgrounds behind the relics
- no giant halos or complex splash art

Layout goals:
- preserve the existing 220x220 slot windows and overall reference-sheet presentation
- 5 columns
- centered relic icons
- each slot should feel easy for Codex to crop out
- slot metadata may live outside the relic icon, but the icon itself should contain no text

Relic order:
000 Carbon Weave
001 Flash Cache
002 Plated Grip
003 Shard Seed
004 Surge Fuse
005 Signal Router
006 Clean Slate
007 Market Key
008 Overclock Relay
009 Butcher Hooks
010 Field Dampener
011 Rot Battery
012 Execution Array
013 Grave Lantern
014 Grave Pick
015 Jam Cycler
016 Null Damper
017 Pressure Sight
018 Septic Reservoir

### Bio-Hacker card sheet prompt

Create a bio-hacker card sheet reference sheet for a cyberpunk roguelike deckbuilder.

Style goals:
- card illustration panels with the gameplay readability of Slay the Spire card art, but with original cyberpunk bio hacker designs
- one strong focal subject per slot
- minimal background clutter
- no card frame, no rules text, no cost gems, no rarity pips, no logos
- the sheet is for Codex slicing, so keep every slot clean, centered, and readable

Visual language:
- Use toxic verdant greens, bruised flesh tones, amber serum glass, and oily black hardware. Organic biotech forms should feel invasive but readable.
- use the owner's internal micro-styles where relevant: signal_mesh for cleaner support/control panels, patch_grid for rougher improvised panels, circuit_burst for brighter attack panels

Layout goals:
- dark navy reference sheet
- 5-column grid
- consistent rectangular art windows
- each slot should contain only the art crop
- slot labels can live outside the crop if needed

Card order:
000 Blood Buffer
001 Coagulate
002 Harvest Bite
003 Hemorrhage
004 Leech Jab
005 Pain Circuit
006 Pain Probe
007 Parasite Fang
008 Reclaimer
009 Rot Harvest
010 Rot Slash
011 Scar Tissue
012 Septic Round
013 Spare Organs
014 Symbiote Mesh
015 Triage Loop
016 Waste Recycler

### Enforcer card sheet prompt

Create a enforcer card sheet reference sheet for a cyberpunk roguelike deckbuilder.

Style goals:
- card illustration panels with the gameplay readability of Slay the Spire card art, but with original cyberpunk enforcer designs
- one strong focal subject per slot
- minimal background clutter
- no card frame, no rules text, no cost gems, no rarity pips, no logos
- the sheet is for Codex slicing, so keep every slot clean, centered, and readable

Visual language:
- Use crimson, rust, warning amber, soot black, and battered steel. Shapes should be blunt, heavy, and riot-gear adjacent.
- use the owner's internal micro-styles where relevant: signal_mesh for cleaner support/control panels, patch_grid for rougher improvised panels, circuit_burst for brighter attack panels

Layout goals:
- dark navy reference sheet
- 5-column grid
- consistent rectangular art windows
- each slot should contain only the art crop
- slot labels can live outside the crop if needed

Card order:
000 Bash Protocol
001 Battle Roar
002 Blood Rush
003 Breaker Line
004 Chain Assault
005 Crackdown
006 Double Tap
007 Feed Aggression
008 Gouge
009 Guard Stance
010 Hard Commit
011 Open Wound
012 Ram Guard
013 Redline Core
014 Riot Barrage
015 Spiked Harness
016 War Engine

### Operator card sheet prompt

Create a operator card sheet reference sheet for a cyberpunk roguelike deckbuilder.

Style goals:
- card illustration panels with the gameplay readability of Slay the Spire card art, but with original cyberpunk operator designs
- one strong focal subject per slot
- minimal background clutter
- no card frame, no rules text, no cost gems, no rarity pips, no logos
- the sheet is for Codex slicing, so keep every slot clean, centered, and readable

Visual language:
- Use cool teal, cyan, slate navy, white UI glow, and sparse electric blue accents. Shapes should feel sleek, precise, and high-control.
- use the owner's internal micro-styles where relevant: signal_mesh for cleaner support/control panels, patch_grid for rougher improvised panels, circuit_burst for brighter attack panels

Layout goals:
- dark navy reference sheet
- 5-column grid
- consistent rectangular art windows
- each slot should contain only the art crop
- slot labels can live outside the crop if needed

Card order:
000 Auto-Tuner
001 Backdoor
002 Cache Cycle
003 Cold Read
004 Control Tower
005 Deep Cache
006 Deflect Mesh
007 Lock In
008 Needle Ping
009 Packet Storm
010 Priority Queue
011 Quiet Cut
012 Recompile Shot
013 Relay Shot
014 Reroute
015 Static Haze
016 Zero-Day Burst

### Shared / starter / status card sheet prompt

Create a shared / starter / status card sheet reference sheet for a cyberpunk roguelike deckbuilder.

Style goals:
- card illustration panels with the gameplay readability of Slay the Spire card art, but with original cyberpunk shared designs
- one strong focal subject per slot
- minimal background clutter
- no card frame, no rules text, no cost gems, no rarity pips, no logos
- the sheet is for Codex slicing, so keep every slot clean, centered, and readable

Visual language:
- Use neutral steel, muted amber, off-white, and small cyan accents. Shared cards should feel universal, modular, and less faction-specific.
- use the owner's internal micro-styles where relevant: signal_mesh for cleaner support/control panels, patch_grid for rougher improvised panels, circuit_burst for brighter attack panels

Layout goals:
- dark navy reference sheet
- 5-column grid
- consistent rectangular art windows
- each slot should contain only the art crop
- slot labels can live outside the crop if needed

Card order:
000 Burn
001 Cache Draw
002 Defend
003 Firewall
004 Glitch
005 Junk
006 Lag
007 Overclock
008 Patch Kit
009 Strike
010 Surge Strike
011 Volley

## 6. Practical do / do-not list

### Do

- Use one iconic subject per relic.
- Use one strong subject or very tight action vignette per card.
- Keep silhouettes readable at small size.
- Leave enough negative space around the focal subject so the art still reads when cropped into a card window.
- Let faction palette and status language do more work than extra detail.

### Do not

- Do not render finished card frames or in-game UI around the art.
- Do not hide the subject inside a busy environment scene.
- Do not add text inside the art crops.
- Do not wrap relics in large effect auras that will fight the separate in-game FX.
- Do not make different cards feel like they belong to different games; keep the whole set cohesive.

## 7. Recommended production order

1. Finalize the **atlas manifests** (`rogue_card_sheet_manifest.json` and `rogue_relic_sheet_manifest.json`).
2. Generate the **relic atlas expansion** first, because the current sheet already provides a proven slicing pattern.
3. Generate the **Bio-Hacker**, **Enforcer**, and **Operator** card sheets next, one sheet per owner.
4. Generate the **Shared / starter / status** sheet last.
5. Use Codex to slice by the manifest coordinates and connect the resulting images to card / relic IDs.