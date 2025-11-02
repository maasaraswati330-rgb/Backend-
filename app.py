# main.py (Final Updated Version)
import os
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/download', methods=['POST'])
def download_media():
    data = request.get_json()
    url = data.get('url')
    media_format = data.get('format', 'video')

    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        unique_id = str(uuid.uuid4())
        
        # --- YAHAN BADLAV KIYA GAYA HAI ---
        # Termux me FFmpeg ka direct path
        ffmpeg_location_path = '/data/data/com.termux/files/usr/bin/'
        
        if media_format == 'audio':
            # Audio ke liye options
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"),
                'quiet': True,
                'ffmpeg_location': ffmpeg_location_path  # FFmpeg ka path yahan set kiya
            }
            final_extension = 'mp3'
        else:
            # Video ke liye options
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"),
                'quiet': True,
                'ffmpeg_location': ffmpeg_location_path  # Yahan bhi set kar diya, safety ke liye
            }
            final_extension = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            original_path = ydl.prepare_filename(info)
            
            if media_format == 'audio':
                base_path, _ = os.path.splitext(original_path)
                final_path = f"{base_path}.{final_extension}"
            else:
                final_path = original_path

        if os.path.exists(final_path):
            return send_file(final_path, as_attachment=True)
        else:
            # Failsafe agar file nahi milti hai
            return jsonify({"error": "Processing failed. Could not locate the final file."}), 500

    except Exception as e:
        # Error ko behtar tarike se dikhane ke liye
        error_message = str(e)
        if 'ffmpeg not found' in error_message:
            error_message = "FFmpeg error. Please ensure it is correctly installed at: " + ffmpeg_location_path
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
