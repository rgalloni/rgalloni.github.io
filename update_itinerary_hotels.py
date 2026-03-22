import csv
import os
import re
from datetime import datetime, timedelta

def parse_date(date_str):
    """Prova a parsare le date nei formati YYYY e YY."""
    for fmt in ('%d/%m/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Formato data non riconosciuto per: {date_str}")

def update_itinerary_files():
    """
    Aggiorna i file dell'itinerario giornaliero con le informazioni degli hotel dal CSV.
    """
    csv_path = 'riepilogo_hotel.csv'
    itinerary_dir = 'Relazione_4808/Itinerario_Giornaliero/'

    if not os.path.exists(csv_path):
        print(f"Errore: File CSV '{csv_path}' non trovato.")
        return

    if not os.path.isdir(itinerary_dir):
        print(f"Errore: Directory itinerario '{itinerary_dir}' non trovata.")
        return

    # 1. Leggi e mappa le prenotazioni per data
    bookings_by_date = {}
    with open(csv_path, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter=';')
        try:
            header = [h.strip('"') for h in next(reader)]
        except StopIteration:
            print("Errore: il file CSV è vuoto.")
            return
            
        col_indices = {name: i for i, name in enumerate(header)}

        for row in reader:
            row_data = [field.strip('"') for field in row]
            
            try:
                check_in_date = parse_date(row_data[col_indices['Check-in']])
                check_out_date = parse_date(row_data[col_indices['Check-out']])
                
                hotel_info = {
                    "piu_stanze": row_data[col_indices['Più stanze']],
                    "overlap": row_data[col_indices['Overlap']],
                    "dove": row_data[col_indices['Dove']],
                    "dettagli_stanze": row_data[col_indices['Dettagli stanze']],
                    "conferma": row_data[col_indices['Numero di conferma/PIN']]
                }

                current_date = check_in_date
                while current_date < check_out_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if date_str not in bookings_by_date:
                        bookings_by_date[date_str] = []
                    bookings_by_date[date_str].append(hotel_info)
                    current_date += timedelta(days=1)
            except (ValueError, IndexError) as e:
                print(f"Riga saltata a causa di un errore: {row_data} -> {e}")
                continue

    # 2. Aggiorna i file Markdown
    for filename in sorted(os.listdir(itinerary_dir)):
        if not filename.endswith('.md'):
            continue

        match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if not match:
            continue
        
        file_date_str = match.group(1)
        file_path = os.path.join(itinerary_dir, filename)

        # Costruisci il nuovo contenuto per la sezione Pernottamento
        new_section_content = "## Pernottamento\n\n"
        if file_date_str in bookings_by_date:
            for booking in bookings_by_date[file_date_str]:
                new_section_content += f"- **{booking['dove']}**\n"
                new_section_content += f"  - **Conferma:** {booking['conferma']}\n"
                new_section_content += f"  - **Stanze:** {booking['dettagli_stanze']}\n"
                if booking['piu_stanze'].upper() == 'YES':
                    new_section_content += "  - **Nota:** Più prenotazioni presenti per questa struttura.\n"
                if booking['overlap'].upper() == 'YES':
                    new_section_content += "  - **ATTENZIONE: OVERLAP RILEVATO!** Questa prenotazione si sovrappone con un'altra.\n"
                new_section_content += "\n"
        else:
            new_section_content += "Nessun pernottamento registrato per questa data.\n"

        # Leggi il file e sostituisci o aggiungi la sezione
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        section_pattern = re.compile(r'(^## Pernottamento\s*\n)(?:.|\n)*?(?=\n##\s|\Z)', re.MULTILINE | re.DOTALL)
        line_pattern = re.compile(r'^- \*\*Pernottamento:\*\*.*$', re.MULTILINE)
        
        # Rimuove la vecchia riga di pernottamento se esiste, per evitare duplicati
        content_without_placeholder = line_pattern.sub('', content).strip()

        if section_pattern.search(content_without_placeholder):
            # Se la sezione ## Pernottamento esiste già, la sostituisce
            updated_content = section_pattern.sub(new_section_content, content_without_placeholder, count=1)
        else:
            # Altrimenti, aggiunge la nuova sezione alla fine del file
            updated_content = content_without_placeholder.strip() + '\n\n' + new_section_content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        print(f"Aggiornato il file: {filename}")

if __name__ == '__main__':
    update_itinerary_files()
    print("\nOperazione completata.")
