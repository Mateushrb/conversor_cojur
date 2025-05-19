import base64
import os
from pathlib import Path
from bs4 import BeautifulSoup

def embed_images_in_html(html_path, output_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Procura todas as imagens
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src or src.startswith('data:'):
            continue  # já está embutida ou src inválido

        # Caminho completo da imagem relativo ao HTML
        img_path = os.path.join(os.path.dirname(html_path), src)

        # Detecta o tipo MIME da imagem
        ext = Path(img_path).suffix.lower()
        mime = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }.get(ext)

        if mime is None:
            print(f"Formato de imagem não suportado: {ext}")
            continue
        
        if not os.path.exists(img_path):
            print(f"Imagem não encontrada, ignorando: {img_path}")
            continue

        # Converte a imagem para base64
        with open(img_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            data_uri = f"data:{mime};base64,{encoded_string}"
            img['src'] = data_uri  # substitui o src

    # Salva o novo HTML com imagens embutidas
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(str(soup))

    print(f"HTML com imagens embutidas salvo em: {output_path}")