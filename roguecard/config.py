from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = PROJECT_ROOT / "assets"
DATA_ROOT = PROJECT_ROOT / "data"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
FRAME_RATE = 60

GAME_VERSION = "0.1.0"
CARD_SCHEMA_VERSION = 1
ENEMY_SCHEMA_VERSION = 1
SAVE_FORMAT_VERSION = 1

MAX_HAND_SIZE = 10
PLAYER_STARTING_HP = 70
PLAYER_STARTING_ENERGY = 3
PLAYER_STARTING_DRAW = 5

DEFAULT_ENEMY_ATTACK_DAMAGE = 6
DEFAULT_ENEMY_DEFEND_BLOCK = 5

MAP_FLOORS = 6
MAP_BRANCHES = 3

CARDS_DATA_PATH = DATA_ROOT / "cards.json"
ENEMIES_DATA_PATH = DATA_ROOT / "enemies.json"

STARTER_DECK_IDS = (
    "strike_01",
    "strike_01",
    "strike_01",
    "strike_01",
    "strike_01",
    "defend_01",
    "defend_01",
    "defend_01",
    "defend_01",
    "defend_01",
)

ENCOUNTER_ENEMY_IDS = {
    "combat": "enemy_basic_01",
    "elite": "enemy_elite_01",
    "boss": "enemy_boss_01",
}


def resolve_asset_path(*parts: str) -> Path:
    return ASSETS_ROOT.joinpath(*parts)
