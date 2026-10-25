import os

STRATEGIES = [s.strip() for s in os.getenv("STRATEGIES", "recursive").split(",") if s.strip()]
DEFAULT_STRATEGY = os.getenv("DEFAULT_STRATEGY", STRATEGIES[0])
API_KEY = os.getenv("API_KEY", "")            # empty = no auth (local dev only)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
SEED_DIR = os.getenv("SEED_DIR", "seed_corpus")
INBOX = "data/inbox"