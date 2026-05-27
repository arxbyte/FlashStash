import os
import shutil
import socket
from flask import Flask, render_template_string, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vdm_flash_stash_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

UPLOAD_DIR = "shared_files"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

file_passwords = {}
history_text = []


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


def get_files_info():
    files_list = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(path):
                size = round(os.path.getsize(path) / (1024 * 1024), 2)
                has_pass = filename in file_passwords and bool(file_passwords[filename])
                
                ext_raw = os.path.splitext(filename)[1].lower().replace('.', '')
                ext_upper = ext_raw.upper() if ext_raw else "FILE"
                is_image = ext_raw in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']
                
                files_list.append({
                    "name": filename, 
                    "size": size, 
                    "protected": has_pass,
                    "is_image": is_image,
                    "ext": ext_upper
                })
    files_list.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x['name'])), reverse=True)
    return files_list


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flash Stash</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Kelly+Slab&display=swap" rel="stylesheet">

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <style>
        :root {
            --bg: #000000;
            --surface: #0a0f0d;
            --surface-card: #0d1410;
            --border: #1f3a2b;
            --accent: #00ff66;
            --accent-dim: #00993d;
            --danger: #ff3333;
            --danger-dim: #b32424;
            --text: #cdffd8;
            --text-muted: #529969;
            --warning: #e67e22;
        }

        body {
            font-family: 'Kelly Slab', monospace;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 16px;
            display: flex;
            justify-content: center;
            min-height: 100vh;
            -webkit-tap-highlight-color: transparent;
            font-size: 0.9rem; /* Чуть увеличили, так как шрифт стал более компактным */
            line-height: 1.4;
            letter-spacing: 0.5px;
        }

        .container {
            width: 100%;
            max-width: 1200px;
        }

        header {
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .terminal-title {
            font-family: 'Kelly Slab', monospace;
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent);
            text-shadow: 0 0 8px rgba(0, 255, 102, 0.2);
        }

        .sys-stats {
            font-size: 0.8rem;
            color: var(--text-muted);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 2px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
            align-items: stretch;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
        }

        h2 {
            margin: 0;
            font-size: 1.1rem;
            text-transform: uppercase;
            color: var(--accent);
        }

        .input-zone {
            height: 145px; 
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            margin-bottom: 15px;
        }

        textarea {
            width: 100%;
            height: 90px;
            background: #040705;
            border: 1px solid var(--border);
            color: var(--accent);
            border-radius: 2px;
            padding: 10px;
            box-sizing: border-box;
            resize: none;
            font-size: 0.85rem;
            outline: none;
            font-family: 'Kelly Slab', monospace;
            line-height: 1.4;
        }

        textarea:focus {
            border-color: var(--accent);
        }

        .input-flat {
            background: #040705;
            border: 1px solid var(--border);
            color: var(--accent);
            border-radius: 2px;
            padding: 10px;
            font-size: 0.85rem;
            outline: none;
            font-family: 'Kelly Slab', monospace;
            width: 100%;
            box-sizing: border-box;
        }
        .input-flat:focus {
            border-color: var(--accent);
        }

        .mask-password {
            -webkit-text-security: disc !important;
            text-security: disc !important;
        }

        .btn {
            background: transparent;
            color: var(--accent);
            border: 1px solid var(--accent);
            padding: 10px;
            border-radius: 2px;
            font-weight: bold;
            font-size: 0.85rem;
            cursor: pointer;
            font-family: 'Kelly Slab', monospace;
            transition: all 0.15s ease;
            box-sizing: border-box;
            width: 100%;
        }

        .btn:hover { 
            background: rgba(0, 255, 102, 0.05);
        }

        .btn-clear {
            background: transparent;
            color: var(--danger-dim);
            border: 1px solid rgba(255, 51, 51, 0.3);
            padding: 4px 8px;
            font-size: 0.7rem;
            cursor: pointer;
            font-family: 'Kelly Slab', monospace;
            transition: all 0.15s ease;
        }
        .btn-clear:hover {
            color: var(--danger);
            border-color: var(--danger);
            background: rgba(255, 51, 51, 0.05);
        }

        .list-container {
            min-height: 380px;
            max-height: 380px;
            overflow-y: auto;
            border-top: 1px solid var(--border);
            padding-top: 10px;
        }

        .list-container::-webkit-scrollbar { width: 4px; }
        .list-container::-webkit-scrollbar-thumb { background: var(--border); }

        .item-box {
            background: var(--surface-card);
            border: 1px solid var(--border);
            padding: 12px;
            position: relative;
            margin-bottom: 12px;
            border-radius: 2px;
        }

        .item-text {
            white-space: pre-wrap;
            word-break: break-all;
            font-size: 0.8rem;
            margin-bottom: 25px;
            color: var(--text);
        }

        .item-actions {
            position: absolute;
            bottom: 6px;
            right: 6px;
            display: flex;
            gap: 6px;
        }

        .btn-action {
            background: #040705;
            border: 1px solid var(--border);
            color: var(--text-muted);
            cursor: pointer;
            font-family: 'Kelly Slab', monospace;
            padding: 4px 8px;
            font-size: 0.7rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            text-decoration: none;
        }

        .btn-action:hover { 
            color: var(--accent);
            border-color: var(--accent);
        }

        .btn-delete {
            color: var(--danger-dim) !important;
            border-color: rgba(255, 51, 51, 0.3) !important;
        }
        .btn-delete:hover {
            color: var(--danger) !important;
            border-color: var(--danger) !important;
            background: rgba(255, 51, 51, 0.05) !important;
        }

        .modal-backdrop {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(5px);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }

        .modal-content {
            background: var(--surface);
            border: 2px solid var(--border);
            border-radius: 4px;
            padding: 20px;
            width: 90%;
            max-width: 420px;
            box-shadow: 0 0 20px rgba(0, 255, 102, 0.1);
            box-sizing: border-box;
        }

        .modal-content h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--accent);
            text-transform: uppercase;
            font-size: 0.95rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }

        .modal-buttons {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 15px;
        }

        .modal-error {
            color: var(--danger);
            font-size: 0.75rem;
            margin-top: 8px;
            display: none;
        }

        .qr-content-box {
            background: #ffffff;
            padding: 10px;
            border-radius: 2px;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto;
            width: 220px;
            height: 220px;
        }

        #qrCodeTarget canvas, #qrCodeTarget img {
            width: 220px !important;
            height: 220px !important;
            display: block;
        }

        .image-preview-content {
            max-width: 80vw;
            max-height: 80vh;
            background: var(--surface);
            border: 2px solid var(--border);
            padding: 10px;
            border-radius: 4px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .image-preview-content img {
            max-width: 100%;
            max-height: 70vh;
            object-fit: contain;
            border: 1px solid var(--border);
        }

        .image-preview-title {
            margin-top: 8px;
            font-size: 0.75rem;
            color: var(--text-muted);
            word-break: break-all;
            text-align: center;
        }

        .file-list { list-style: none; padding: 0; margin: 0; }

        .file-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--surface-card);
            border: 1px solid var(--border);
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 2px;
            gap: 12px;
        }

        .file-preview {
            width: 42px;
            height: 42px;
            min-width: 42px;
            background: #040705;
            border: 1px solid var(--border);
            border-radius: 2px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.65rem;
            color: var(--text-muted);
            overflow: hidden;
            user-select: none;
            text-align: center;
            font-weight: bold;
        }

        .file-preview.clickable {
            cursor: pointer;
        }
        .file-preview.clickable:hover {
            border-color: var(--accent);
        }

        .file-preview img {
            object-fit: cover;
            width: 100%;
            height: 100%;
        }

        .file-preview.is-locked {
            color: var(--warning);
            border-color: rgba(230, 126, 34, 0.4);
            font-size: 0.6rem;
            cursor: pointer;
        }

        .file-info-block {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-grow: 1;
            max-width: calc(100% - 160px);
        }

        .file-info { word-break: break-all; width: 100%; }
        .file-name { font-size: 0.75rem; color: var(--text); }
        .file-lock-badge { font-size: 0.7rem; color: var(--warning); margin-left: 5px; }
        .file-size { font-size: 0.65rem; color: var(--text-muted); margin-top: 4px; }

        .file-actions {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }

        input[type="file"] { display: none; }
        .file-label {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #040705;
            border: 1px dashed var(--border);
            height: 90px;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 0.75rem;
            border-radius: 2px;
            box-sizing: border-box;
            text-align: center;
            padding: 10px;
        }
        .file-label:hover { 
            border-color: var(--accent); 
            color: var(--accent);
        }

        .status-text { font-size: 0.7rem; color: var(--accent); text-align: center; margin-top: 5px; display: none;}
    </style>
