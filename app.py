# main.py (Final, Corrected, and Secure Version)
import os
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

# --- Environment Variables se Instagram Credentials Lena ---
# Yeh details Render ke "Environment" section me set hongi
INSTA_USER = os.environ.get('INSTA_USER')
INSTA_PASS = os.environ.get('INSTA_PASS')

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
        
        # --- Yahan Sahi Code Hai ---
        # Common options jo dono format ke liye use honge
        common_opts = {
            'quiet': True,
            'username': INSTA_USER,
            'password': INSTA_PASS,
        }
        
        if media_format == 'audio':
            # Audio ke liye specific options
            ydl_opts = {
                **common_opts, # Common options yahan aa gaye
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"),
            }
            final_extension = 'mp3'
        else: # 'video' ke liye
            # Video ke liye specific options
            ydl_opts = {
                **common_opts, # Common options yahan aa gaye
                'format': 'best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"),
            }
            final_extension = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Login karne ki koshish karega
            ydl.extract_info(url, download=True) 
            info = ydl.extract_info(url, download=False) # Info dobara nikalte hain filename ke liye
            
            # Filename set karte hain
            original_path = ydl.prepare_filename(info)
            
            if media_format == 'audio':
                base_path, _ = os.path.splitext(original_path)
                final_path = f"{base_path}.{final_extension}"
            else:
                final_path = original_path

        if os.path.exists(final_path):
            return send_file(final_path, as_attachment=True, download_name=os.path.basename(final_path))
        else:
            return jsonify({"error": "Processing failed. Could not locate the final file."}), 500

    except Exception as e:
        error_message = str(e)
        if 'login required' in error_message.lower():
            return jsonify({"error": "Authentication failed on server. Please check credentials."}), 401
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    # Gunicorn isko run karega
    app.run()
