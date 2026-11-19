import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_veritas.db")
os.environ.setdefault("MODEL_HF_ID", "hamzab/roberta-fake-news-classification")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.database.database import Base, engine

    Base.metadata.create_all(bind=engine)
    app = create_app()
    with TestClient(app) as c:
        yield c
    # cleanup test db (ignore if still locked by sqlite)
    import os
    db_path = Path("test_veritas.db")
    try:
        if db_path.exists():
            db_path.unlink()
    except OSError:
        pass
