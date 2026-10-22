import re
from pathlib import Path

def index_to_mongodb(corpus_dir: Path, db_name="search_engine", collection_name="inverted_index"):
    try:
        from pymongo import MongoClient
    except ImportError:
        print("[!] pymongo no instalado. Ejecuta: pip install pymongo")
        return None

    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    try:
        client.server_info()
    except Exception:
        print("[!] Servidor MongoDB no disponible localmente. Se documentará como arquitectura opcional.")
        return None

    db = client[db_name]
    col = db[collection_name]
    col.drop()
    
    index_map = {}
    for body_file in corpus_dir.glob("*_body.txt"):
        book_id = int(body_file.name.split("_")[0])
        text = body_file.read_text(encoding="utf-8", errors="ignore").lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", text))
        for w in words:
            if w not in index_map:
                index_map[w] = []
            index_map[w].append(book_id)

    docs = [{"term": term, "postings": postings} for term, postings in index_map.items()]
    if docs:
        col.insert_many(docs)
        col.create_index("term")
    return len(docs)