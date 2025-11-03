# main.py (Instaloader Version)
import os
import re
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import instaloader
import subprocess

app = Flask(__name__)
CORS(app)

# --- Environment Variables se Credentials Lena ---
INSTA_USER = os.environ.get('INSTA_USER')
INSTA_PASS = os.environ.get('INSTA_PASS')

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Instaloader ka Instance Banana ---
L = instaloader.Instaloader(
    download_videos=True,
    download_pictures=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    dirname_pattern=DOWNLOAD_FOLDER
)

# --- Login Karna (Sirf ek baar, server start hone par) ---
try:
    print("Instagram me login karne ki koshish...")
    L.login(INSTA_USER, INSTA_PASS)
    print("Login successful!")
except Exception as e:
    print(f"Login failed: {e}")


def get_shortcode_from_url(url):
    # URL se shortcode (e.g., 'DPWZawaDrul') nikalne ke liye
    match = re.search(r"/(?:p|reel)/([w-]+)", url)
    return match.group(1) if match else None

@app.route('/download', methods=['POST'])
def download_media():
    data = request.get_json()
    url = data.get('url')
    media_format = data.get('format', 'video')

    if not url:
        return jsonify({"error": "URL is required."}), 400

    shortcode = get_shortcode_from_url(url)
    if not shortcode:
        return jsonify({"error": "Invalid Instagram URL."}), 400

    try:
        print(f"Post fetch kar raha hoon: {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Video download karna
        L.download_post(post, target=f"temp_{shortcode}")
        
        # Downloaded file ka path dhoondhna
        video_path = None
        temp_dir = f"temp_{shortcode}"
        for f in os.listdir(temp_dir):
            if f.endswith('.mp4'):
                video_path = os.path.join(temp_dir, f)
                break
        
        if not video_path:
            return jsonify({"error": "Video file not found after download."}), 500
        
        # Final file jo user ko bhejenge
        final_path = video_path

        if media_format == 'audio':
            print("Audio extract kar raha hoon...")
            audio_filename = f"{str(uuid.uuid4())}.mp3"
            final_path = os.path.join(DOWNLOAD_FOLDER, audio_filename)
            
            # FFmpeg command to convert video to mp3
            command = [
                'ffmpeg', '-i', video_path,
                '-q:a', '0', '-map', 'a', final_path
            ]
            subprocess.run(command, check=True, capture_output=True)
            print("Audio extraction complete.")

        # File bhejna aur fir temporary files delete karna
        response = send_file(final_path, as_attachment=True)
        
        # Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir)
            if media_format == 'audio':
                os.remove(final_path) # Audio file ko bhi delete karein
        except Exception as e:
            print(f"Cleanup error: {e}")
            
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
