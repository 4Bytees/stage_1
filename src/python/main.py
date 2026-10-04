import sys
import os

# Añadir la carpeta raíz de Python al sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import metadata.metadata_parser as metadata_module
import indexer.indexer as indexer_module
from crawler_controller import CrawlerController
from control_layer import ControlLayer

def main():
    print("=== Iniciando Pipeline de Procesamiento de Libros ===")
    
    # Definir rutas base para Datalake y Logs/Control
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    datalake_path = os.path.join(base_dir, "datalake")
    logs_path = os.path.join(base_dir, "control")
    
    os.makedirs(datalake_path, exist_ok=True)
    os.makedirs(logs_path, exist_ok=True)
    
    # Instanciar el Crawler pasando los dos argumentos requeridos
    crawler = CrawlerController(datalake_path=datalake_path, logs_path=logs_path)
    
    # Instanciar o referenciar el módulo de metadatos
    if hasattr(metadata_module, 'MetadataParser'):
        metadata_service = metadata_module.MetadataParser()
    elif hasattr(metadata_module, 'MetadataService'):
        metadata_service = metadata_module.MetadataService()
    else:
        metadata_service = metadata_module
    
    # Instanciar o referenciar el módulo de indexación
    if hasattr(indexer_module, 'Indexer'):
        indexer_service = indexer_module.Indexer()
    elif hasattr(indexer_module, 'IndexerService'):
        indexer_service = indexer_module.IndexerService()
    else:
        indexer_service = indexer_module

    # Instanciar la capa de control
    control = ControlLayer(crawler, metadata_service, indexer_service)
    
    # Procesar libros de prueba (del 6 al 30)
    target_books = range(6, 31)
    
    for b_id in target_books:
        print(f"\n--- Procesando Libro ID: {b_id} ---")
        control.process_book(b_id)

    print("\n=== Procesamiento completado ===")

if __name__ == "__main__":
    main()