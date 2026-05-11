import lancedb
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    db_uri = os.getenv("LANCEDB_URI", "./.lancedb")
    return lancedb.connect(db_uri)
