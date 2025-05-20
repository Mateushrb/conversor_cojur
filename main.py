from fastapi import FastAPI, UploadFile, File, Request, Body
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from pathlib import Path
from datetime import datetime
from http import HTTPStatus
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
import zipfile
import socket
import logging
from db import registrar_conversao
from db import obter_estatisticas
from conversor import converter_doc_para_html
from tobase64 import embed_images_in_html

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/imagens", StaticFiles(directory="templates/imagens"), name="imagens")

UPLOAD_DIR = Path("uploads")
CONVERTED_DIR = Path("convertidos")
ZIP_DIR = Path("zips")

# Configura o logger para salvar no arquivo "access.log"
logging.basicConfig(
    filename="access.log",
    format="%(asctime)s - %(message)s",
    level=logging.INFO
)

# Middleware para registrar IP, nome da máquina, método, rota e status
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        client_ip = request.client.host
        try:
            # Resolução reversa via DNS
            hostname, _, _ = socket.gethostbyaddr(client_ip)
        except socket.herror:
            hostname = "desconhecido"
        except Exception as e:
            hostname = "desconhecido"
            logging.warning(f"Erro ao resolver hostname de {client_ip}: {e}")

        method = request.method
        path = request.url.path
        start_time = datetime.now()

        response = await call_next(request)

        status_code = response.status_code
        duration = (datetime.now() - start_time).total_seconds()
        status_phrase = HTTPStatus(status_code).phrase
        
        user_agent = request.headers.get("user-agent", "desconhecido")

        log_msg = (
            f'{client_ip} ({hostname}) - {method} {path} - {status_code} {status_phrase} - {duration:.2f}s - '
            f'{duration:.2f}s - UA: {user_agent}'
        )
        logging.info(log_msg)

        return response

app.add_middleware(LoggingMiddleware)

for folder in [UPLOAD_DIR, CONVERTED_DIR, ZIP_DIR]:
    folder.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/converter/")
