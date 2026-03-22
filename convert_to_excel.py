import pandas as pd

try:
    # Read the CSV file with semicolon delimiter
    csv_file = 'riepilogo_hotel.csv'
    df = pd.read_csv(csv_file, delimiter=';')

    # Define the Excel file name
    excel_file = 'riepilogo_hotel.xlsx'

    # Write the DataFrame to an Excel file
    df.to_excel(excel_file, index=False)

    print(f"File '{csv_file}' convertito con successo in '{excel_file}'")

except FileNotFoundError:
    print(f"Errore: il file '{csv_file}' non è stato trovato.")
except Exception as e:
    print(f"Si è verificato un errore durante la conversione: {e}")
