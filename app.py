import os
import cv2
import uuid
import subprocess
import logging
import mimetypes
import absl.logging
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mediapipe as mp

# Suppress unnecessary warnings
absl.logging.set_verbosity(absl.logging.ERROR)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Disable TensorFlow logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Initialize MediaPipe Hands model
mp_hands = mp.solutions.hands
hands_model = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5,
    model_complexity=0
)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union != 0 else 0

def process_video(input_path, file_id):
    temp_output = os.path.join(app.config['PROCESSED_FOLDER'], f"temp_{file_id}.avi")
    final_output = os.path.join(app.config['PROCESSED_FOLDER'], f"final_{file_id}.mp4")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {input_path}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (frame_width, frame_height))
    if not out.isOpened():
        raise RuntimeError("Failed to initialize VideoWriter")

    analysis_data = {
        'total_frames': 0,
        'intersection_frames': 0,
        'max_hands_detected': 0
    }

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands_model.process(rgb_frame)
            hand_boxes = []

            if results.multi_hand_landmarks:
                current_hands = len(results.multi_hand_landmarks)
                analysis_data['max_hands_detected'] = max(
                    analysis_data['max_hands_detected'],
                    current_hands
                )

                for hand in results.multi_hand_landmarks:
                    x_coords = [lm.x * frame_width for lm in hand.landmark]
                    y_coords = [lm.y * frame_height for lm in hand.landmark]
                    min_x, max_x = int(min(x_coords)), int(max(x_coords))
                    min_y, max_y = int(min(y_coords)), int(max(y_coords))
                    hand_boxes.append((min_x, min_y, max_x, max_y))

                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand, mp_hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                        mp.solutions.drawing_styles.get_default_hand_connections_style()
                    )
                    cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (0, 255, 0), 2)

                if len(hand_boxes) >= 2:
                    iou = calculate_iou(hand_boxes[0], hand_boxes[1])
                    if iou > 0.05:
                        analysis_data['intersection_frames'] += 1
                        ix1 = max(hand_boxes[0][0], hand_boxes[1][0])
                        iy1 = max(hand_boxes[0][1], hand_boxes[1][1])
                        ix2 = min(hand_boxes[0][2], hand_boxes[1][2])
                        iy2 = min(hand_boxes[0][3], hand_boxes[1][3])
                        cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (255, 0, 0), 3)
                        cv2.putText(frame, "HANDS INTERSECTING", (50, 80),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            out.write(frame)
            analysis_data['total_frames'] += 1

    finally:
        cap.release()
        out.release()

    try:
        ffmpeg_command = [
            'ffmpeg', '-y', '-i', temp_output,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-preset', 'fast',
            '-movflags', '+faststart',
            '-an', final_output
        ]
        subprocess.run(ffmpeg_command, check=True, shell=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg conversion failed: {e.stderr.decode()}") from e
    finally:
        if os.path.exists(temp_output):
            os.remove(temp_output)

    return final_output, analysis_data

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    mimetype, _ = mimetypes.guess_type(filename)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        mimetype=mimetype
    )

@app.route('/processed/<filename>')
def processed_file(filename):
    response = send_from_directory(
        app.config['PROCESSED_FOLDER'],
        filename,
        mimetype='video/mp4'
    )
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400

    file_id = uuid.uuid4().hex
    safe_filename = secure_filename(file.filename)
    input_filename = f"{file_id}_{safe_filename}"
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
    
    try:
        # Save original file
        file.save(input_path)

        web_original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"web_{file_id}.mp4")
        conv_command = [
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'fast',
            '-movflags', '+faststart',
            web_original_path
        ]
        subprocess.run(conv_command, check=True, shell=True, stderr=subprocess.PIPE)

        # Now process using the WEB-READY original
        processed_path, analysis = process_video(web_original_path, file_id)

        # Process video
        return jsonify({
        'original': f'/uploads/web_{file_id}.mp4',  # Serve CONVERTED original
        'processed': f'/processed/{os.path.basename(processed_path)}',
        'analysis': analysis
            })

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        return jsonify({'error': 'Video conversion failed'}), 500
    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
        return jsonify({'error': 'Video processing failed'}), 500
    finally:
        # ONLY clean up temporary files, keep web-ready original
        paths_to_clean = [input_path]  # Don't delete web_original_path
        for path in paths_to_clean:
            if path and os.path.exists(path):
                try: os.remove(path)
                except: pass
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000)