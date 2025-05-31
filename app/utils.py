import matplotlib.pyplot as plt
import os
from scipy.signal import find_peaks
from scipy.ndimage import minimum_filter #for Rolling Ball (or Morphological) Baseline Correction
from scipy.signal import savgol_filter #for smoothing algorithm
import sqlite3
import numpy as np
from numpy.polynomial.polynomial import Polynomial #for polynomial fitting algorithm
import pandas as pd
import pywt #for wavelet algorithm

height_threshold = 0.4 # Height threshold for peak detection

db_file_path = 'app/database/microplastics_reference.db'  # Path to SQLite database

def get_all_ids():
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ID FROM microplastics")
    rows = cursor.fetchall()
    conn.close()

    # Extract IDs from the fetched rows
    all_ids = [row[0] for row in rows]
    return all_ids

# Set reference_spectra_ids with all IDs from the database
reference_spectra_ids = get_all_ids()

def get_spectrum_data(material_id):
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT Intensity, WaveNumber, Comment FROM microplastics WHERE ID=?", (material_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return [], [], ''

    # Extract intensities and wave numbers from the query result
    intensities, wave_numbers = zip(*[(row[0], row[1]) for row in rows])

    # Extract comments, default to empty string if none present
    comments = [row[2] if len(row) > 2 else '' for row in rows]
    # Assuming the comment is the same for all entries of a material_id, take the first one
    comment = comments[0] if comments else ''
    return list(intensities), list(wave_numbers), comment


def normalize_data(intensities):
    max_intensity = max(intensities)
    return [i / max_intensity for i in intensities]

def process_spectrum(intensities, wavelengths):

    peaks, _ = find_peaks(intensities, height=height_threshold)
    peak_wavelengths = [wavelengths[i] for i in peaks]
    peak_intensities = [intensities[i] for i in peaks]

    return list(zip(peak_wavelengths, peak_intensities))

def plot_spectrum(wavelengths, intensities, peaks, title, filename, directory='app/plots'):
    if not os.path.exists(directory):
        os.makedirs(directory)

    peak_wavelengths, peak_intensities = zip(*peaks) if peaks else ([], [])

    plt.figure(figsize=(10, 5))
    plt.plot(wavelengths, intensities, label=title)
    plt.scatter(peak_wavelengths, peak_intensities, color='red', label='Peaks')
    plt.axhline(y=height_threshold, color='green', linestyle='--', label='Threshold')
    plt.xlabel('Wavenumber [/cm]')
    plt.ylabel('Intensity')
    plt.title(f'{title} Spectrum with Peaks')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{directory}/{filename}')
    plt.close()

def calculate_similarity(sample_peaks):
    similarities = {}
    window = 25

    for name in reference_spectra_ids:
        intensities, wavelengths, comment = get_spectrum_data(name)
        ref_peaks = process_spectrum(intensities, wavelengths)

        similarity_scores = []

        for sample_peak in sample_peaks:
            # Check suitable matching peaks within a ±window range
            sample_peak_score = -1
            sample_wavenumber = sample_peak[0]
            found_peak = False

            for ref_peak in ref_peaks:
                ref_wavenumber = ref_peak[0]
                ref_intensity = ref_peak[1]

                # Check if the reference peak is within the specified window
                if abs(sample_wavenumber - ref_wavenumber) <= window:
                    position_diff = abs(sample_wavenumber - ref_wavenumber) / ref_wavenumber
                    intensity_diff = abs(sample_peak[1] - ref_intensity) / ref_intensity

                    similarity = 1 - (0.8 * position_diff + 0.2 * intensity_diff)
                    weighted_similarity = similarity * ref_intensity

                    sample_peak_score = weighted_similarity
                    found_peak = True

            if found_peak == False:
                similarity_scores.append(-1)
            similarity_scores.append(sample_peak_score)

        # Calculate a weighted average similarity for this reference
        if similarity_scores:
            similarities[name] = np.average(similarity_scores)
        else:
            similarities[name] = 0

    # Determine the best match based on the similarity scores
    best_match = max(similarities, key=similarities.get) if similarities else None
    return similarities, best_match

