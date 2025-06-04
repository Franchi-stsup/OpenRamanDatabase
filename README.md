# OpenRamanDatabase

OpenRamanDatabase is a comprehensive Flask-based web application designed to analyze Raman spectroscopy data and automatically match samples against a database of known microplastics references. The application features an automated sample nomenclature system, advanced baseline correction algorithms, and intelligent peak matching capabilities.

![Sample Analysis Example](app/sample_plots/sample_Sample1_with_match.png)

## Table of Contents
- [Features](#features)
- [Application Architecture](#application-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Sample Nomenclature System](#sample-nomenclature-system)
- [Baseline Correction Algorithms](#baseline-correction-algorithms)
- [Database Structure](#database-structure)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Features

### Core Functionality
- **Automated Sample ID Generation**: Implements LOC-TYP-YYMMDD-SEQ nomenclature system
- **Multi-Algorithm Baseline Correction**: Polynomial fitting, rolling ball, wavelet, and derivative methods
- **Intelligent Peak Matching**: Gaussian-weighted similarity scoring with position and intensity analysis
- **Interactive Web Interface**: Modern, responsive UI with real-time sample ID preview
- **Reference Library Management**: Browse and visualize all reference spectra with detailed metadata
- **Sample History Tracking**: Two-panel interface for managing analyzed samples
- **Manual Match Override**: Allow users to manually select best matches with plot regeneration
- **Performance Monitoring**: Built-in timing and performance metrics

### Advanced Features
- **Session-Based Sequence Tracking**: Automatic sample numbering per browser session
- **Multiple File Format Support**: CSV, TXT, and other common spectroscopy formats
- **Real-Time Plot Generation**: Dynamic visualization of spectra comparisons
- **Database-Driven Architecture**: SQLite backend with optimized queries
- **Docker Containerization**: Easy deployment and environment consistency

## Application Architecture

### System Overview
```
OpenRamanDatabase/
├── Frontend (Flask Templates)
│   ├── Sample Upload Interface
│   ├── Reference Library Browser
│   ├── Sample History Manager
│   └── Spectrum Visualization
├── Backend (Flask Application)
│   ├── Route Handlers (main.py)
│   ├── Processing Engine (utils.py)
│   ├── Database Layer (SQLite)
│   └── Plot Generation (Matplotlib)
└── Data Storage
    ├── Reference Database
    ├── Sample Bank
    └── Generated Plots
```

### Component Architecture

#### 1. **Web Application Layer** (`app/main.py`)
- **Flask Routes**: Handle HTTP requests and responses
- **Session Management**: Track user sessions and sequence counters
- **File Upload Processing**: Handle multipart form data and file validation
- **Template Rendering**: Serve dynamic HTML with Jinja2 templating

#### 2. **Data Processing Engine** (`app/utils.py`)
- **Spectrum Processing**: Peak detection, baseline correction, normalization
- **Similarity Calculation**: Advanced Gaussian-weighted matching algorithms
- **Plot Generation**: Matplotlib-based visualization with peak annotations
- **Database Operations**: CRUD operations for samples and references

#### 3. **Database Layer** (`app/database/microplastics_reference.db`)
- **Reference Spectra**: Pre-calculated peak data and metadata
- **Sample Bank**: User-uploaded samples with match results
- **Performance Optimization**: Indexed queries and pre-computed values

#### 4. **Frontend Templates** (`app/templates/`)
- **Responsive Design**: Bootstrap-based modern UI
- **Real-Time Updates**: JavaScript for live sample ID preview
- **Interactive Elements**: Click-to-view functionality and search filters

### Data Flow Architecture
```
[User Upload] → [File Processing] → [Baseline Correction] → [Peak Detection] 
                                                              ↓
[Plot Generation] ← [Database Storage] ← [Similarity Matching] ← [Normalization]
        ↓
[Web Interface Display] → [Manual Override Option] → [Plot Regeneration]
```

## Prerequisites

Before installing OpenRamanDatabase, ensure you have the following prerequisites:

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Storage**: At least 2GB free space for application and data
- **Python**: Version 3.8 or higher (if running without Docker)

### Software Dependencies

#### Option 1: Docker (Recommended)
- **Docker Desktop**: Latest version from [Docker Official Site](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Usually bundled with Docker Desktop

#### Option 2: Native Python Installation
- **Python 3.8+**: From [python.org](https://www.python.org/downloads/)
- **Git**: For cloning the repository
- **Virtual Environment**: Recommended for dependency isolation

## Installation

### Docker Installation (Recommended)

1. **Install Docker Desktop**
   - **Windows/Mac**: Download from [Docker Official Site](https://www.docker.com/products/docker-desktop)
   - **Linux (Ubuntu)**:
     ```bash
     sudo apt-get update
     sudo apt-get install docker-ce docker-ce-cli containerd.io
     sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
     sudo chmod +x /usr/local/bin/docker-compose
     ```

2. **Clone and Setup**
   ```bash
   git clone https://github.com/Sailowtech/OpenRamanDatabase.git
   cd OpenRamanDatabase
   docker compose build
   docker compose up
   ```

3. **Access Application**
   - Open browser to `http://localhost:5000`
   - Application will be ready for use

### Native Python Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/Sailowtech/OpenRamanDatabase.git
   cd OpenRamanDatabase
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Application**
   ```bash
   python -m app.main
   ```

## Usage Guide

### 1. Uploading and Analyzing Samples

#### Step-by-Step Process:
1. **Navigate to Homepage**: Open `http://localhost:5000`
2. **Enter Sample Information**:
   - **Location**: Laboratory or sampling location (e.g., "LAB1", "FIELD2")
   - **Sample Type**: Type of sample (e.g., "Microplastic", "Fiber", "Particle")
   - **Live Preview**: Sample ID is generated automatically as you type
3. **Select Processing Algorithm**:
   - **Polynomial**: Best for smooth baseline variations
   - **Rolling Ball**: Ideal for complex baseline structures
   - **Wavelet**: Advanced denoising capabilities
   - **Derivative**: Simple slope-based correction
4. **Upload Spectrum File**: CSV or TXT format with wavelength and intensity columns
5. **View Results**: Automatic matching with similarity scores and visualizations

#### Expected File Formats:
```csv
Wavelength,Intensity
400.5,1250.3
401.0,1255.7
401.5,1248.9
...
```

### 2. Browse Reference Library

#### Access: Navigate to `/library_list`
- **Search Functionality**: Filter by material name or ID
- **Quick Preview**: Click any reference to view spectrum
- **Detailed Information**: Material properties and peak data
- **Performance Metrics**: Load times and database statistics

### 3. Sample History Management

#### Access: Navigate to `/sample_history`
- **Two-Panel Interface**: Sample list on left, spectrum display on right
- **Search and Filter**: Find samples by ID or characteristics
- **Click-to-View**: Interactive spectrum display
- **Sample Management**: Delete outdated or incorrect samples

### 4. Manual Match Override

#### When to Use:
- Automatic matching seems incorrect
- Domain expertise suggests different match
- Quality control and validation

#### Process:
1. From results page, click "Select Different Match"
2. Choose alternative reference from similarity rankings
3. System automatically regenerates plots
4. Updated match is saved to database

## Sample Nomenclature System

### Format: `LOC-TYP-YYMMDD-SEQ`

#### Components:
- **LOC**: Location code (user-defined, uppercase)
- **TYP**: Sample type (user-defined)
- **YYMMDD**: Date in 2-digit year, month, day format
- **SEQ**: 3-digit sequence number (000-999)

#### Examples:
- `LAB1-Microplastic-250604-001`: First microplastic sample from LAB1 on June 4, 2025
- `FIELD2-Fiber-250604-003`: Third fiber sample from FIELD2 on the same day
- `OCEAN-Particle-250605-012`: Twelfth particle sample from OCEAN on June 5, 2025

#### Key Features:
- **Session-Based Sequencing**: Counter resets per browser session
- **Automatic Generation**: No manual ID entry required
- **Collision Prevention**: Unique identifiers prevent database conflicts
- **Traceability**: Clear connection between sample origin and analysis date

## Baseline Correction Algorithms

### 1. Polynomial Fitting
**Best for**: Smooth, predictable baseline variations
```python
# Mathematical basis: Least squares polynomial fitting
baseline = np.polyval(np.polyfit(wavelengths, intensities, degree), wavelengths)
corrected = intensities - baseline
```

### 2. Rolling Ball Algorithm
**Best for**: Complex baseline structures with multiple curves
- Simulates rolling a ball under the spectrum
- Effectively removes broad background features
- Preserves sharp peaks and valleys

### 3. Wavelet-Based Correction
**Best for**: Noisy spectra requiring denoising
- Uses discrete wavelet transforms
- Separates signal from noise components
- Configurable decomposition levels

### 4. Derivative-Based Method
**Best for**: Simple linear baseline slopes
- Calculates local derivatives
- Removes linear trends
- Fastest processing option

## Database Structure

### Core Tables

#### 1. **Reference Spectra Table**
```sql
CREATE TABLE reference_spectra (
    id TEXT PRIMARY KEY,
    wavelength REAL,
    intensity REAL,
    comment TEXT
);
```

#### 2. **Reference Peaks Table** (Optimized)
```sql
CREATE TABLE reference_peaks (
    id TEXT,
    wavelength REAL,
    intensity REAL,
    FOREIGN KEY(id) REFERENCES reference_spectra(id)
);
```

#### 3. **Sample Bank Table**
```sql
CREATE TABLE sample_bank (
    sample_id TEXT,
    wavelength REAL,
    intensity REAL,
    best_match TEXT,
    similarity_score REAL
);
```

### Performance Optimizations
- **Pre-calculated Peaks**: Reference peaks stored separately for faster matching
- **Indexed Queries**: Database indexes on frequently accessed columns
- **Batch Operations**: Efficient bulk data insertion and retrieval

## API Endpoints

### Core Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET/POST | Main upload and analysis interface |
| `/library_list` | GET | Browse reference spectra library |
| `/sample_history` | GET | View and manage analyzed samples |
| `/spectrum/<id>` | GET | View individual spectrum details |
| `/save_manual_selection` | POST | Override automatic match selection |
| `/delete_sample` | POST | Remove sample from database |
| `/plots/<filename>` | GET | Serve generated plot images |

### API Response Formats

#### Sample Analysis Response
```json
{
    "sample_id": "LAB1-Microplastic-250604-001",
    "best_match": "Polyethylene Reference",
    "similarity_score": 0.847,
    "processing_time": "2.345",
    "plot_file": "sample_LAB1-Microplastic-250604-001_with_match.png"
}
```

## Development

### Setting Up Development Environment

1. **Clone and Setup**
   ```bash
   git clone https://github.com/Sailowtech/OpenRamanDatabase.git
   cd OpenRamanDatabase
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Development Mode**
   ```bash
   export FLASK_ENV=development  # Windows: set FLASK_ENV=development
   python -m app.main
   ```

### Key Development Files

- **`app/main.py`**: Flask routes and application logic
- **`app/utils.py`**: Data processing and analysis functions
- **`app/templates/`**: HTML templates with Jinja2
- **`app/static/`**: CSS, JavaScript, and static assets
- **`requirements.txt`**: Python dependencies

### Adding New Features

#### 1. New Baseline Correction Algorithm
```python
def new_algorithm_baseline(intensities, parameter):
    """Implement new baseline correction method"""
    # Add implementation
    return corrected_intensities
```

#### 2. New Similarity Metric
```python
def new_similarity_method(sample_peaks, ref_peaks):
    """Implement alternative similarity calculation"""
    # Add implementation
    return similarity_score
```

### Testing and Validation

#### Regenerate Reference Plots
```bash
python -c "from app.utils import generate_plots; generate_plots()"
```

#### Database Maintenance
```bash
# Add new references from CSV
python create_db_from_csv.py

# Remove specific reference
python delete_id_from_db.py

# Database structure modifications
python alter_db.py
```

## Troubleshooting

### Common Issues and Solutions

#### 1. **Application Won't Start**
```bash
# Check port availability
netstat -ano | findstr :5000

# Kill existing process
taskkill /PID <PID> /F

# Restart application
python -m app.main
```

#### 2. **Database Errors**
```bash
# Check database file permissions
ls -la app/database/microplastics_reference.db

# Recreate database if corrupted
python create_db_from_csv.py
```

#### 3. **Plot Generation Issues**
```bash
# Install missing matplotlib backends
pip install matplotlib

# Set matplotlib backend (in utils.py)
import matplotlib
matplotlib.use('Agg')
```

#### 4. **File Upload Problems**
- **Supported Formats**: CSV, TXT with wavelength/intensity columns
- **File Size Limit**: Default 16MB (configurable in Flask)
- **Column Headers**: Ensure proper wavelength and intensity column names

#### 5. **Performance Issues**
- **Large Datasets**: Consider pagination for sample history
- **Memory Usage**: Monitor RAM usage with large spectral files
- **Database Optimization**: Regular database maintenance and indexing

### Debug Mode
```bash
export FLASK_DEBUG=1  # Windows: set FLASK_DEBUG=1
python -m app.main
```

### Log Analysis
- Check console output for processing times
- Monitor database query performance
- Review matplotlib backend compatibility

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for low-cost Raman spectroscopy applications
- Designed for microplastics identification and analysis
- Community-driven reference database expansion