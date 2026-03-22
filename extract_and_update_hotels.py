import csv
import re
from datetime import datetime
import pandas as pd

def extract_booking_info(text_content, filename):
    info = {
        'Check-in': 'Non specificato',
        'Check-out': 'Non specificato',
        'Dove': 'Non specificato',
        'Colazione': 'Non specificato',
        'Cucina': 'Non specificato',
        'Dettagli stanze': 'Non specificato',
        'Cancellabile': 'Non specificato',
        'Entro quando cancellabile': 'Non specificato',
        'Sito prenotazione': 'Non specificato',
        'Pagabile in loco': 'Non specificato',
        'Numero di conferma/PIN': 'Non specificato',
        'Link di gestione prenotazione': 'Non specificato',
        'Costo totale': 'Non specificato'
    }

    # Determine source
    if "Booking.com" in text_content:
        info['Sito prenotazione'] = 'Booking.com'
    elif "Ptarmigan Inn" in text_content or "Nahanni Traveller Hotel" in text_content or "Toad River Lodge" in text_content:
        info['Sito prenotazione'] = 'Email'
    else:
        info['Sito prenotazione'] = 'Sconosciuto'

    # Extract Hotel Name and City
    hotel_match = re.search(r'La tua prenotazione aggiornata per (.+?)\n|Hotel\n(.+?)\n\d+ \w+ Street, (.+?),', text_content)
    if hotel_match:
        if hotel_match.group(1):
            info['Dove'] = hotel_match.group(1).strip()
        elif hotel_match.group(2) and hotel_match.group(3):
            info['Dove'] = f"{hotel_match.group(2).strip()}, {hotel_match.group(3).strip()}"
    elif "Ptarmigan Inn" in text_content:
        info['Dove'] = "Ptarmigan Inn, Hay River"
    elif "Nahanni Traveller Hotel" in text_content:
        info['Dove'] = "Nahanni Traveller Hotel, Fort Simpson"
    elif "Toad River Lodge" in text_content:
        info['Dove'] = "Toad River Lodge"


    # Extract Check-in and Check-out dates
    check_in_match = re.search(r'Arrivo\s+([a-zA-Z]+\s+\d+\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})', text_content)
    check_out_match = re.search(r'Partenza\s+([a-zA-Z]+\s+\d+\s+\w+\s+\d{4}|\w+\s+\d{1,2},\s+\d{4})', text_content)
    
    if check_in_match:
        date_str = check_in_match.group(1).replace('alle ore ', '').replace('dalle ore ', '').strip()
        try:
            info['Check-in'] = datetime.strptime(date_str, '%A %d %B %Y').strftime('%d/%m/%Y')
        except ValueError:
            try:
                info['Check-in'] = datetime.strptime(date_str, '%B %d, %Y').strftime('%d/%m/%Y')
            except ValueError:
                try:
                    info['Check-in'] = datetime.strptime(date_str, '%b %d, %Y').strftime('%d/%m/%Y')
                except ValueError:
                    pass # Keep 'Non specificato' if parsing fails
    
    if check_out_match:
        date_str = check_out_match.group(1).replace('alle ore ', '').replace('fino alle ore ', '').strip()
        try:
            info['Check-out'] = datetime.strptime(date_str, '%A %d %B %Y').strftime('%d/%m/%Y')
        except ValueError:
            try:
                info['Check-out'] = datetime.strptime(date_str, '%B %d, %Y').strftime('%d/%m/%Y')
            except ValueError:
                try:
                    info['Check-out'] = datetime.strptime(date_str, '%b %d, %Y').strftime('%d/%m/%Y')
                except ValueError:
                    pass # Keep 'Non specificato' if parsing fails

    # Specific handling for email dates if not found above
    if info['Check-in'] == 'Non specificato' and info['Check-out'] == 'Non specificato':
        date_range_match = re.search(r'availability from August (\d+) to (\d+)\?', text_content)
        if date_range_match:
            start_day = date_range_match.group(1)
            end_day = date_range_match.group(2)
            info['Check-in'] = f"{start_day}/08/2025" # Assuming 2025 based on other files
            info['Check-out'] = f"{end_day}/08/2025"

    # Extract Colazione
    if re.search(r'Colazione\s+La colazione è inclusa nel prezzo finale', text_content):
        info['Colazione'] = 'Sì'
    elif re.search(r'Colazione\s+La tariffa di questa camera non include alcun pasto', text_content):
        info['Colazione'] = 'No'
    elif re.search(r'Pasti\s+Colazione costa CAD \d+ a persona per notte', text_content):
        info['Colazione'] = 'Sì (a pagamento)'
    elif re.search(r'Breakfast not included', text_content):
        info['Colazione'] = 'No'

    # Extract Cucina
    if re.search(r'kitchenette|kitchen|cucina attrezzata|prepping meals', text_content, re.IGNORECASE):
        info['Cucina'] = 'Sì'
    elif re.search(r'Cucina\s+No', text_content):
        info['Cucina'] = 'No'

    # Extract Dettagli stanze
    room_details_match = re.search(r'Dettagli sulle camere\s+(.+?)\nNome dell\'ospite', text_content, re.DOTALL)
    if room_details_match:
        info['Dettagli stanze'] = room_details_match.group(1).strip().replace('\n', ' ')
    else:
        room_type_match = re.search(r'Room Type: (.+?)\n', text_content)
        if room_type_match:
            info['Dettagli stanze'] = room_type_match.group(1).strip()
        else:
            room_desc_match = re.search(r'(\d+)\s+camere\s+(.+?)\n|(\d+)\s+camere\s+Queen con due letti Queen', text_content)
            if room_desc_match:
                if room_desc_match.group(2):
                    info['Dettagli stanze'] = f"{room_desc_match.group(1)} camere {room_desc_match.group(2).strip()}"
                elif room_desc_match.group(3):
                    info['Dettagli stanze'] = f"{room_desc_match.group(3)} camere Queen con due letti Queen"
            else:
                    room_type_booking_match = re.search(r'(\d+)\s+camere\n(.+?)\n\d+\s+%\s+tassa', text_content, re.DOTALL)
                    if room_type_booking_match:
                        details = room_type_booking_match.group(2).strip().replace('\n', ' ')
                        info['Dettagli stanze'] = f"{room_type_booking_match.group(1)} camere {details}"
                    else:
                        room_type_booking_match_single = re.search(r'La tua prenotazione \d+ notti, \d+ camera\n.+?\n(.+?)\n\d+,\d+\s+%\s+tassa', text_content, re.DOTALL)
                        if room_type_booking_match_single:
                            info['Dettagli stanze'] = room_type_booking_match_single.group(1).strip().replace('\n', ' ')
                        else: # This else corresponds to room_type_booking_match_single
                            room_type_booking_match_single_email = re.search(r'Room Type: (.+?)\n', text_content)
                            if room_type_booking_match_single_email:
                                info['Dettagli stanze'] = room_type_booking_match_single_email.group(1).strip()
                            elif "3 rooms with 2 queen beds and kitchenette" in text_content:
                                info['Dettagli stanze'] = "3 camere con 2 letti queen size e angolo cottura"
                            elif "3 camere Queen con due letti Queen" in text_content:
                                info['Dettagli stanze'] = "3 camere Queen con due letti Queen"
                            elif "2 camere matrimoniali con bagno in comune" in text_content:
                                info['Dettagli stanze'] = "2 camere matrimoniali con bagno in comune"
                            elif "12 posti letto in dormitorio misto con 8 letti" in text_content:
                                info['Dettagli stanze'] = "12 posti letto in dormitorio misto con 8 letti"
                            elif "2 suite Alpine Kitchen con 2 letti queen size, 1 camera Woodland con balcone e 2 letti queen size" in text_content:
                                info['Dettagli stanze'] = "2 suite Alpine Kitchen con 2 letti queen size, 1 camera Woodland con balcone e 2 letti queen size"
                            elif "3 camere con 2 letti King-Size" in text_content:
                                info['Dettagli stanze'] = "3 camere con 2 letti King-Size"
                            elif "Superior Hotel Room, 2 Queens" in text_content:
                                info['Dettagli stanze'] = "Superior Hotel Room, 2 Queens"
                            elif "3 camere Matrimoniali Economy con Letto Queen-Size" in text_content:
                                info['Dettagli stanze'] = "3 camere Matrimoniali Economy con Letto Queen-Size"
                            elif "3 Camere Familiari Deluxe (3 letti per camera)" in text_content:
                                info['Dettagli stanze'] = "3 Camere Familiari Deluxe (3 letti per camera)"
                            elif "3 Camere Standard Queen con 2 Letti Queen-Size" in text_content:
                                info['Dettagli stanze'] = "3 Camere Standard Queen con 2 Letti Queen-Size"
                            elif "3 Camere con 2 Letti Queen-Size - Non Fumatori" in text_content:
                                info['Dettagli stanze'] = "3 Camere con 2 Letti Queen-Size - Non Fumatori"
                            elif "Camera Matrimoniale con Bagno Privato Esterno (1 letto)" in text_content:
                                info['Dettagli stanze'] = "Camera Matrimoniale con Bagno Privato Esterno (1 letto)"
                            elif "1 Appartamento con 3 Camere da Letto (4 letti)" in text_content:
                                info['Dettagli stanze'] = "1 Appartamento con 3 Camere da Letto (4 letti)"
                            elif "3 Camere con 2 Letti Matrimoniali" in text_content:
                                info['Dettagli stanze'] = "3 Camere con 2 Letti Matrimoniali"


    # Extract Cancellabile and Entro quando cancellabile
    cancellation_match = re.search(r'Puoi cancellare gratuitamente fino a (.+?)\.', text_content)
    if cancellation_match:
        info['Cancellabile'] = 'SI'
        info['Entro quando cancellabile'] = cancellation_match.group(1).strip()
        # Further parse date if possible
        date_cancel_match = re.search(r'alle (\d{1,2} \w+ \d{4})', info['Entro quando cancellabile'])
        if date_cancel_match:
            date_str = date_cancel_match.group(1)
            try:
                info['Entro quando cancellabile'] = datetime.strptime(date_str, '%d %B %Y').strftime('%d/%m/%Y')
            except ValueError:
                try:
                    info['Entro quando cancellabile'] = datetime.strptime(date_str, '%d %b %Y').strftime('%d/%m/%Y')
                except ValueError:
                    pass
        elif "1 giorno prima dell'arrivo" in info['Entro quando cancellabile']:
            info['Entro quando cancellabile'] = '1 giorno prima dell\'arrivo'
        elif "3 giorni prima dell'arrivo" in info['Entro quando cancellabile']:
            info['Entro quando cancellabile'] = '3 giorni prima dell\'arrivo'
        elif "7 giorni prima dell'arrivo" in info['Entro quando cancellabile']:
            info['Entro quando cancellabile'] = '7 giorni prima dell\'arrivo'
        elif "24 hours prior notice" in info['Entro quando cancellabile']:
            info['Entro quando cancellabile'] = '24 ore prima dell\'arrivo'
    else:
        info['Cancellabile'] = 'No'

    # Extract Pagabile in loco
    if re.search(r'Pagabile in loco|effettueremo l\'addebito sulla tua carta in modo automatico', text_content):
        info['Pagabile in loco'] = 'No' # If automatic charge, not payable in loco
    elif re.search(r'Pagamento\s+Questa struttura accetta i seguenti metodi di pagamento', text_content) and "Pagabile in loco" not in text_content:
        info['Pagabile in loco'] = 'Non specificato'
    elif re.search(r'We will pay on arrival', text_content):
        info['Pagabile in loco'] = 'Sì'
    elif re.search(r'your card will not be charged your arrival', text_content):
        info['Pagabile in loco'] = 'Sì'


    # Extract Numero di conferma/PIN
    conf_pin_match = re.search(r'Numero di conferma:\s*(\d+)\s*\n\s*Codice PIN:\s*(\d+)', text_content)
    if conf_pin_match:
        info['Numero di conferma/PIN'] = f"Conf: {conf_pin_match.group(1)}, PIN: {conf_pin_match.group(2)}"
    else:
        conf_num_match = re.search(r'Confirmation Number: (\d+)', text_content)
        if conf_num_match:
            info['Numero di conferma/PIN'] = f"Conf: {conf_num_match.group(1)}"
        elif "Nahanni Traveller Hotel" in info['Dove']:
            # For Nahanni, the confirmation is implied by the email exchange
            info['Numero di conferma/PIN'] = "Confermato via Email"


    # Extract Link di gestione prenotazione
    link_match = re.search(r'Modifica la prenotazione\n(.+?)\n|Gestisci la prenotazione\n(.+?)\n', text_content)
    if link_match:
        if link_match.group(1):
            info['Link di gestione prenotazione'] = link_match.group(1).strip()
        elif link_match.group(2):
            info['Link di gestione prenotazione'] = link_match.group(2).strip()
    elif "booking.com" in info['Sito prenotazione'].lower():
        info['Link di gestione prenotazione'] = "Vedi Booking.com"
    elif "Email" in info['Sito prenotazione']:
        info['Link di gestione prenotazione'] = "Contatta struttura via Email"


    # Extract Costo totale
    total_cost_match = re.search(r'Importo totale\s+CAD\s+([\d\.,]+)', text_content)
    if total_cost_match:
        info['Costo totale'] = f"CAD {total_cost_match.group(1).replace('.', '').replace(',', '.')}"
    elif re.search(r'Price: ([\d\.]+)', text_content):
        price_match = re.search(r'Price: ([\d\.]+)', text_content)
        if price_match:
            info['Costo totale'] = f"CAD {price_match.group(1)}"
        elif "Nahanni Traveller Hotel" in info['Dove']:
            # For Nahanni, infer from email conversation
            info['Costo totale'] = "CAD 210 per camera/notte"
        elif "Toad River Lodge" in info['Dove']:
            info['Costo totale'] = "CAD 179 + tasse per camera/notte"


    return info

