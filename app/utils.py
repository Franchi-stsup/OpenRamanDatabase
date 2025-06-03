import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web applications
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
import functools

height_threshold = 0.25 # Height threshold for peak detection

db_file_path = 'app/database/microplastics_reference.db'  # Path to SQLite database

# Simple cache for spectrum data
spectrum_data_cache = {}

@functools.lru_cache(maxsize=32)
def get_comment(material_id):
    """Get just the comment for a material ID - much faster than retrieving the full spectrum.
    
    This function uses LRU caching to store up to 32 most recently accessed comments in memory,
    which significantly improves performance when comments are accessed repeatedly.
    
    Args:
        material_id (str): The ID of the material to fetch the comment for
        
    Returns:
        str: The comment associated with the material, or empty string if none exists
    """
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Comment FROM microplastics WHERE ID=? LIMIT 1", (material_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else ''

def get_all_comments():
    """Get all material IDs and their comments in a single database query.
    This is much more efficient than making separate queries for each ID.
    
    This function makes a single database connection and query to fetch all comments at once,
    which is significantly faster than fetching each comment individually, especially when
    there are many materials in the database.
    
    Returns:
        dict: A dictionary mapping material IDs to their comments, with empty strings for
              materials that have no comment or 'None' as a comment
    """
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ID, Comment FROM microplastics")
    results = cursor.fetchall()
    conn.close()
    
    # Convert to a dictionary for easy lookup
    comments_dict = {row[0]: row[1] if row[1] and row[1] != 'None' else '' for row in results}
    return comments_dict

def get_all_ids():
    """Retrieve all unique material IDs from the microplastics database.
    
    This function makes a database query to fetch all distinct material IDs from
    the microplastics reference database. These IDs are used throughout the application
    to identify different reference materials.
    
    Returns:
        list: A list of all unique material IDs in the database
    """
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
    """Retrieve spectrum data for a specific material from the database.
    
    This function fetches the intensity values, wave numbers, and associated comment
    for a given material ID from the microplastics database. The data is used for
    spectrum analysis and visualization.
    
    Args:
        material_id (str): The ID of the material to fetch spectrum data for
        
    Returns:
        tuple: A tuple containing three elements:
            - list of intensity values
            - list of corresponding wave numbers
            - str containing the comment associated with the material
    """
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
    """Normalize intensity values to a range of 0 to 1.
    
    This function scales all intensity values by dividing by the maximum intensity,
    which ensures all values are between 0 and 1. Normalization is important for
    comparing spectra with different absolute intensity scales.
    
    Args:
        intensities (list): List of intensity values to normalize
        
    Returns:
        list: Normalized intensity values, where the maximum value is 1.0
    """
    max_intensity = max(intensities)
    return [i / max_intensity for i in intensities]

def process_spectrum(intensities, wavelengths):
    """Process a spectrum by identifying significant peaks.
    
    This function detects peaks in the spectrum data that exceed the defined height
    threshold. These peaks are characteristic features used for material identification
    and spectrum comparison.
    
    Args:
        intensities (list): List of intensity values for the spectrum
        wavelengths (list): List of corresponding wave numbers for each intensity value
        
    Returns:
        list: List of tuples, where each tuple contains (wavelength, intensity) for each detected peak
    """
    peaks, _ = find_peaks(intensities, height=height_threshold)
    peak_wavelengths = [wavelengths[i] for i in peaks]
    peak_intensities = [intensities[i] for i in peaks]

    return list(zip(peak_wavelengths, peak_intensities))

def plot_spectrum(wavelengths, intensities, peaks, title, filename, directory='app/plots'):
    """Generate and save a plot of a spectrum with detected peaks.
    
    This function creates a visualization of the spectrum data, highlighting detected peaks
    and the threshold used for peak detection. The plot is saved as an image file in the 
    specified directory.
    
    Args:
        wavelengths (list): List of wave numbers for the spectrum
        intensities (list): List of corresponding intensity values
        peaks (list): List of detected peaks as (wavelength, intensity) tuples
        title (str): Title for the plot, typically the material ID
        filename (str): Filename to save the plot as
        directory (str, optional): Directory to save the plot in. Defaults to 'app/plots'.
    """
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

