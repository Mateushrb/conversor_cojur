from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from pathlib import Path
import os
import shutil
import uuid
import zipfile
from conversor import converter_doc_para_html

app = FastAPI()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("uploads")
CONVERTED_DIR = Path("convertidos")
ZIP_DIR = Path("zips")

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
    session_zip = ZIP_DIR / f"{session_id}.zip"

    session_upload.mkdir()
    session_convertido.mkdir()

    # Salvar uploads
    paths_doc = []
    for file in files:
        if not file.filename.endswith((".doc", ".docx")):
            continue
        destino = session_upload / file.filename
        with open(destino, "wb") as f:
            f.write(await file.read())
        paths_doc.append(destino)

    # Converter
    html_paths = []
    for path_doc in paths_doc:
        html_path = converter_doc_para_html(path_doc, session_convertido)
        html_paths.append(html_path)

    # Compactar
    with zipfile.ZipFile(session_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for html in html_paths:
            zipf.write(html, arcname=html.name)
            pasta_arquivos = html.with_name(html.stem + "_arquivos")
            if pasta_arquivos.exists():
                for item in pasta_arquivos.rglob("*"):
                    arcname = Path(html.stem + "_arquivos") / item.relative_to(pasta_arquivos)
                    zipf.write(item, arcname=arcname)

    # Limpar arquivos .doc/.docx
    shutil.rmtree(session_upload, ignore_errors=True)

    # Limpar HTML + pastas
    for html in html_paths:
        html.unlink(missing_ok=True)
        pasta_arquivos = html.with_name(html.stem + "_arquivos")
        if pasta_arquivos.exists():
            shutil.rmtree(pasta_arquivos, ignore_errors=True)
    session_convertido.rmdir()

    return RedirectResponse(url=f"/download_page/{session_zip.name}", status_code=303)


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