def generate_plots():
    for material_id in reference_spectra_ids:
        intensities, wavelengths, comment = get_spectrum_data(material_id)

        if not intensities or not wavelengths:
            print(f"No data found for {material_id}")
            continue

        peaks, _ = find_peaks(intensities, height=height_threshold)
        peak_wavelengths = [wavelengths[i] for i in peaks]
        peak_intensities = [intensities[i] for i in peaks]

        plot_spectrum(
            wavelengths,
            intensities,
            list(zip(peak_wavelengths, peak_intensities)),
            material_id,
            f'{material_id}_with_peaks.png'
        )
    print("All plots generated and saved.")

def process_and_plot_sample(file, sample_id="Sample"):
    df = process_uploaded_file(file)

    wavelengths = df.iloc[:, 1].tolist()
    intensities = df.iloc[:, 0].tolist()
    sample_peaks = process_spectrum(intensities, wavelengths)

    max_intensity = max(intensities)
    intensities = [i / max_intensity for i in intensities]

    peaks, _ = find_peaks(intensities, height=height_threshold)
    peak_wavelengths = [wavelengths[i] for i in peaks]
    peak_intensities = [intensities[i] for i in peaks]

    plot_spectrum(wavelengths, intensities, list(zip(peak_wavelengths, peak_intensities)), sample_id, filename = f'sample_{sample_id}_with_peaks.png', directory='app/sample_plots')

    return sample_peaks, peak_wavelengths, peak_intensities

def process_uploaded_file(file):
    df = pd.read_csv(file)
    return df

def add_sample_to_bank(sample_id, intensities, wave_numbers, best_match, similarity_score):
    try:
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        for intensity, wave_number in zip(intensities, wave_numbers):
            cursor.execute("""
                INSERT INTO sample_bank (sample_id, intensity, wave_number, best_match, similarity_score)
                VALUES (?, ?, ?, ?, ?)
            """, (sample_id, intensity, wave_number, best_match, similarity_score))

        conn.commit()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def get_sample_data(sample_id):
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT intensity, wave_number FROM sample_bank WHERE sample_id=?", (sample_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return [], []

    intensities, wave_numbers = zip(*rows)
    return list(intensities), list(wave_numbers)

def generate_sample_plots(sample_ids):
    for sample_id in sample_ids:
        intensities, wave_numbers = get_sample_data(sample_id)

        if not intensities or not wave_numbers:
            print(f"No data found for {sample_id}")
            continue

        # Find peaks in the normalized intensities
        peaks, _ = find_peaks(intensities, height=height_threshold)
        peak_wavelengths = [wave_numbers[i] for i in peaks]
        peak_intensities = [intensities[i] for i in peaks]

        # Generate plot for the sample
        plot_spectrum(
            wave_numbers,
            intensities,
            list(zip(peak_wavelengths, peak_intensities)),
            sample_id,
            f'sample_{sample_id}_with_peaks.png',
            directory='app/sample_plots'
        )

    print("Sample plots generated and saved.")

def plot_sample_with_reference(sample_id, sample_wavelengths, sample_intensities, ref_wavelengths, ref_intensities, match_id):
    plt.figure(figsize=(10, 5))

    # Plot the sample spectrum
    plt.plot(sample_wavelengths, sample_intensities, label=f'Sample: {sample_id}')

    # Plot the matched reference spectrum in red dashed lines
    plt.plot(ref_wavelengths, ref_intensities, 'r--', label=f'Match: {match_id} (Reference)')

    plt.xlabel('Wavenumber [cm⁻¹]')
    plt.ylabel('Normalized Intensity')
    plt.title(f'Sample vs. Matched Reference')
    plt.legend()

    # Save the plot to a file
    plot_file_path = f'app/sample_plots/sample_{sample_id}_with_match.png'
    plot_file_path_to_render = f'sample_{sample_id}_with_match.png'
    plt.savefig(plot_file_path)
    plt.close()

    return plot_file_path_to_render

