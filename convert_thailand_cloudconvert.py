#!/usr/bin/env python3
"""
Script per generare un documento Word utilizzando l'API di CloudConvert per l'itinerario in Thailandia.
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
API_KEY = os.environ.get("CLOUDCONVERT_API_KEY")
BASE_DIR = Path("Itinerary")
OUTPUT_FILENAME = "Itinerario_Thailandia_2026_CloudConvert.docx"
COMBINED_MD_FILENAME = "itinerario_completo.md"

def check_dependencies():
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
    print("1. Unisco tutti i file Markdown in un unico documento...")
    
    # Prendi tutti i file md nella cartella Itinerary, ordinati per nome
    if not BASE_DIR.exists():
        print(f"Errore: La cartella '{BASE_DIR}' non esiste!")
        sys.exit(1)

    all_files = sorted(list(BASE_DIR.glob("*.md")))
    if not all_files:
        print(f"Errore: Nessun file markdown trovato in '{BASE_DIR}'!")
        sys.exit(1)

    with open(COMBINED_MD_FILENAME, 'w', encoding='utf-8') as outfile:
        for i, file_path in enumerate(all_files):
            with open(file_path, 'r', encoding='utf-8') as infile:
                content = infile.read()
                
                content = re.sub(r'^\s*---\s*(#+.*)', r'\n***\n\n\1', content, flags=re.MULTILINE)
                content = re.sub(r'^\s*---\s*$', '***', content, flags=re.MULTILINE)
                
                outfile.write(content)
                
                if i < len(all_files) - 1:
                    page_break_code = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'
                    outfile.write(f'\n\n{page_break_code}\n\n')

            print(f"   - Aggiunto: {file_path.name}")
    
    print(f"✅ File combinato creato: {COMBINED_MD_FILENAME}\n")
    return COMBINED_MD_FILENAME

def wait_for_job(job_id):
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
    check_dependencies()

    if not API_KEY or API_KEY == "LA_TUA_CHIAVE_API_QUI":
        print("❌ Errore: La chiave API di CloudConvert non è stata impostata nel file .env.")
        print("   Devi creare un file '.env' e inserire 'CLOUDCONVERT_API_KEY=LaTuaChiave'.")
        sys.exit(1)

    combined_file = combine_markdown_files()

    print("2. Avvio del processo di conversione con CloudConvert...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-type": "application/json"
    }
    
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
                "engine": "pandoc",
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
    if 'data' not in response:
        print(f"❌ Errore nella creazione del job: {response}")
        sys.exit(1)
        
    job_id = response['data']['id']
    upload_task_id = response['data']['tasks'][0]['id']
    upload_url = response['data']['tasks'][0]['result']['form']['url']
    upload_params = response['data']['tasks'][0]['result']['form']['parameters']
    
    print(f"   - Job creato con ID: {job_id}")

    print("   - Caricamento del file combinato...")
    with open(combined_file, 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, data=upload_params, files=files)
    
    if upload_response.status_code != 201:
        print(f"❌ Errore durante il caricamento del file: {upload_response.text}")
        sys.exit(1)
    print("   - File caricato con successo.")

    print("   - In attesa del completamento della conversione...")
    job_data = wait_for_job(job_id)
    
    export_task = next(t for t in job_data['data']['tasks'] if t['operation'] == 'export/url')
    download_url = export_task['result']['files'][0]['url']
    
    print("\n3. Scaricamento del file convertito...")
    downloaded_file = requests.get(download_url)
    
    with open(OUTPUT_FILENAME, 'wb') as f:
        f.write(downloaded_file.content)
        
    print(f"✅ Documento Word creato con successo: {OUTPUT_FILENAME}")
    
    os.remove(combined_file)
    print(f"   - File temporaneo '{combined_file}' rimosso.")

if __name__ == "__main__":
    main()
