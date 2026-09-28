import sys
from pathlib import Path
from crawler_controller import CrawlerController

if __name__ == "__main__":
    # Si no se pasan argumentos por consola, asigna las rutas estándar del proyecto
    datalake_path = sys.argv[1] if len(sys.argv) > 1 else "../../datalake"
    logs_output_path = sys.argv[2] if len(sys.argv) > 2 else "../../control"
    
    # Cantidad de libros a descargar en esta prueba (ej. 5 libros)
    books_to_process = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print("--- Starting the Crawler / Data Lake Ingestion ---")
    crawler = CrawlerController(
        datalake_path=datalake_path, 
        logs_path=logs_output_path, 
        total_books=100, 
        datalake_structure="date"
    )
    crawler.download(books_to_process)