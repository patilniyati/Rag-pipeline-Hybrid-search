from . import config, service
from .state import rag

if __name__ == "__main__":
    service.wait_for_chroma()
    print(rag.ingest(config.SEED_DIR))