def process_all_bookings(text_files_dir):
    all_bookings = []
    
    # List all relevant files
    file_list = [f for f in os.listdir(text_files_dir) if f.endswith('.txt') and 
                 not f.startswith('006345') and not f.startswith('Come valuteresti')]

    for filename in file_list:
        file_path = os.path.join(text_files_dir, filename)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            booking_data = extract_booking_info(content, filename)
            
            # Special handling for Ptarmigan Inn to count multiple rooms
            if "Ptarmigan Inn" in booking_data['Dove'] and "Confirmation Number" in booking_data['Numero di conferma/PIN']:
                # Add each Ptarmigan Inn booking as a separate entry if multiple confirmations
                # This assumes each file is a unique confirmation for a single room
                all_bookings.append(booking_data)
            elif "Nahanni Traveller Hotel" in booking_data['Dove']:
                # For Nahanni, it's 3 rooms, so add 3 entries
                for _ in range(3):
                    all_bookings.append(booking_data)
            elif "Toad River Lodge" in booking_data['Dove']:
                # Toad River Lodge was not confirmed, so skip
                continue
            else:
                all_bookings.append(booking_data)
    
    return all_bookings

# Main execution
import os

text_files_directory = 'Hotel/Converted_Text/'
output_csv_file = 'riepilogo_hotel.csv'
output_excel_file = 'riepilogo_hotel.xlsx'

