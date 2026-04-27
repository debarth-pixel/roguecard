# Protocol Drift Catalog Note

Generated as part of the full event expansion pass.

- Run state: Protocol Drift lives in `run_state.protocol_drift_pct` from `0` to `100`; `protocol_drift_seen` is set once Drift becomes visible, and `queued_next_combat_effects` stores one-shot combat payloads from events.
- Supported event mechanics: live events use credits, HP damage/heal, card gain, fixed card removal, purge targeting, run modifier gain/remove/refresh, Protocol Drift adjustment, random modifier gain, and queued next-combat effects.
- Queued next-combat effects: supported payloads are turn-one Energy, draw, Block, player combat status, status-card insertion, and temporary card to hand.
- Hidden cards: current event sources are `signal_busker_01` -> `drift_mirror_cache_01`, `blackwire_broker_01` -> `drift_null_refund_01`, `bone_receipt_window_01` -> `drift_error_knife_01`, `protocol_patch_bay_01` -> `drift_unsafe_overclock_01`, and `protocol_eclipse_01` -> `drift_black_ice_bloom_01`.
- Corruption riders: hidden corruption text remains gated by Protocol Drift visibility and rider thresholds on cards; event previews show Drift deltas and queued next-combat chips before confirmation.
- Character-specific events: each character owns 10 events through event-level `character_ids`; universal events omit that field.
- Signature events: before normal weighted selection, the first eligible event node offers `riot_drill_square_01` for Enforcer, `cheap_implant_rack_01` for Operator, or `infection_gallery_01` for Bio-Hacker. Existing `event_history` prevents repeats.
- Draft adaptations: event flags, OR chain requirements, next-shop state, next-reward state, max-HP loss, and random deck loss were converted into supported immediate effects, fixed gates, fixed card edits, or queued next-combat effects.
