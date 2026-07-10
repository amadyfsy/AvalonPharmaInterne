import os
import uuid
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from flask import current_app
from werkzeug.exceptions import BadRequest

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_upload(file):
    if not file or not file.filename:
        raise BadRequest("Aucun fichier fourni")
    
    if not allowed_file(file.filename):
        raise BadRequest("Type de fichier non autorisé")

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)
    return new_filename

def encrypt_data(data: str) -> str:
    if not data:
        return data
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set")
    f = Fernet(key.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    if not token:
        return token
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set")
    f = Fernet(key.encode())
    return f.decrypt(token.encode()).decode()
