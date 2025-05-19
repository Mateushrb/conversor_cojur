import base64
import os
from pathlib import Path
from bs4 import BeautifulSoup

def embed_images_in_html(html_path, output_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # 🔁 Processa <img src="...">
    for img in soup.find_all('img'):
        src = unquote(img.get('src') or "")
        if not src or src.startswith('data:'):
            continue

        img_path = os.path.join(os.path.dirname(html_path), src)
        ext = Path(img_path).suffix.lower()
        mime = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }.get(ext)

        if mime is None:
            print(f"[AVISO] Extensão de imagem não suportada: {ext} em {img_path}")
            continue

        if not os.path.exists(img_path):
            print(f"[AVISO] Imagem não encontrada, ignorando: {img_path}")
            continue

        try:
            with open(img_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                data_uri = f"data:{mime};base64,{encoded_string}"
                img['src'] = data_uri
        except Exception as e:
            print(f"[ERRO] Falha ao embutir imagem {img_path}: {e}")
            continue

    # 🔁 Processa <v:imagedata src="...">
    for vimg in soup.find_all('v:imagedata'):
        src = unquote(vimg.get('src') or "")
        if not src or src.startswith('data:'):
            continue

        img_path = os.path.join(os.path.dirname(html_path), src)
        ext = Path(img_path).suffix.lower()
        mime = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }.get(ext)

        if mime is None:
            print(f"[AVISO] VML com extensão não suportada: {ext} em {img_path}")
            continue

        if not os.path.exists(img_path):
            print(f"[AVISO] VML imagem não encontrada, ignorando: {img_path}")
            continue

        try:
            with open(img_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                data_uri = f"data:{mime};base64,{encoded_string}"

                # Cria elemento <img> substituto
                new_img = soup.new_tag("img", src=data_uri)
                vimg.insert_after(new_img)
                vimg.decompose()
        except Exception as e:
            print(f"[ERRO] Falha ao embutir VML {img_path}: {e}")
            continue

    # Salva HTML final com imagens embutidas
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(str(soup))

    print(f"[OK] HTML com imagens embutidas salvo em: {output_path}")