def calculate_similarity2(sample_peaks):
    """Calculate similarity between a sample spectrum and all reference spectra.
    
    This function compares the peaks of a sample spectrum with all reference spectra in the 
    database to find the best match. For each reference spectrum, it calculates similarity 
    scores based on the position and intensity of peaks within a specified window. The 
    similarity calculation weighs peak position differences more heavily (80%) than 
    intensity differences (20%).
    
    Args:
        sample_peaks (list): List of detected peaks in the sample spectrum as (wavelength, intensity) tuples
        
    Returns:
        tuple: A tuple containing:
            - dict: Dictionary mapping reference material IDs to their similarity scores
            - str: Material ID of the best match (highest similarity score)
    """
    similarities = {}
    window = 35  # Wavelength window size for peak matching (±25 cm⁻¹)

    for name in reference_spectra_ids:
        # intensities, wavelengths, comment = get_spectrum_data(name)
        # ref_peaks = process_spectrum(intensities, wavelengths)

        #Use pre-calculated peaks from the database for efficiency
        ref_peaks = get_peaks(name)

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

                    # Calculate similarity with 80% weight on position and 20% on intensity
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

def calculate_similarity(sample_peaks):
    """Calculate similarity using a weighted match score with Gaussian weighting.
    
    This method compares sample peaks to reference spectra using a similarity score
    that favors close peak positions and similar intensities. Position differences
    are evaluated using a Gaussian function and intensity using a ratio.
    
    Args:
        sample_peaks (list): List of (wavenumber, intensity) tuples from the sample spectrum.
        
    Returns:
        tuple: (dict of similarity scores per reference ID, best matching reference ID)
    """
    similarities = {}
    window = 35  # Wavelength window size for peak matching (± cm⁻¹)
    sigma = window / 2.0  # Spread for Gaussian weighting

    for name in reference_spectra_ids:
        ref_peaks = get_peaks(name)
        match_scores = []

        for sample_wavenumber, sample_intensity in sample_peaks:
            best_score = -1

            for ref_wavenumber, ref_intensity in ref_peaks:
                position_diff = sample_wavenumber - ref_wavenumber

                # Only consider matches within the window
                if abs(position_diff) <= window:
                    # Gaussian weight for position
                    position_weight = np.exp(- (position_diff ** 2) / (2 * sigma ** 2))

                    # Intensity similarity (bounded ratio)
                    if ref_intensity > 0 and sample_intensity > 0:
                        intensity_similarity = min(sample_intensity, ref_intensity) / max(sample_intensity, ref_intensity)
                    else:
                        intensity_similarity = 0

                    # Combined score
                    score = position_weight * intensity_similarity

                    if score > best_score:
                        best_score = score

            # Add the best score for this sample peak (even if unmatched, will be -1)
            match_scores.append(best_score)

        # Average over all match scores for this reference
        if match_scores:
            similarities[name] = np.mean(match_scores)
        else:
            similarities[name] = 0

    best_match = max(similarities, key=similarities.get) if similarities else None
    return similarities, best_match


