import json
import time
import logging
import os
from datetime import datetime
from pymongo import MongoClient, errors

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"import_to_mongo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

client = MongoClient('mongodb://localhost:27017/')
db = client['steam_db']
collection = db['raw_games']

collection.drop()
logger.info("Dropped existing collection 'raw_games'")

bulk_size = 10000
batch = []
start = time.time()

start = time.time()

def insert_batch(batch):
    if batch:
        try:
            collection.insert_many(batch, ordered=False)
            logger.info(f"Inserted {len(batch)} documents")
        except errors.BulkWriteError as e:
            logger.error(f"Bulk write error: {e.details}")
        return []

logger.info("Reading JSON file...")
with open('data/raw/steam_games.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    total = len(data)  
    logger.info(f"Total games in JSON: {total}")
    
    for app_id, game_info in data.items():
        doc = game_info.copy()
        doc['_id'] = app_id  
        batch.append(doc)
        if len(batch) >= bulk_size:
            batch = insert_batch(batch)
    
    if batch:
        insert_batch(batch)

elapsed = time.time() - start
final_count = collection.count_documents({})
logger.info(f"Done in {elapsed:.2f}s. Total documents in MongoDB: {final_count}")