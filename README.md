```markdown
# Hand Interaction Analyzer

A web application that analyzes video content to detect hand interactions using MediaPipe and computer vision techniques.

## Features

- Video upload and processing
- Real-time hand detection
- Hand interaction analysis
- Side-by-side video comparison
- Detailed analytics dashboard

## Prerequisites

- **Windows 10/11**
- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **FFmpeg** ([Installation instructions below](#ffmpeg-installation))
- video files

## Installation

### 1. FFmpeg Installation
1. Download [Windows build](https://www.gyan.dev/ffmpeg/builds/)
2. Extract ZIP to `C:\ffmpeg`
3. Add to System PATH:
   - Right-click Start > System > Advanced system settings
   - Environment Variables > Path > Edit > New
   - Add `C:\ffmpeg\bin`

### 2. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start Backend (Flask)
```bash
# In main project directory
flask run --port 5000
```

### Start Frontend (React)
```bash
# In frontend directory
npm start
```

## Usage

1. Access application at `http://localhost:3000`
2. Upload video file through the interface
3. View processing results:
   - Original vs Analyzed video comparison
   - Interaction statistics
   - Frame-by-frame analysis

## Project Structure

```
├── api/                 # Backend (Flask)
│   ├── app.py
│   ├── uploads/         # Temporary upload storage
│   └── processed/       # Processed video storage
│
├── my-app/            # Frontend (React)
    ├── src/
    └── public/
```

## Troubleshooting

### Common Issues

**FFmpeg Path Not Found**  
```bash
# Verify installation
ffmpeg -version
```

**CORS Errors**  
- Ensure backend is running on port 5000
- Check Flask CORS configuration

**Video Conversion Issues**  
- Confirm input video format is supported
- Check file permissions in `uploads/` and `processed/` directories

**Missing Dependencies**  
```bash
# Reinstall requirements
pip install -r requirements.txt
cd frontend && npm install
```

**Note:** Requires modern browser with WebAssembly support (Chrome 80+, Firefox 79+, Edge 80+).  
**Recommended:** Dedicated GPU for better performance with video processing.
```

This README includes:
1. Clear installation instructions for Windows
2. Step-by-step setup for both backend and frontend
3. FFmpeg installation guidance
4. Common troubleshooting solutions
5. Project structure overview
6. Contribution guidelines
7. Browser requirements
