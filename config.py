
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

except FileNotFoundError:
    raise RuntimeError(f"Config file not found: {CONFIG_PATH}")

except json.JSONDecodeError as e:
    raise RuntimeError(f"Invalid config JSON: {e}")