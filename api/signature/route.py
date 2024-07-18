from flask import Blueprint, request, jsonify, current_app
from.controller import SignatureController
from werkzeug.utils import secure_filename
import os

signature = Blueprint('signatures', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MODE = {'PENGIRIM', 'PENERIMA', 'PENGELUARAN', 'GUDANG', 'PEMASARAN_MENGETAHUI', 'PEMASARAN_TGL'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@signature.route('/detect', methods=["POST"])
def detect_signature():
    try:
        if 'file' not in request.files:
            return jsonify(message="File tidak boleh kosong"), 400
        
        file = request.files['file']
        mode = request.form.get('mode').upper()

        if mode == '' or not mode:
            return jsonify(message="Mode deteksi tanda tangan tidak boleh kosong"), 400
        
        if mode not in ALLOWED_MODE:
            return jsonify(message=f"Mode deteksi tidak tersedia.Mode yang tersedia {', '.join(ALLOWED_MODE)}"), 400

        if file.filename == '':
            return jsonify(message="Nama file tidak boleh kosong"), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify(message="Ekstensi file tidak diperbolehkan"), 400

        if not os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'])):
            os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER']))
            os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], 'raw'))
            os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], 'cropped'))
            os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], 'preversion'))

        filename = secure_filename(file.filename)
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'raw', filename)
        file.save(full_path)

        return SignatureController().detect_signature(full_path, filename, mode)
    except:
        return jsonify(message="Ada sesuatu yang salah"), 500