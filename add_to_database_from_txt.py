#script to incorporate data from txt files into the database

import os
import sqlite3
import pandas as pd

# Set root directory for raw data files and SQLite database path
root_folder = 'OPENRAMANDATABASE'  # Adjust this to your actual path
db_file_path = 'app/database/microplastics_reference.db'  # SQLite database path

# Prepare a connection to the SQLite database
conn = sqlite3.connect(db_file_path)
cursor = conn.cursor()


# Similar data dictionary to process and store all data
data = {}

# Function to process a single file
def process_file(file_path):
    # Assume columns correspond to wave number and intensities
    df = pd.read_csv(file_path, sep='\s+', header=None, names=['WaveNumber', 'Intensity'])
    
    # Normalize intensities
    max_intensity = df['Intensity'].max()
    df['NormalizedIntensity'] = df['Intensity'] / max_intensity
    
    # Use file path or unique part of it as ID
    ID = os.path.splitext(os.path.basename(file_path))[0]
    
    if ID not in data:
        data[ID] = {'WaveNumbers': [], 'Intensities': []}
    
    # Append data for this ID
    data[ID]['WaveNumbers'].extend(df['WaveNumber'].tolist())
    data[ID]['Intensities'].extend(df['NormalizedIntensity'].tolist())

# Traverse directory to find all .txt files
for root, _, files in os.walk(root_folder):
    for file in files:
        if file.endswith('.txt'):
            file_path = os.path.join(root, file)
            process_file(file_path)

# Insert collected data into the database
for ID in data:
    for intensity, wave_number in zip(data[ID]['Intensities'], data[ID]['WaveNumbers']):
        cursor.execute("INSERT INTO microplastics (ID, Intensity, WaveNumber) VALUES (?, ?, ?)", (ID, intensity, wave_number))
    print(f"Inserted data for ID: {ID}")

# Commit all changes to the database
conn.commit()

# Function to query processed data by ID
def query_by_id(search_id):
    cursor.execute("SELECT Intensity, WaveNumber FROM microplastics WHERE ID=?", (search_id,))
    rows = cursor.fetchall()
    intensities, wave_numbers = zip(*rows) if rows else ([], [])
    return list(intensities), list(wave_numbers)

# Example usage demonstration
ID_to_query = "Acrylic 1. Green Yarn"  # Use a specific file name as ID
intensities, wave_numbers = query_by_id(ID_to_query)
print("Intensities:", intensities)
print("Wave Numbers:", wave_numbers)

# Close the database connection
conn.close()