</head>
<body>

    <div class="modal-backdrop" id="qrModal" onclick="closeQRModal()">
        <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 280px; padding: 16px;">
            <div class="qr-content-box">
                <div id="qrCodeTarget"></div>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="imagePreviewModal" onclick="closeImageModal()">
        <div class="image-preview-content" onclick="event.stopPropagation()">
            <img id="modal-preview-img" src="" alt="Full Preview">
            <div class="image-preview-title" id="modal-preview-title"></div>
        </div>
    </div>

    <div class="modal-backdrop" id="passwordModal" onclick="closePasswordModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3 id="passModalTitle">ENTER PASSWORD</h3>
            <div style="color: var(--text-muted); font-size: 0.75rem; margin-bottom: 10px;" id="passModalSubtitle">This file is encrypted.</div>
            <input type="text" id="modal-password-input" class="input-flat mask-password" placeholder="Password..." autocomplete="off">
            <div id="modal-password-error" class="modal-error">[ERROR: INVALID PASSWORD]</div>
            <div class="modal-buttons">
                <button class="btn" style="width: auto; padding: 6px 12px;" onclick="closePasswordModal()">[CANCEL]</button>
                <button class="btn" style="width: auto; padding: 6px 12px;" id="modal-password-submit">[SUBMIT]</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="confirmModal">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3>CONFIRM ACTION</h3>
            <div style="color: var(--text); font-size: 0.8rem; margin-bottom: 15px;" id="confirmModalMessage">Are you sure?</div>
            <div class="modal-buttons">
                <button class="btn" style="width: auto; padding: 6px 12px; border-color: var(--text-muted); color: var(--text-muted);" id="confirm-modal-cancel">[CANCEL]</button>
                <button class="btn" style="width: auto; padding: 6px 12px; border-color: var(--danger); color: var(--danger);" id="confirm-modal-submit">[PROCEED]</button>
            </div>
        </div>
    </div>

    <div class="container">
        <header>
            <div class="terminal-title">Flash Stash</div>
            <div class="sys-stats" id="disk-indicator">
                LOCAL_IP: {{ local_ip }}
            </div>
        </header>

        <div class="grid">
            <div class="panel">
                <div class="panel-header">
                    <h2>Text & Links</h2>
                    <button class="btn-clear" onclick="clearAllText()">Clear all</button>
                </div>
                
                <div class="input-zone">
                    <textarea id="text-input" placeholder="Type text or paste link here... (Ctrl+Enter to send)"></textarea>
                    <button onclick="sendText()" class="btn">Send to buffer</button>
                </div>

                <div class="list-container" id="history-box">
                    {% for item in history|reverse %}
                    <div class="item-box" data-index="{{ loop.revindex0 }}">
                        <div class="item-text">{{ item }}</div>
                        <div class="item-actions">
                            <button class="btn-action" onclick="showTextQR(`{{ item|replace('`','\\\\`') }}`)">[QR]</button>
                            <button class="btn-action" onclick="copyText(this)">[COPY]</button>
                            <button class="btn-action btn-delete" onclick="deleteText({{ loop.revindex0 }})">[RM]</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <h2>File Storage</h2>
                    <button class="btn-clear" onclick="clearAllFiles()">Delete all files</button>
                </div>
                
                <div class="input-zone">
                    <label class="file-label">
                        <span>Click to browse or drop files here</span>
                        <input type="file" id="file-input" multiple onchange="uploadFiles()">
                    </label>
                    <input type="text" id="file-password" class="input-flat mask-password" placeholder="Set file password (optional)..." autocomplete="off">
                </div>

                <div id="upload-status" class="status-text">Uploading...</div>

                <div class="list-container">
                    <ul class="file-list" id="files-box">
                        {% for file in files %}
                        <li class="file-row">
                            <div class="file-info-block">
                                <div id="preview-wrapper-{{ file.name|replace('.', '_') }}">
                                    {% if file.protected %}
                                        <div class="file-preview is-locked" onclick="unlockPreview('{{ file.name|replace("'","\\\\'") }}')">[LOCK]</div>
                                    {% elif file.is_image %}
                                        <div class="file-preview clickable" onclick="openImageModal('/download/{{ file.name }}', '{{ file.name|replace("'","\\\\'") }}')">
                                            <img src="/download/{{ file.name }}" alt="thumb">
                                        </div>
                                    {% else %}
                                        <div class="file-preview">{{ file.ext }}</div>
                                    {% endif %}
                                </div>
                                
                                <div class="file-info">
                                    <div class="file-name">
                                        {{ file.name }}
                                        {% if file.protected %}<span class="file-lock-badge" id="lock-badge-{{ file.name|replace('.', '_') }}">[LOCKED]</span>{% endif %}
                                    </div>
                                    <div class="file-size">{{ file.size }} MB</div>
                                </div>
                            </div>
                            <div class="file-actions">
                                <button class="btn-action" onclick="handleFileQRClick('{{ file.name|replace("'","\\\\'") }}', {{ 'true' if file.protected else 'false' }})">[QR]</button>
                                <button class="btn-action" onclick="handleFileGetClick('{{ file.name|replace("'","\\\\'") }}', {{ 'true' if file.protected else 'false' }})">[GET]</button>
                                <button class="btn-action btn-delete" onclick="deleteFile('{{ file.name }}')">[RM]</button>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        const qrModal = document.getElementById('qrModal');
        const passModal = document.getElementById('passwordModal');
        const confirmModal = document.getElementById('confirmModal');
        const imgModal = document.getElementById('imagePreviewModal');
        const qrTarget = document.getElementById('qrCodeTarget');

        let passModalCallback = null;

        function getSavedPassword(filename) {
            return sessionStorage.getItem('pass_' + filename) || '';
        }

        function savePassword(filename, password) {
            sessionStorage.setItem('pass_' + filename, password);
        }

        function getDownloadBaseUrl(filename, password = '') {
            const base = window.location.protocol + "//" + window.location.host + "/download/" + encodeURIComponent(filename);
            const activePass = password || getSavedPassword(filename);
            return activePass ? base + "?pass=" + encodeURIComponent(activePass) : base;
        }

        function openConfirmModal(message, onConfirm) {
            document.getElementById('confirmModalMessage').innerText = message;
            confirmModal.style.display = 'flex';
            const cancelBtn = document.getElementById('confirm-modal-cancel');
            const submitBtn = document.getElementById('confirm-modal-submit');
            const clearEvents = () => { submitBtn.onclick = null; cancelBtn.onclick = null; };
            submitBtn.onclick = () => { clearEvents(); confirmModal.style.display = 'none'; onConfirm(); };
            cancelBtn.onclick = () => { clearEvents(); confirmModal.style.display = 'none'; };
        }

        function openQRModal(payloadString) {
            qrTarget.innerHTML = ''; 
            qrModal.style.display = 'flex'; 
            new QRCode(qrTarget, {
                text: payloadString,
                width: 220,  
                height: 220,
                colorDark : "#000000",
                colorLight : "#ffffff"
            });
        }

        function closeQRModal() { qrModal.style.display = 'none'; }
        function showTextQR(text) { openQRModal(text); }

        function openImageModal(src, title) {
            document.getElementById('modal-preview-img').src = src;
            document.getElementById('modal-preview-title').innerText = title;
            imgModal.style.display = 'flex';
        }

        function closeImageModal() { imgModal.style.display = 'none'; }

        function openPasswordModal(title, subtitle, onSubmit) {
            document.getElementById('passModalTitle').innerText = title;
            document.getElementById('passModalSubtitle').innerText = subtitle;
            document.getElementById('modal-password-input').value = '';
            document.getElementById('modal-password-error').style.display = 'none';
            passModal.style.display = 'flex';
            document.getElementById('modal-password-input').focus();
            passModalCallback = onSubmit;
        }

        function closePasswordModal() {
            passModal.style.display = 'none';
            passModalCallback = null;
        }

        document.getElementById('modal-password-submit').addEventListener('click', () => {
            const passValue = document.getElementById('modal-password-input').value;
            if (passModalCallback) passModalCallback(passValue);
        });

        document.getElementById('modal-password-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('modal-password-submit').click();
        });

        function unlockPreview(filename) {
            openPasswordModal("UNLOCK PREVIEW", "Enter password to view preview:", (password) => {
                fetch(`/check_pass?filename=${encodeURIComponent(filename)}&pass=${encodeURIComponent(password)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.valid) {
                        savePassword(filename, password);
                        closePasswordModal();
                        socket.emit('request_files_refresh'); 
                    } else {
                        document.getElementById('modal-password-error').style.display = 'block';
                    }
                });
            });
        }

        function handleFileQRClick(filename, isProtected) {
            const savedPass = getSavedPassword(filename);
            if (isProtected && !savedPass) {
                openPasswordModal("GENERATE SECURE QR", "Enter password:", (password) => {
                    fetch(`/check_pass?filename=${encodeURIComponent(filename)}&pass=${encodeURIComponent(password)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.valid) {
                            savePassword(filename, password);
                            closePasswordModal();
                            openQRModal(getDownloadBaseUrl(filename, password));
                            socket.emit('request_files_refresh');
                        } else {
                            document.getElementById('modal-password-error').style.display = 'block';
                        }
                    });
                });
            } else {
                openQRModal(getDownloadBaseUrl(filename));
            }
        }

        function handleFileGetClick(filename, isProtected) {
            const savedPass = getSavedPassword(filename);
            if (isProtected && !savedPass) {
                openPasswordModal("DOWNLOAD SECURE FILE", "Verification required.", (password) => {
                    fetch(`/check_pass?filename=${encodeURIComponent(filename)}&pass=${encodeURIComponent(password)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.valid) {
                            savePassword(filename, password);
                            closePasswordModal();
                            window.location.href = getDownloadBaseUrl(filename, password);
                            socket.emit('request_files_refresh');
                        } else {
                            document.getElementById('modal-password-error').style.display = 'block';
                        }
                    });
                });
            } else {
                window.location.href = getDownloadBaseUrl(filename);
            }
        }

        function sendText() {
            const input = document.getElementById('text-input');
            const val = input.value.trim();
            if (val) {
                socket.emit('new_text', { text: val });
                input.value = '';
            }
        }

        document.getElementById('text-input').addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') { sendText(); }
        });

        function clearAllText() {
            openConfirmModal("CLEAR ALL TEXT HISTORY?", () => { socket.emit('clear_all_text'); });
        }

        function deleteText(index) {
            socket.emit('delete_text', { index: parseInt(index) });
        }

        socket.on('update_history', function(data) {
            const box = document.getElementById('history-box');
            box.innerHTML = '';
            for (let i = data.history.length - 1; i >= 0; i--) {
                const item = data.history[i];
                const escapedItem = item.replace(/`/g, '\\\\`').replace(/"/g, '&quot;');
                const div = document.createElement('div');
                div.className = 'item-box';
                div.setAttribute('data-index', i);
                div.innerHTML = `
                    <div class="item-text">${escapeHtml(item)}</div>
                    <div class="item-actions">
                        <button class="btn-action" onclick="showTextQR(\\`${escapedItem}\\`)">[QR]</button> 
                        <button class="btn-action" onclick="copyText(this)">[COPY]</button>
                        <button class="btn-action btn-delete" onclick="deleteText(${i})">[RM]</button>
                    </div>
                `;
                box.appendChild(div);
            }
        });

        function copyText(button) {
            const text = button.closest('.item-box').querySelector('.item-text').innerText;
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed"; textArea.style.left = "-9999px";
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                const origText = button.innerText; button.innerText = '[OK]';
                setTimeout(() => button.innerText = origText, 1000);
            } catch (err) { alert('Clipboard error'); }
            document.body.removeChild(textArea);
        }

        function uploadFiles() {
            const fileInput = document.getElementById('file-input');
            const passInput = document.getElementById('file-password');
            const status = document.getElementById('upload-status');
            if (fileInput.files.length === 0) return;

            const formData = new FormData();
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append('files', fileInput.files[i]);
            }
            formData.append('password', passInput.value);
            status.style.display = 'block'; status.innerText = 'Uploading...';

            fetch('/upload', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                status.innerText = 'Files uploaded successfully';
                fileInput.value = ''; passInput.value = '';
                setTimeout(() => { status.style.display = 'none'; }, 2000);
            });
        }

        function deleteFile(filename) { socket.emit('delete_file', { filename: filename }); }
        function clearAllFiles() { openConfirmModal("DELETE ALL UPLOADED FILES?", () => { socket.emit('clear_all_files'); }); }

        socket.on('update_files', function(data) {
            const filesBox = document.getElementById('files-box');
            filesBox.innerHTML = '';

            data.files.forEach(file => {
                const escapedName = file.name.replace(/'/g, "\\\\'");
                const elementId = file.name.replace(/\./g, '_');
                
                const savedPass = getSavedPassword(file.name);
                const isCurrentlyLocked = file.protected && !savedPass;

                let lockBadgeHtml = (file.protected && !savedPass) ? `<span class="file-lock-badge" id="lock-badge-${elementId}">[LOCKED]</span>` : '';
                let previewHtml = '';

                if (isCurrentlyLocked) {
                    previewHtml = `<div class="file-preview is-locked" onclick="unlockPreview('${escapedName}')">[LOCK]</div>`;
                } else if (file.is_image) {
                    const srcUrl = getDownloadBaseUrl(file.name);
                    previewHtml = `
                        <div class="file-preview clickable" onclick="openImageModal('${srcUrl}', '${escapedName}')">
                            <img src="${srcUrl}" alt="thumb">
                        </div>`;
                } else {
                    previewHtml = `<div class="file-preview">${file.ext}</div>`;
                }

                const li = document.createElement('li');
                li.className = 'file-row';
                li.innerHTML = `
                    <div class="file-info-block">
                        <div id="preview-wrapper-${elementId}">${previewHtml}</div>
                        <div class="file-info">
                            <div class="file-name">${escapeHtml(file.name)} ${lockBadgeHtml}</div>
                            <div class="file-size">${file.size} MB</div>
                        </div>
                    </div>
                    <div class="file-actions">
                        <button class="btn-action" onclick="handleFileQRClick('${escapedName}', ${file.protected})">[QR]</button>
                        <button class="btn-action" onclick="handleFileGetClick('${escapedName}', ${file.protected})">[GET]</button>
                        <button class="btn-action btn-delete" onclick="deleteFile('${escapeHtml(file.name)}')">[RM]</button>
                    </div>
                `;
                filesBox.appendChild(li);
            });
        });

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    local_ip = get_local_ip()
    return render_template_string(
        HTML_TEMPLATE,
        history=history_text,
        files=get_files_info(),
        local_ip=local_ip
    )


@app.route("/check_pass")
def check_pass():
    filename = request.args.get("filename", "")
    user_pass = request.args.get("pass", "")
    if filename in file_passwords:
        return jsonify({"valid": file_passwords[filename] == user_pass})
    return jsonify({"valid": True})


@socketio.on('request_files_refresh')
def handle_refresh_request():
    emit('update_files', {'files': get_files_info()}, broadcast=True)


@socketio.on('new_text')
def handle_new_text(data):
    text_val = data.get('text', '').strip()
    if text_val:
        history_text.append(text_val)
        if len(history_text) > 40:
            history_text.pop(0)
        emit('update_history', {'history': history_text}, broadcast=True)


@socketio.on('delete_text')
def handle_delete_text(data):
    index = data.get('index')
    if index is not None and 0 <= index < len(history_text):
        history_text.pop(index)
        emit('update_history', {'history': history_text}, broadcast=True)


@socketio.on('clear_all_text')
def handle_clear_all_text():
    global history_text
    history_text = []
    emit('update_history', {'history': history_text}, broadcast=True)


@socketio.on('delete_file')
def handle_delete_file(data):
    filename = data.get('filename')
    if filename:
        secure_filename = os.path.basename(filename)
        file_path = os.path.join(UPLOAD_DIR, secure_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        if secure_filename in file_passwords:
            del file_passwords[secure_filename]
        emit('update_files', {'files': get_files_info()}, broadcast=True)


@socketio.on('clear_all_files')
def handle_clear_all_files():
    global file_passwords
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    file_passwords = {}
    emit('update_files', {'files': get_files_info()}, broadcast=True)


@app.route("/upload", methods=["POST"])
def upload_files():
    uploaded_files = request.files.getlist("files")
    password = request.form.get("password", "").strip()

    for file in uploaded_files:
        if file.filename:
            file.save(os.path.join(UPLOAD_DIR, file.filename))
            if password:
                file_passwords[file.filename] = password

    socketio.emit('update_files', {'files': get_files_info()})
    return jsonify({"status": "success"})


@app.route("/download/<filename>")
def download_file(filename):
    if filename in file_passwords:
        user_pass = request.args.get("pass", "")
        if user_pass != file_passwords[filename]:
            return "<h1>ACCESS DENIED: Invalid or Missing Password</h1>", 403

    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
