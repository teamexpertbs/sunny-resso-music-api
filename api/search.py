from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import json
import base64
import html
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

DES_KEY = b'38346591'

def decrypt_saavn_url(encrypted_url):
    try:
        cipher = Cipher(algorithms.TripleDES(DES_KEY * 3), modes.ECB())
        decryptor = cipher.decryptor()
        raw_bytes = base64.b64decode(encrypted_url)
        decrypted = decryptor.update(raw_bytes) + decryptor.finalize()
        unpadder = padding.PKCS7(64).unpadder()
        unpadded = unpadder.update(decrypted) + unpadder.finalize()
        stream_url = unpadded.decode('utf-8')
        return stream_url.replace('_96.mp4', '_320.mp4').replace('_160.mp4', '_320.mp4')
    except Exception as e:
        return None

def search_jiosaavn(query):
    encoded_q = urllib.parse.quote(query)
    api_url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&_format=json&_marker=0&cc=in&n=20&p=1&q={encoded_q}"
    req = urllib.request.Request(api_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read().decode('utf-8', errors='ignore')
        data = json.loads(content)
        
    songs = []
    for item in data.get('results', []):
        enc_url = item.get('encrypted_media_url')
        if not enc_url:
            continue
        audio_url = decrypt_saavn_url(enc_url)
        if not audio_url:
            continue
        
        raw_title = item.get('song', '')
        raw_singers = item.get('primary_artists') or item.get('singers') or 'Various Artists'
        raw_album = item.get('album', '')
        img = item.get('image', '').replace('150x150.jpg', '500x500.jpg')
        duration_sec = int(item.get('duration', 0))
        
        songs.append({
            'id': item.get('id'),
            'title': html.unescape(raw_title),
            'artist': html.unescape(raw_singers),
            'album': html.unescape(raw_album),
            'duration': duration_sec,
            'durationFormatted': f"{duration_sec // 60}:{duration_sec % 60:02d}",
            'albumArt': img,
            'audioUrl': audio_url,
            'year': item.get('year', '')
        })
    return songs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get('q', [''])[0].strip()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Cache-Control', 'public, s-maxage=86400, stale-while-revalidate=43200')
        self.end_headers()
        
        if not query:
            self.wfile.write(json.dumps({'success': False, 'error': 'Query q is required'}).encode('utf-8'))
            return
            
        try:
            results = search_jiosaavn(query)
            res = {
                'success': True,
                'query': query,
                'count': len(results),
                'results': results
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