def process_and_compare_sample(file, sample_id, algorithm, param):
    df = process_uploaded_file(file)
    sample_intensities = df.iloc[:, 0].tolist()
    sample_wavelengths = df.iloc[:, 1].tolist()

    # Baseline correction for sample data
    # Apply the chosen baseline correction algorithm
    if algorithm == 'polynomial':
        corrected_sample_intensities = baseline_polynomial(sample_intensities, degree=int(param))
        normalized_sample_intensities = normalize_data(corrected_sample_intensities)
    elif algorithm == 'rolling_ball':
        corrected_sample_intensities = rolling_ball_baseline(sample_intensities, window_size=int(param))
        normalized_sample_intensities = normalize_data(corrected_sample_intensities)
    elif algorithm == 'wavelet':
        corrected_sample_intensities = wavelet_baseline(sample_intensities, level=int(param))
        normalized_sample_intensities = normalize_data(corrected_sample_intensities)
    elif algorithm == 'derivative':
        corrected_sample_intensities = derivative_baseline(sample_intensities, window_length=int(param))
        normalized_sample_intensities = normalize_data(corrected_sample_intensities)
    else:
        normalized_sample_intensities = normalize_data(sample_intensities) # No baseline correction applied

    # save_to_csv(corrected_sample_intensities, sample_wavelengths, sample_id) #for troubleshooting
    # Calculate peaks and find the best match
    sample_peaks = process_spectrum(normalized_sample_intensities, sample_wavelengths)
    results, best_match = calculate_similarity(sample_peaks)

    # Get matched reference data
    ref_intensities, ref_wavelengths, _ = get_spectrum_data(best_match)

    # Normalize reference data
    normalized_ref_intensities = normalize_data(ref_intensities)
    add_sample_to_bank(sample_id, normalized_sample_intensities, sample_wavelengths, best_match, best_match)
    # Plot the sample with the matched reference

    plot_file = plot_sample_with_reference(
        sample_id,
        sample_wavelengths,
        normalized_sample_intensities,
        ref_wavelengths,
        normalized_ref_intensities,
        best_match
    )

    return best_match, results, plot_file

###Removing Baseline algorithms

#promissing try changing parameter
#By fitting a polynomial to the data, you can estimate and subtract the baseline.
# This approach is quite different from ALS and can be effective when the baseline behaves like a polynomial function.
def baseline_polynomial(intensities, degree=3):
    indices = np.arange(len(intensities))
    poly = Polynomial.fit(indices, intensities, degree)

    baseline = poly(indices)
    corrected_spectrum = intensities - baseline

    return corrected_spectrum

#most promissing try changing parameter or ebhance this
#This method finds baselines as an envelope of the data using mathematical morphology operations,
# suitable for baselines that need localization and aren't of polynomial form.
def rolling_ball_baseline(intensities, window_size=50):
    baseline = minimum_filter(intensities, size=window_size)
    corrected_spectrum = np.array(intensities) - baseline

    return corrected_spectrum

#Doesnt seem to work
#Wavelet transforms can be used to decompose the signal and separate out low-frequency components considered as the baseline.
def wavelet_baseline(intensities, wavelet='db3', level=1):
    coeffs = pywt.wavedec(intensities, wavelet, level=level)

    # Set approximation coefficients to zero to remove baseline
    coeffs[0] *= 0

    baseline = pywt.waverec(coeffs, wavelet)
    if len(baseline) != len(intensities):
        baseline = baseline[:len(intensities)]  # Adjust length if necessary

    corrected_spectrum = np.array(intensities) - baseline

    return corrected_spectrum

#doesnt seem to work
#This approach utilizes smoothing, followed by calculation of derivatives to approximate the baseline.
def derivative_baseline(intensities, window_length=11, polyorder=2):
    smoothed = savgol_filter(intensities, window_length, polyorder)
    derivative = np.gradient(smoothed)  # First derivative

    baseline = np.cumsum(derivative)  # Integrate to get back the baseline

    corrected_spectrum = np.array(intensities) - baseline
    return corrected_spectrum

###auxiliary function for troobleshooting
def save_to_csv(intensities, wavenumbers, filename='output.csv'):

    # Create a DataFrame for easier CSV export
    df = pd.DataFrame({
        'Intensity': intensities,
        'Wavenumber': wavenumbers
    })

    # Save to CSV
    df.to_csv(filename, index=False)
