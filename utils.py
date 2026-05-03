import os
import requests
from io import BytesIO
from flask import current_app
from werkzeug.utils import secure_filename

def upload_to_imgbb(file, custom_name=None):
    """Upload une image vers ImgBB et retourne l'URL"""
    try:
        api_key = current_app.config['IMGBB_API_KEY']
        
        if hasattr(file, 'read'):
            file_content = file.read()
        else:
            file_content = file
        
        files = {
            'image': (secure_filename(custom_name or 'image.jpg'), file_content)
        }
        
        data = {
            'key': api_key,
            'name': custom_name or 'medilogic_image',
            'expiration': 0
        }
        
        response = requests.post('https://api.imgbb.com/1/upload', files=files, data=data)
        result = response.json()
        
        if result.get('success'):
            return result['data']['url']
        else:
            print(f"Erreur ImgBB: {result}")
            return None
            
    except Exception as e:
        print(f"Exception upload ImgBB: {e}")
        return None

def upload_multiple_images(files, boutique_id, article_id=None):
    """Upload plusieurs images vers ImgBB"""
    urls = []
    for idx, file in enumerate(files):
        if file and file.filename:
            custom_name = f"boutique_{boutique_id}_article_{article_id or idx}_{idx}"
            url = upload_to_imgbb(file, custom_name)
            if url:
                urls.append(url)
    return urls