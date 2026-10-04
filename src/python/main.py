import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import metadata.metadata_parser as metadata_module
import indexer.indexer as indexer_module
from crawler_controller import CrawlerController
from control_layer import ControlLayer

def main():
    print("=== Starting Book Processing Pipeline ===")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    datalake_path = os.path.join(base_dir, "datalake")
    logs_path = os.path.join(base_dir, "control")
    
    os.makedirs(datalake_path, exist_ok=True)
    os.makedirs(logs_path, exist_ok=True)
    
    crawler = CrawlerController(datalake_path=datalake_path, logs_path=logs_path)
    
    if hasattr(metadata_module, 'MetadataParser'):
        metadata_service = metadata_module.MetadataParser()
    elif hasattr(metadata_module, 'MetadataService'):
        metadata_service = metadata_module.MetadataService()
    else:
        metadata_service = metadata_module
    
    if hasattr(indexer_module, 'Indexer'):
        indexer_service = indexer_module.Indexer()
    elif hasattr(indexer_module, 'IndexerService'):
        indexer_service = indexer_module.IndexerService()
    else:
        indexer_service = indexer_module

    control = ControlLayer(crawler, metadata_service, indexer_service)
    
    target_books = range(6, 31)
    
    for b_id in target_books:
        print(f"\n--- Processing Book ID: {b_id} ---")
        control.process_book(b_id)

    print("\n=== Processing completed ===")

if __name__ == "__main__":
    main()