async def converter_arquivos(files: list[UploadFile] = File(...)):
    session_id = uuid.uuid4().hex
    session_upload = UPLOAD_DIR / session_id
    session_convertido = CONVERTED_DIR / session_id

    session_upload.mkdir()
    session_convertido.mkdir()

    paths_doc = []
    for file in files:
        if not file.filename.endswith((".doc", ".docx")):
            continue
        destino = session_upload / file.filename
        with open(destino, "wb") as f:
            f.write(await file.read())
        paths_doc.append(destino)

    if not paths_doc:
        return JSONResponse(status_code=400, content={"error": "Nenhum arquivo válido enviado."})

    # 🔢 Registrar conversão no banco
    qtd_arquivos = len(paths_doc)
    nomes = [p.name for p in paths_doc]
    numero_conversao = registrar_conversao(qtd_arquivos, nomes)
    nome_base = f"conversao_{numero_conversao}_{qtd_arquivos}"

    html_paths = []
    for path_doc in paths_doc:
        html_path = converter_doc_para_html(path_doc, session_convertido)

        # Embutir imagens no HTML
        embed_images_in_html(html_path, html_path)

        # Deletar pasta de imagens externas
        pasta_arquivos = html_path.with_name(html_path.stem + "_arquivos")
        if pasta_arquivos.exists():
            shutil.rmtree(pasta_arquivos, ignore_errors=True)

        html_paths.append(html_path)

    shutil.rmtree(session_upload, ignore_errors=True)

    if len(html_paths) == 1:
        html_file = html_paths[0]
        
        # Confirma se o arquivo realmente existe
        if not html_file.exists():
            return JSONResponse(status_code=500, content={"error": "Arquivo convertido não foi encontrado no sistema."})
    
        # Caminho absoluto seguro
        absolute_path = html_file.resolve()

        # Usa o nome original do arquivo enviado como base
        nome_original_sem_ext = paths_doc[0].stem
        safe_name = f"{nome_original_sem_ext}.html"

        # Mover o arquivo final para a pasta zips (onde estão os .zip), para baixar via /download
        destino_final = ZIP_DIR / safe_name
        shutil.move(str(absolute_path), destino_final)

        # Limpa somente os temporários
        def cleanup():
            shutil.rmtree(session_upload, ignore_errors=True)
            session_convertido.rmdir()

        return JSONResponse(content={"html_file": safe_name}, background=BackgroundTask(cleanup))
    
    else:
        # 📦 Mais de um arquivo → compacta em .zip
        session_zip = ZIP_DIR / f"{nome_base}.zip"
        with zipfile.ZipFile(session_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for html in html_paths:
                zipf.write(html, arcname=html.name)

        # 🧹 Limpeza dos .html e pastas convertidas
        for html in html_paths:
            html.unlink(missing_ok=True)
            pasta_arquivos = html.with_name(html.stem + "_arquivos")
            if pasta_arquivos.exists():
                shutil.rmtree(pasta_arquivos, ignore_errors=True)

        session_convertido.rmdir()

        return JSONResponse(content={"zip_file": session_zip.name})

@app.post("/converter_arquivo/")
async def converter_arquivo(file: UploadFile = File(...)):
    session_id = uuid.uuid4().hex
    session_upload = UPLOAD_DIR / session_id
    session_convertido = CONVERTED_DIR / session_id

    session_upload.mkdir()
    session_convertido.mkdir()

    path = session_upload / file.filename
    with open(path, "wb") as f:
        f.write(await file.read())

    html_path = converter_doc_para_html(path, session_convertido)
    embed_images_in_html(html_path, html_path)

    # Move para ZIP_DIR temporariamente
    safe_name = path.stem + ".html"
    destino_final = ZIP_DIR / safe_name
    shutil.move(str(html_path), destino_final)

    shutil.rmtree(session_upload, ignore_errors=True)
    shutil.rmtree(session_convertido, ignore_errors=True)

    return {"arquivo": safe_name}

from fastapi import Body

@app.post("/finalizar_conversao")
async def finalizar_conversao(payload: dict = Body(...)):
    nomes = payload.get("arquivos", [])
    qtd = len(nomes)

    if qtd == 0:
        return JSONResponse(status_code=400, content={"error": "Nenhum arquivo recebido."})

    numero = registrar_conversao(qtd, nomes)

    if qtd == 1:
        return {"redirect_to": nomes[0]}

    nome_zip = f"conversao_{numero}_{qtd}.zip"
    zip_path = ZIP_DIR / nome_zip
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for nome in nomes:
            caminho = ZIP_DIR / nome
            if caminho.exists():
                zipf.write(caminho, arcname=nome)
                caminho.unlink(missing_ok=True)

    return {"redirect_to": nome_zip}

@app.get("/download/{zip_file_name}")
def download(zip_file_name: str):
    zip_path = ZIP_DIR / zip_file_name
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    def iterfile():
        with open(zip_path, mode="rb") as file_like:
            yield from file_like

    def remove_file():
        try:
            zip_path.unlink()
            print(f"Arquivo {zip_file_name} removido com sucesso após o download.")
        except Exception as e:
            print(f"Erro ao remover {zip_file_name}: {e}")

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_file_name}"},
        background=BackgroundTask(remove_file)
    )

@app.get("/download_page/{zip_file_name}", response_class=HTMLResponse)
def download_page(request: Request, zip_file_name: str):
    zip_path = ZIP_DIR / zip_file_name
    if not zip_path.exists():
        return HTMLResponse(content="Arquivo não encontrado.", status_code=404)
    
    download_url = f"/download/{zip_file_name}"
    return templates.TemplateResponse("download.html", {"request": request, "url": download_url})

@app.get("/estatisticas")
def estatisticas():
    stats = obter_estatisticas()
    return JSONResponse(content=stats)