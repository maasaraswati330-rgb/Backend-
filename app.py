from flask import Flask, jsonify, request
from flask_cors import CORS
import yt_dlp
import os
import re
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
logging.basicConfig(level=logging.INFO)


# ✅ Normalize all YouTube URL types
def normalize_youtube_url(url):
    url = url.strip()

    # Short youtu.be links
    m = re.match(r'https?://(?:www\.)?youtu\.be/([^?&]+)', url)
    if m:
        video_id = m.group(1)
        return f'https://www.youtube.com/watch?v={video_id}'

    # Shorts links
    m = re.match(r'https?://(?:www\.)?youtube\.com/shorts/([^?&]+)', url)
    if m:
        video_id = m.group(1)
        return f'https://www.youtube.com/watch?v={video_id}'

    # Embed links
    m = re.match(r'https?://(?:www\.)?youtube\.com/embed/([^?&]+)', url)
    if m:
        video_id = m.group(1)
        return f'https://www.youtube.com/watch?v={video_id}'

    # If it's already a proper watch link, return as-is
    if 'youtube.com/watch?v=' in url:
        return url

    # Otherwise return original (may fail)
    return url


# ✅ Extract video + audio streams
def extract_streams(url):
    cookiefile = os.environ.get('YT_COOKIES_FILE')  # optional cookie file

    ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'format': 'bv*+ba/bestvideo+bestaudio/best',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'force_ipv4': True,
}

cookiefile = os.environ.get('YT_COOKIES_FILE')
if cookiefile and os.path.exists(cookiefile):
    import shutil, tempfile, os
    tmp_cookie = os.path.join(tempfile.gettempdir(), "cookies.txt")
    shutil.copy(cookiefile, tmp_cookie)
    ydl_opts['cookiefile'] = tmp_cookie
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Unknown Title')
        logging.info(f"Extracted info for: {title}")

        formats = info.get('formats', [])
        video_streams = []
        audio_data = None

        # ✅ Progressive streams (video + audio)
        for fmt in formats:
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                height = fmt.get('height') or 0
                filesize = fmt.get('filesize') or 0
                video_streams.append({
                    'resolution': f"{height}p",
                    'filesize': f"{filesize/(1024*1024):.1f} MB" if filesize else 'Unknown',
                    'url': fmt.get('url'),
                    'type': 'progressive'
                })

        # ✅ Audio-only stream
        for fmt in formats:
            if fmt.get('vcodec') == 'none' and fmt.get('acodec') != 'none':
                filesize = fmt.get('filesize') or 0
                audio_data = {
                    'filesize': f"{filesize/(1024*1024):.1f} MB" if filesize else 'Unknown',
                    'url': fmt.get('url'),
                    'note': 'Audio only (may need to rename to .mp3 or .m4a)'
                }
                break

        # ✅ Fallback adaptive video-only streams
        if not video_streams:
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') == 'none':
                    height = fmt.get('height') or 0
                    filesize = fmt.get('filesize') or 0
                    video_streams.append({
                        'resolution': f"{height}p (video only)",
                        'filesize': f"{filesize/(1024*1024):.1f} MB" if filesize else 'Unknown',
                        'url': fmt.get('url'),
                        'type': 'adaptive'
                    })

        # ✅ Sort by resolution (high to low)
        def get_h(res):
            m = re.search(r'(\d+)p', res)
            return int(m.group(1)) if m else 0

        video_streams.sort(key=lambda x: get_h(x['resolution']), reverse=True)

        logging.info(f"Streams found: videos={len(video_streams)}, audio={'yes' if audio_data else 'no'}")

        return {
            'title': title,
            'videoStreams': video_streams[:4],
            'audioStream': audio_data
        }


# ✅ Endpoint: /streams?url=YOUTUBE_URL
@app.route('/streams', methods=['GET', 'OPTIONS'])
def get_streams():
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }

    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL parameter required: ?url=...'}), 400

    url = normalize_youtube_url(url)

    if not re.search(r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)', url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        data = extract_streams(url)
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /streams: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ✅ Home route
@app.route('/')
def home():
    return jsonify({
        'status': '✅ Backend Live',
        'usage': '/streams?url=YOUTUBE_URL'
    }), 200


# ✅ Run app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
