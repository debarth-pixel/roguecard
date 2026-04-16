from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = PROJECT_ROOT / "assets"
DATA_ROOT = PROJECT_ROOT / "data"
SPRITE_REFERENCE_PACK_ROOT = PROJECT_ROOT / "sprite_sheet_reference_pack"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
FRAME_RATE = 60
FAST_MODE_MULTIPLIER = 1.75
NOTICE_DURATION_SECONDS = 2.4
HELP_PANEL_WIDTH = 820
HELP_PANEL_HEIGHT = 500
SETTINGS_PANEL_WIDTH = 980
SETTINGS_PANEL_HEIGHT = 610
SETTINGS_TAB_WIDTH = 158
SETTINGS_TAB_HEIGHT = 34
ACTION_COOLDOWN_SECONDS = 0.12
DEFAULT_FULLSCREEN = True
DEFAULT_FAST_MODE = False
DEFAULT_SHOW_HELP = False
DEFAULT_MASTER_VOLUME = 0.8
DEFAULT_MUSIC_VOLUME = 0.65
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0
VOLUME_STEP = 0.1
DEFAULT_PRESENTATION_SCALE = 1.0
MIN_PRESENTATION_SCALE = 0.8
MAX_PRESENTATION_SCALE = 1.0
PRESENTATION_SCALE_STEP = 0.05
DEFAULT_UI_SCALE = 1.0
MIN_UI_SCALE = 0.9
MAX_UI_SCALE = 1.25
UI_SCALE_STEP = 0.1
DEFAULT_SCREEN_SHAKE = True
DEFAULT_HIGH_CONTRAST = False
SETTINGS_FORMAT_VERSION = 1
MAP_NODE_RADIUS = 48
MAP_NODE_HIT_RADIUS = 58
CARD_HOVER_LIFT = 18
PAUSE_BUTTON_WIDTH = 118
PAUSE_BUTTON_HEIGHT = 40
MODIFIER_ICON_SIZE = 46
MODIFIER_ICON_GAP = 10
MODIFIER_TOOLTIP_WIDTH = 270
STATUS_ICON_SIZE = 30
STATUS_ICON_GAP = 8
STATUS_TOOLTIP_WIDTH = 300

GAME_VERSION = "0.1.0"
CARD_SCHEMA_VERSION = 2
CHARACTER_SCHEMA_VERSION = 1
CAMPAIGN_SCHEMA_VERSION = 1
ENEMY_SCHEMA_VERSION = 2
EVENT_SCHEMA_VERSION = 1
RUN_MODIFIER_SCHEMA_VERSION = 1
SAVE_FORMAT_VERSION = 12

MAX_HAND_SIZE = 10
PLAYER_STARTING_HP = 70
PLAYER_STARTING_ENERGY = 3
PLAYER_STARTING_DRAW = 5
PLAYER_STARTING_CREDITS = 0

DEFAULT_ENEMY_ATTACK_DAMAGE = 6
DEFAULT_ENEMY_DEFEND_BLOCK = 5

MAP_FLOOR_COUNT = 15
MAP_TOTAL_ROWS = MAP_FLOOR_COUNT + 1
MAP_BRANCHES = 3
BOSS_CHECKPOINT_HEAL = 12
BOSS_REWARD_CARD_CHOICE_COUNT = 4
BARK_GENERIC_DURATION_SECONDS = 2.2
BARK_BOSS_DURATION_SECONDS = 3.2
BARK_COOLDOWN_ACTIONS = 2
BARK_MAX_GENERIC_PER_SPEAKER = 2
BARK_MAX_BOSS_PER_SPEAKER = 5

CARDS_DATA_PATH = DATA_ROOT / "cards.json"
CHARACTERS_DATA_PATH = DATA_ROOT / "characters.json"
CAMPAIGN_MAPS_DATA_PATH = DATA_ROOT / "campaign_maps.json"
ENEMIES_DATA_PATH = DATA_ROOT / "enemies.json"
EVENTS_DATA_PATH = DATA_ROOT / "events.json"
RUN_MODIFIERS_DATA_PATH = DATA_ROOT / "run_modifiers.json"
SETTINGS_DATA_PATH = DATA_ROOT / "settings.json"
RUN_SAVE_DATA_PATH = DATA_ROOT / "run_save.json"
GRAYSPINE_LORE_DATA_PATH = DATA_ROOT / "grayspine_lore.json"
FINAL_MAP_BOSSES_DATA_PATH = DATA_ROOT / "final_map_bosses.json"
FINAL_MAP_ENCOUNTERS_DATA_PATH = DATA_ROOT / "final_map_encounters.json"
FINAL_MAP_BARKS_DATA_PATH = DATA_ROOT / "final_map_barks.json"
CARD_ART_ATLAS_PATH = SPRITE_REFERENCE_PACK_ROOT / "card_art_atlas.png"
CARD_ART_ATLAS_COORDINATES_PATH = SPRITE_REFERENCE_PACK_ROOT / "card_art_atlas_coordinates.csv"
RELIC_SPRITE_SHEET_PATH = SPRITE_REFERENCE_PACK_ROOT / "relic_sprite_sheet_reference.png"
RELIC_SPRITE_COORDINATES_PATH = SPRITE_REFERENCE_PACK_ROOT / "relic_sprite_coordinates.csv"
RELIC_CUTOUTS_ROOT = ASSETS_ROOT / "ui" / "relics"

