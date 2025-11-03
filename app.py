# main.py (Final Corrected Instaloader Version)
import os
import re
import uuid
import shutil
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
    compress_json=False
)

# --- Login Karna ---
try:
    print(f"Instagram me '{INSTA_USER}' se login karne ki koshish...")
    L.login(INSTA_USER, INSTA_PASS)
    print("Login successful!")
except Exception as e:
    print(f"Login fail ho gaya: {e}")


def get_shortcode_from_url(url):
    """
    Ek behtar tareeka URL se shortcode nikalne ka.
    Yeh /p/, /reel/, aur ?igshid=... jaise sabhi links ke liye kaam karega.
    """
    pattern = r"(?:https?://)?(?:www.)?instagram.com/(?:p|reel)/([w-]+)"
    match = re.search(pattern, url)
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
        return jsonify({"error": "Invalid Instagram URL format."}), 400

    temp_dir = os.path.join(DOWNLOAD_FOLDER, f"temp_{shortcode}_{str(uuid.uuid4())[:8]}")

    try:
        print(f"Post fetch kar raha hoon: {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Post ko ek temporary directory me download karna
        L.download_post(post, target=temp_dir)
        
        video_path = None
        for f in os.listdir(temp_dir):
            if f.endswith('.mp4'):
                video_path = os.path.join(temp_dir, f)
                break
        
        if not video_path:
            return jsonify({"error": "Video file not found after download."}), 500
        
        final_path = video_path

        if media_format == 'audio':
            print("Audio extract kar raha hoon...")
            audio_filename = f"{shortcode}.mp3"
            final_path = os.path.join(DOWNLOAD_FOLDER, audio_filename)
            
            command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', final_path]
            subprocess.run(command, check=True, capture_output=True)
            print("Audio extraction complete.")

        return send_file(final_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Hamesha temporary files ko delete karna
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Temporary directory '{temp_dir}' delete kar di gayi.")
            except Exception as e:
                print(f"Cleanup error: {e}")

if __name__ == '__main__':
    app.run()