# Process all text files
bookings = process_all_bookings(text_files_directory)

# Convert check-in dates for sorting
for booking in bookings:
    try:
        booking['Check-in_dt'] = datetime.strptime(booking['Check-in'], '%d/%m/%Y')
    except ValueError:
        booking['Check-in_dt'] = datetime.min # Assign a very early date for unparseable dates

# Sort bookings by check-in date
bookings.sort(key=lambda x: x['Check-in_dt'])

# Prepare data for CSV writing
header = [
    'Check-in', 'Check-out', 'Dove', 'Colazione', 'Cucina', 
    'Dettagli stanze', 'Cancellabile', 'Entro quando cancellabile', 
    'Sito prenotazione', 'Pagabile in loco', 'Numero di conferma/PIN', 
    'Link di gestione prenotazione', 'Costo totale'
]

csv_rows = [header]
for booking in bookings:
    row = [booking.get(col, 'Non specificato') for col in header]
    csv_rows.append(row)

# Write to CSV
with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerows(csv_rows)

print(f"File '{output_csv_file}' aggiornato e ordinato con successo.")

# Convert CSV to Excel
try:
    df = pd.read_csv(output_csv_file, delimiter=';')
    df.to_excel(output_excel_file, index=False)
    print(f"File '{output_csv_file}' convertito con successo in '{output_excel_file}'")
except Exception as e:
    print(f"Si è verificato un errore durante la conversione in Excel: {e}")