ENCOUNTER_ENEMY_IDS = {
    "combat": "enemy_basic_01",
    "elite": "enemy_elite_01",
    "boss": "enemy_boss_01",
}

REWARD_CARD_CHOICE_COUNT = 3
SHOP_CARD_OFFER_COUNT = 3
REGULAR_COMBAT_CREDIT_REWARD = 20
ELITE_COMBAT_CREDIT_REWARD = 40
REGULAR_REWARD_CHANCE = 0.5
REGULAR_REWARD_CARD_WEIGHT = 7
REGULAR_REWARD_PURGE_WEIGHT = 3
MIN_STARTING_DECK_SIZE = 1
SHOP_HEAL_ENABLED = True
SHOP_HEAL_OFFER_ID = "heal_service"
SHOP_HEAL_PRICE = 18
SHOP_HEAL_AMOUNT = 14
SHOP_PURGE_OFFER_ID = "purge_service"
SHOP_PURGE_PRICE = 40
SHOP_REROLL_BASE_PRICE = 12
SHOP_REROLL_PRICE_STEP = 8
EVENT_RARITY_WEIGHTS = {
    "common": 1.0,
    "uncommon": 0.55,
    "rare": 0.22,
    "special": 0.0,
}
STATUS_RARITY_WEIGHTS = {
    "positive": {
        "common": 1.0,
        "uncommon": 0.5,
        "rare": 0.18,
        "cursed": 0.0,
        "special": 0.0,
    },
    "risky": {
        "common": 0.85,
        "uncommon": 0.55,
        "rare": 0.22,
        "cursed": 0.35,
        "special": 0.0,
    },
}
EVENT_RECENTLY_SEEN_PENALTY = 0.2
EVENT_SAME_TAG_REPEAT_PENALTY = 0.45
EARLY_MID_LATE_RUN_WEIGHT_MODIFIERS = {
    "early": {
        "common": 1.15,
        "uncommon": 0.9,
        "rare": 0.6,
        "special": 0.0,
    },
    "mid": {
        "common": 1.0,
        "uncommon": 1.0,
        "rare": 1.0,
        "special": 1.0,
    },
    "late": {
        "common": 0.9,
        "uncommon": 1.0,
        "rare": 1.25,
        "special": 1.0,
    },
}
MAX_SEEN_EVENT_MEMORY = 4
STATUS_DUPLICATE_RULES = {
    "no_duplicate": "Ignore duplicate rolls and reroll within the same weighted pool.",
    "refresh_duration": "Refresh the duration on the active entry instead of adding a duplicate.",
    "stack_intensity": "Increase a modifier intensity multiplier on the existing record.",
    "stack_count": "Increase a stack counter and repeat safe numeric effects per stack.",
}
EVENT_TAGS = (
    "economy",
    "recovery",
    "status_gain",
    "status_risk",
    "deck_edit",
    "gamble",
    "upgrade",
    "curse",
    "blessing",
    "combat_prep",
    "merchant_style",
    "anomaly",
    "narrative",
)
STATUS_TAGS = (
    "economy",
    "offense",
    "defense",
    "energy",
    "draw",
    "risk",
    "recovery",
    "scaling",
    "volatility",
    "shop",
    "event",
    "curse",
    "blessing",
)
STATUS_SOURCE_TYPES = (
    "event",
    "relic",
    "run_start",
    "shop",
    "combat_reward",
    "boss_reward",
)
FINAL_MAP_FACTION_IDS = (
    "helix_ward",
    "blackwire_directorate",
    "cinder_jackals",
)

FINAL_MAP_ROUTE_IDS = {
    "helix_ward": "helix_ward_depths",
    "blackwire_directorate": "blackwire_lockdown_sector",
    "cinder_jackals": "cinder_jackals_edgeworks",
}
def resolve_asset_path(*parts: str) -> Path:
    return ASSETS_ROOT.joinpath(*parts)
