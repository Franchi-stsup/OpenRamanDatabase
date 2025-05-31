from flask import Flask, request, render_template, send_from_directory, redirect
import os
import sqlite3
import time
from app.utils import *

app = Flask(__name__)
db_file_path = 'app/database/microplastics_reference.db'  # Path to SQLite database

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Start timing the processing
        start_time = time.time()
        
        file = request.files['file']
        sample_id = request.form.get('sample_id')
        algorithm = request.form.get('algorithm')
        param = request.form.get('param')

        if file and sample_id:
            best_match, results, plot_file = process_and_compare_sample(file, sample_id, algorithm, param)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            print(f"Spectrum processing time: {processing_time:.4f} seconds")

            return render_template('index.html', results=results, best_match=best_match, 
                                 score=results[best_match], sample_plot=plot_file,
                                 processing_time=f"{processing_time:.4f}")

    return render_template('index.html', results=None, best_match=None, score=None, sample_plot=None)

@app.route('/library', methods=['GET', 'POST'])
def library():
    # Start timing the function execution
    start_time = time.time()
    plot_time = None
    
    if request.method == 'POST':
        plot_time = generate_plots()

    plots = os.listdir('app/plots')

    # Fetch all comments
    comments = {}
    for material_id in reference_spectra_ids:
        _, _, comment = get_spectrum_data(material_id)
        comments[material_id] = comment

    total_ids = len(reference_spectra_ids)
    
    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    print(f"Library route execution time: {elapsed_time:.4f} seconds")
    
    return render_template('library.html', plots=plots, total_ids=total_ids, comments=comments, 
                          load_time=elapsed_time, plot_time=plot_time)

@app.route('/plots/<filename>')
def plot(filename):
    if 'sample' in filename:
        return send_from_directory('sample_plots', filename)
    return send_from_directory('plots', filename)

@app.route('/sample_plots/<filename>')
def sample_plot_retrieve(filename):
    return send_from_directory('sample_plots', filename)

@app.route('/update_comment', methods=['POST'])
def update_comment():
    material_id = request.form.get('material_id')
    new_comment = request.form.get('comment')

    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE microplastics SET Comment=? WHERE ID=?", (new_comment, material_id))
    conn.commit()
    conn.close()
    
    # Clear the comment cache for this material
    if hasattr(get_comment, 'cache_clear'):
        get_comment.cache_clear()

    # Check if this is an AJAX request by examining headers
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 204  # Return success but no content
    else:
        # If it's a regular form submission, redirect
        return redirect('/library')
@app.route('/add_sample', methods=['POST'])
def add_sample():
    sample_id = request.form.get('sample_id')
    file = request.files.get('file')

    if sample_id and file:
        df = process_uploaded_file(file)
        intensities = df.iloc[:, 0].tolist()
        wave_numbers = df.iloc[:, 1].tolist()
        add_sample_to_bank(sample_id, intensities, wave_numbers)

    return redirect('/')

@app.route('/sample_history', methods=['GET'])
def sample_history():
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT sample_id FROM sample_bank")
    samples = cursor.fetchall()
    conn.close()

    sample_ids = [sample[0] for sample in samples]
    #generate_sample_plots(sample_ids)
    plots = os.listdir('app/sample_plots')

    return render_template('sample_history.html', samples=sample_ids, plots=plots)
@app.route('/delete_sample', methods=['POST'])
def delete_sample():
    sample_id = request.form.get('sample_id')

    if sample_id:
        # Delete the sample from the database
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sample_bank WHERE sample_id=?", (sample_id,))
        conn.commit()
        conn.close()

        # Delete the corresponding plot file
        plot_file_path = os.path.join('app/sample_plots', f'sample_{sample_id}_with_match.png')
        if os.path.exists(plot_file_path):
            os.remove(plot_file_path)

    return redirect('/sample_history')

@app.route('/library_list', methods=['GET'])
def library_list():
    # Start timing the function execution
    start_time = time.time()
    
    # Get all comments and IDs in a single query (much faster)
    print("Getting all comments in a single query...")
    comments = get_all_comments()
    material_ids = list(comments.keys())
    total_ids = len(material_ids)
    
    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    print(f"Library list route execution time: {elapsed_time:.4f} seconds")
    
    return render_template('library_list.html', material_ids=material_ids, 
                           total_ids=total_ids, comments=comments, load_time=elapsed_time)

@app.route('/spectrum/<material_id>', methods=['GET'])
def get_spectrum(material_id):
    start_time = time.time()
    
    # Check if plot already exists
    plot_file = f'{material_id}_with_peaks.png'
    plot_path = os.path.join('app', 'plots', plot_file)
    
    # If plot doesn't exist, generate it
    if not os.path.exists(plot_path):
        intensities, wavelengths, _ = get_spectrum_data(material_id)
        
        if intensities and wavelengths:
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
    
    # Get comment using the cached function
    comment = get_comment(material_id)
    
    elapsed_time = time.time() - start_time
    print(f"Spectrum load time for {material_id}: {elapsed_time:.4f} seconds")
    
    return render_template('spectrum_detail.html', 
                          material_id=material_id, 
                          plot_file=plot_file,
                          comment=comment,
                          load_time=elapsed_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
