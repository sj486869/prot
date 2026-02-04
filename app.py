from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
import json, os, threading, time

# --- CONFIGURATION ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(ROOT, 'data', 'data.json')
MSG_FILE = os.path.join(ROOT, 'data', 'messages.json')
UPLOAD_DIR = os.path.join(ROOT, 'uploads')
LOCK = threading.Lock()

app = Flask(__name__)
CORS(app)

# --- UTILITIES ---
def read_json(path):
    """Safely read JSON file, returns content or None if missing/corrupt."""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return None

def write_json(path, data):
    """Safely write JSON file using a temp file to prevent corruption."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"Error writing JSON: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)

# --- MAIN DATA ENDPOINTS ---

@app.route('/api/data', methods=['GET'])
def get_data():
    data = read_json(DATA_FILE)
    if not isinstance(data, dict):
        data = {}
    return jsonify(data)

@app.route('/api/item', methods=['POST'])
def add_or_update_item():
    body = request.get_json() or {}
    section = body.get('section')
    payload = body.get('payload') or {}
    
    if not section or not isinstance(payload, dict):
        return jsonify({'error': 'bad request'}), 400

    with LOCK:
        data = read_json(DATA_FILE)
        if not isinstance(data, dict): 
            data = {}
            
        arr = data.get(section)
        if not isinstance(arr, list):
            arr = []

        # Update if ID exists, else Add
        if payload.get('id'):
            found = False
            for i, it in enumerate(arr):
                # Compare IDs safely as integers
                if int(it.get('id', 0)) == int(payload['id']):
                    arr[i].update(payload)
                    found = True
                    break
            if not found:
                arr.append(payload)
        else:
            # Generate new ID
            maxid = max([int(it.get('id', 0)) for it in arr], default=0)
            payload['id'] = maxid + 1
            arr.append(payload)

        data[section] = arr
        write_json(DATA_FILE, data)

    return jsonify({'ok': True, 'id': payload.get('id')})

@app.route('/api/delete', methods=['POST'])
def delete_item():
    body = request.get_json() or {}
    section = body.get('section')
    id_val = body.get('id')
    
    if not section or id_val is None:
        return jsonify({'error': 'bad request'}), 400

    with LOCK:
        data = read_json(DATA_FILE)
        if not isinstance(data, dict):
            data = {}
            
        arr = data.get(section)
        if isinstance(arr, list):
            # Filter out the item
            arr = [it for it in arr if int(it.get('id', 0)) != int(id_val)]
            data[section] = arr
            write_json(DATA_FILE, data)

    return jsonify({'ok': True})

# --- MESSAGES ENDPOINTS ---

@app.route('/api/messages', methods=['GET'])
def get_messages():
    msgs = read_json(MSG_FILE)
    # Ensure it's a list
    if not isinstance(msgs, list):
        msgs = []
    # Sort by newest first (optional)
    msgs.sort(key=lambda x: x.get('created', 0), reverse=True)
    return jsonify(msgs)

@app.route('/api/message', methods=['POST'])
def post_message():
    body = request.get_json() or {}
    name = body.get('name')
    email = body.get('email')
    message = body.get('message')
    
    if not (name and email and message):
        return jsonify({'error': 'missing fields'}), 400

    entry = {
        'id': int(time.time() * 1000),
        'name': name,
        'email': email,
        'message': message,
        'created': int(time.time() * 1000)
    }
    
    with LOCK:
        msgs = read_json(MSG_FILE)
        if not isinstance(msgs, list):
            msgs = []
        msgs.insert(0, entry)
        write_json(MSG_FILE, msgs)

    return jsonify({'ok': True})

@app.route('/api/message/delete', methods=['POST'])
def delete_message():
    body = request.get_json() or {}
    mid = body.get('id')
    
    if mid is None:
        return jsonify({'error': 'id required'}), 400

    with LOCK:
        msgs = read_json(MSG_FILE)
        if not isinstance(msgs, list):
            msgs = []
        
        # Remove message with matching ID
        initial_count = len(msgs)
        msgs = [m for m in msgs if int(m.get('id', 0)) != int(mid)]
        
        if len(msgs) != initial_count:
            write_json(MSG_FILE, msgs)

    return jsonify({'ok': True})

# --- FILE UPLOAD ---

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'no filename'}), 400
        
    filename = secure_filename(f.filename)
    dest = os.path.join(UPLOAD_DIR, filename)
    f.save(dest)
    
    url = '/uploads/' + filename
    return jsonify({'ok': True, 'url': url})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# --- STATIC FILES ---

@app.route('/admin')
def serve_admin():
    return send_from_directory(ROOT, 'admin.html')

@app.route('/admin.html')
def serve_admin_html():
    return send_from_directory(ROOT, 'admin.html')

@app.route('/')
@app.route('/index.html')
def serve_index():
    return send_from_directory(ROOT, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(ROOT, path)):
        return send_from_directory(ROOT, path)
    return send_from_directory(ROOT, 'index.html')

# --- STARTUP ---

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Initialize JSON files if missing
    if not os.path.exists(DATA_FILE):
        write_json(DATA_FILE, {})
    if not os.path.exists(MSG_FILE):
        write_json(MSG_FILE, [])
        
    app.run(host='0.0.0.0', port=5000, debug=True)