def generate_plots():
    """Generate spectral plots for all reference materials in the database.
    
    This function creates visualizations for all reference spectra in the database,
    identifying peaks in each spectrum and saving the plots to the plots directory.
    The function includes timing measurements to track performance and outputs
    progress information to the console.
    
    Returns:
        float: Total time taken to generate all plots in seconds
    """
    import time
    
    # Start timing
    start_time = time.time()
    plot_count = 0
    
    for material_id in reference_spectra_ids:
        intensities, wavelengths, comment = get_spectrum_data(material_id)

        if not intensities or not wavelengths:
            print(f"No data found for {material_id}")
            continue

        # peaks, _ = find_peaks(intensities, height=height_threshold)
        # peak_wavelengths = [wavelengths[i] for i in peaks]
        # peak_intensities = [intensities[i] for i in peaks]
        # peak_data = get_peaks(material_id)

        plot_spectrum(
            wavelengths,
            intensities,
            # list(zip(peak_wavelengths, peak_intensities)),
            get_peaks(material_id),
            material_id,
            f'{material_id}_with_peaks.png'
        )
        plot_count += 1
        
        # Print progress every 10 plots
        if plot_count % 10 == 0:
            current_time = time.time() - start_time
            print(f"Generated {plot_count}/{len(reference_spectra_ids)} plots in {current_time:.2f} seconds")
    
    # Calculate total time
    total_time = time.time() - start_time
    print(f"All {plot_count} plots generated and saved in {total_time:.2f} seconds")
    
    return total_time

def process_and_plot_sample(file, sample_id="Sample"):
    """Process an uploaded sample file, detect peaks, and generate a plot.
    
    This function takes an uploaded spectrum file, extracts the intensity and wavelength data,
    normalizes the intensities, identifies peaks, and generates a plot visualizing the sample 
    spectrum with its detected peaks.
    
    Args:
        file: The uploaded file containing spectrum data
        sample_id (str, optional): Identifier for the sample. Defaults to "Sample".
        
    Returns:
        tuple: A tuple containing:
            - list: Sample peaks as (wavelength, intensity) tuples
            - list: Wavelengths of detected peaks
            - list: Intensity values at detected peaks
    """
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
    """Process an uploaded CSV file containing spectrum data.
    
    This function reads a CSV file containing Raman spectroscopy data and converts it 
    to a pandas DataFrame for further processing. The file is expected to contain 
    intensity values and corresponding wave numbers.
    
    Args:
        file: The uploaded CSV file
        
    Returns:
        pandas.DataFrame: DataFrame containing the spectrum data
    """
    df = pd.read_csv(file)
    return df

def add_sample_to_bank(sample_id, intensities, wave_numbers, best_match, similarity_score):
    """Add a processed sample spectrum to the sample bank database.
    
    This function stores a processed sample spectrum in the database for future reference.
    It saves each data point (intensity and wave number) along with metadata about the
    sample, including its ID, best matching reference, and similarity score.
    
    Args:
        sample_id (str): Identifier for the sample
        intensities (list): List of intensity values for the sample spectrum
        wave_numbers (list): List of corresponding wave numbers
        best_match (str): ID of the best matching reference material
        similarity_score (float): Similarity score between the sample and best match
    """
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
    """Retrieve spectrum data for a specific sample from the sample bank.
    
    This function fetches intensity and wave number data for a previously processed
    and stored sample from the database. The data can be used for further analysis
    or visualization.
    
    Args:
        sample_id (str): The ID of the sample to retrieve data for
        
    Returns:
        tuple: A tuple containing:
            - list: Intensity values for the sample spectrum
            - list: Corresponding wave numbers
    """
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

def get_peaks(material_id):
    """Retrieve pre-calculated peaks for a specific material from the reference_peaks table.
    
    This function fetches pre-calculated peak data from the reference_peaks table for a given
    material ID. It filters peaks based on the global height_threshold value and returns
    them in the same format as the process_spectrum function.
    
    Args:
        material_id (str): The ID of the material to fetch peaks for
        
    Returns:
        list: List of tuples, where each tuple contains (wavelength, intensity) for each detected peak
              that exceeds the height threshold
    """
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    
    # Query peaks from the reference_peaks table that exceed the height threshold
    cursor.execute("SELECT wavenumber, intensity FROM reference_peaks WHERE microplastic_id=? AND intensity >= ?", 
                  (material_id, height_threshold))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
    
    # No need to separate as the query already returns (wavenumber, intensity) pairs
    return list(rows)
