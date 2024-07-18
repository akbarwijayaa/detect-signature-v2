from flask import Blueprint, jsonify
from api.signature import route

api = Blueprint('api', __name__)
api.register_blueprint(route.signature, url_prefix="/signatures")

@api.route('/')
def home():
    return jsonify(message="Api deteksi tanda tangan pada dokumen")
