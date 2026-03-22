#!/usr/bin/env python3
"""
Script per generare un documento Word utilizzando l'API di CloudConvert.
Questo approccio garantisce una conversione Markdown di alta qualità,
specialmente per elementi complessi come le liste annidate.
"""

import os
import sys
import time
import requests
import re
from pathlib import Path
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# --- CONFIGURAZIONE ---
# La chiave API viene letta dal file .env
API_KEY = os.environ.get("CLOUDCONVERT_API_KEY")
BASE_DIR = Path("Relazione_4808")
OUTPUT_FILENAME = "Relazione_4808_CloudConvert.docx"
COMBINED_MD_FILENAME = "relazione_completa.md"

def check_dependencies():
    """Verifica che i moduli necessari siano installati."""
    try:
        import requests
        from dotenv import load_dotenv
    except ImportError:
        print("❌ Errore: Mancano delle dipendenze (requests, python-dotenv)!")
        print("\n📦 Per installarle, esegui:")
        print("   pip install requests python-dotenv")
        print("\n🔄 Poi rilancia questo script.")
        sys.exit(1)

def combine_markdown_files():
    """
    Combina tutti i file Markdown della relazione in un unico file.
    Questo è necessario per caricarli come un singolo input a CloudConvert.
    """
    print("1. Unisco tutti i file Markdown in un unico documento...")
    
    # Lista dei file delle sezioni principali in ordine
    main_sections = [
        "01_Informazioni_Generali.md", "02_Considerazioni_Iniziali.md",
        "03_Informazioni_Pratiche.md", "04_Piano_Voli.md", "05_Trasporti.md",
        "06_Pernottamenti.md", "07_Costi_e_Cassa.md", "08_Escursioni_e_Attivita.md",
        "09_Itinerario_di_Massima.md"
    ]
    
    # Itinerario giornaliero
    itinerario_dir = BASE_DIR / "Itinerario_Giornaliero"
    day_files = sorted([f for f in itinerario_dir.glob("Giorno_*.md")]) if itinerario_dir.exists() else []
    
    # Manuale operativo
    manual_file = BASE_DIR / "MANUALE_OPERATIVO_COORDINATORE.md"
    
    all_files = [BASE_DIR / f for f in main_sections] + day_files
    if manual_file.exists():
        all_files.append(manual_file)

    with open(COMBINED_MD_FILENAME, 'w', encoding='utf-8') as outfile:
        for i, file_path in enumerate(all_files):
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    
                    # 1. Gestisce i titoli preceduti da '---' (es. --- ### Titolo)
                    #    sostituendoli con un separatore e un titolo su righe separate.
                    content = re.sub(r'^\s*---\s*(#+.*)', r'\n***\n\n\1', content, flags=re.MULTILINE)
                    
                    # 2. Converte tutte le altre linee '---' in separatori orizzontali '***'
                    #    per evitare problemi di parsing YAML con Pandoc.
                    content = re.sub(r'^\s*---\s*$', '***', content, flags=re.MULTILINE)
                    
                    outfile.write(content)
                    
                    # 3. Aggiunge un'interruzione di pagina dopo ogni file, eccetto l'ultimo.
                    #    Utilizza un blocco raw OpenXML, il metodo più robusto per forzare
                    #    un'interruzione di pagina in DOCX tramite Pandoc.
                    if i < len(all_files) - 1:
                        page_break_code = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'
                        outfile.write(f'\n\n{page_break_code}\n\n')

                print(f"   - Aggiunto: {file_path.name}")
            else:
                print(f"   - ATTENZIONE: {file_path.name} non trovato!")
    
    print(f"✅ File combinato creato: {COMBINED_MD_FILENAME}\n")
    return COMBINED_MD_FILENAME

def wait_for_job(job_id):
    """Attende il completamento di un job di CloudConvert."""
    while True:
        url = f"https://api.cloudconvert.com/v2/jobs/{job_id}"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(url, headers=headers).json()
        
        status = response['data']['status']
        if status == 'finished':
            print("   - Job completato.")
            return response
        elif status == 'error':
            print(f"❌ Errore nel job: {response['data'].get('message', 'Nessun dettaglio')}")
            sys.exit(1)
        
        print(f"   - Stato del job: {status}... attendo...")
        time.sleep(3)

def main():
    """Funzione principale per orchestrare la conversione."""
    check_dependencies()

    if not API_KEY or API_KEY == "LA_TUA_CHIAVE_API_QUI":
        print("❌ Errore: La chiave API di CloudConvert non è stata impostata nel file .env.")
        print("   Apri il file '.env' e sostituisci 'LA_TUA_CHIAVE_API_QUI' con la tua chiave reale.")
        sys.exit(1)

    if not BASE_DIR.exists():
        print(f"Errore: La cartella '{BASE_DIR}' non esiste!")
        sys.exit(1)

    combined_file = combine_markdown_files()

    # --- FASE 2: Processo con CloudConvert ---
    print("2. Avvio del processo di conversione con CloudConvert...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-type": "application/json"
    }
    
    # 2.1. Crea il job principale e definisci i task
    payload = {
        "tasks": {
            "import-file": {
                "operation": "import/upload"
            },
            "convert-file": {
                "operation": "convert",
                "input": "import-file",
                "input_format": "md",
                "output_format": "docx",
                "engine": "pandoc", # Usa Pandoc per una migliore gestione del Markdown
            },
            "export-file": {
                "operation": "export/url",
                "input": "convert-file",
                "inline": False,
                "archive_multiple_files": False
            }
        }
    }
    
    response = requests.post("https://api.cloudconvert.com/v2/jobs", headers=headers, json=payload).json()
    job_id = response['data']['id']
    upload_task_id = response['data']['tasks'][0]['id']
    upload_url = response['data']['tasks'][0]['result']['form']['url']
    upload_params = response['data']['tasks'][0]['result']['form']['parameters']
    
    print(f"   - Job creato con ID: {job_id}")

    # 2.2. Carica il file
    print("   - Caricamento del file combinato...")
    with open(combined_file, 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, data=upload_params, files=files)
    
    if upload_response.status_code != 201:
        print(f"❌ Errore durante il caricamento del file: {upload_response.text}")
        sys.exit(1)
    print("   - File caricato con successo.")

    # 2.3. Attendi il completamento del job
    print("   - In attesa del completamento della conversione...")
    job_data = wait_for_job(job_id)
    
    # 2.4. Ottieni il link per il download
    export_task = next(t for t in job_data['data']['tasks'] if t['operation'] == 'export/url')
    download_url = export_task['result']['files'][0]['url']
    
    print("\n3. Scaricamento del file convertito...")
    downloaded_file = requests.get(download_url)
    
    with open(OUTPUT_FILENAME, 'wb') as f:
        f.write(downloaded_file.content)
        
    print(f"✅ Documento Word creato con successo: {OUTPUT_FILENAME}")
    
    # Pulizia del file temporaneo
    os.remove(combined_file)
    print(f"   - File temporaneo '{combined_file}' rimosso.")

if __name__ == "__main__":
    main()
