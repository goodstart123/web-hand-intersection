import React, { useState, useRef } from 'react';
import './App.css';

function App() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setError(null);
    setLoading(true);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Video processing failed');
      }

      const data = await response.json();
      setResults({
        ...data,
        // Add cache busting to both videos
        original: `${data.original}?t=${Date.now()}`,
        processed: `${data.processed}?t=${Date.now()}`
      });

      // Auto-play video when available
      if (videoRef.current) {
        videoRef.current.load();
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>Hand Interaction Analyzer</h1>
      
      <div className="upload-section">
        <label className="upload-button">
          Upload Video
          <input 
            type="file" 
            accept="video/mp4,video/x-m4v,video/*"
            onChange={handleUpload}
            disabled={loading}
            hidden
          />
        </label>
        <p className="format-info">
          Supported formats: MP4, MOV, AVI, MKV, WEBM (max 500MB)
        </p>
      </div>

      {loading && (
        <div className="status-box loading">
          <div className="spinner"></div>
          <p>Processing video...</p>
        </div>
      )}

      {error && (
        <div className="status-box error">
          <p>⚠️ Error: {error}</p>
        </div>
      )}

      {results && (
        <div className="results-container">
          <div className="video-comparison">
            <div className="video-wrapper">
              <h2>Original Video</h2>
              <video 
                controls 
                key={results.original}
                onError={(e) => console.error('Original video error:', e.target.error)}
              >
                <source 
                  src={`http://localhost:5000${results.original}`}  // Added full backend URL
                  type="video/mp4" 
                />
                Your browser does not support the video tag.
              </video>
            </div>
            
            <div className="video-wrapper">
              <h2>Analyzed Video</h2>
              <video 
                ref={videoRef}
                controls 
                key={results.processed}
                onError={(e) => {
                  console.error('Processed video error:', e.target.error);
                  setError('Failed to load processed video');
                }}
                onLoadedData={() => videoRef.current?.play()}
              >
                <source 
                  src={`http://localhost:5000${results.processed}`}
                  type="video/mp4; codecs=avc1" 
                />
                Your browser does not support HTML5 video.
              </video>
            </div>
          </div>

          <div className="analysis-summary">
            <h2>Analysis Results</h2>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">Total Frames Processed:</span>
                <span className="metric-value">
                  {results.analysis.total_frames.toLocaleString()}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Hand Intersections Detected:</span>
                <span className="metric-value">
                  {results.analysis.intersection_frames.toLocaleString()}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Maximum Hands Visible:</span>
                <span className="metric-value">
                  {results.analysis.max_hands_detected}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;