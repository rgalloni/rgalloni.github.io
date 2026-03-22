import csv
from datetime import datetime

def sort_key(row):
    try:
        return datetime.strptime(row[0], '%d/%m/%Y')
    except ValueError:
        return datetime.max # Puts 'Non specificato' at the end

with open('riepilogo_hotel.csv', 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')
    header = next(reader)
    data = sorted(reader, key=sort_key)

with open('riepilogo_hotel.csv', 'w', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(header)
    writer.writerows(data)

print("File riepilogo_hotel.csv ordinato con successo.")
