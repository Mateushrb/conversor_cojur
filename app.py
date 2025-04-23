import os
import uuid
import zipfile
import subprocess
from flask import Flask, request, render_template, send_file
from rodape import limpar_html_moderno

UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
ALLOWED_EXTENSIONS = {'.doc', '.docx'}

app = Flask(__name__)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def allowed_file(filename):
	return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def salvar_arquivo_temporario(file):
	ext = os.path.splitext(file.filename)[1]
	nome = f"{uuid.uuid4()}_{file.filename}"
	caminho = os.path.join(UPLOAD_FOLDER, nome)
	file.save(caminho)
	return caminho

def converter_para_docx(caminho_doc):
    cmd = [
        "libreoffice", "--headless",
        "--convert-to", "docx",
        "--outdir", UPLOAD_FOLDER,
        caminho_doc
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    nome_base = os.path.splitext(os.path.basename(caminho_doc))[0]
    caminho_docx = os.path.join(UPLOAD_FOLDER, nome_base + ".docx")
    return caminho_docx if os.path.exists(caminho_docx) else None

def converter_para_html(caminho_docx):
    cmd = [
        "libreoffice", "--headless",
        "--convert-to", "html:HTML (StarWriter)",
        "--outdir", CONVERTED_FOLDER,
        caminho_docx
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    nome_base = os.path.splitext(os.path.basename(caminho_docx))[0]
    caminho_html = os.path.join(CONVERTED_FOLDER, nome_base + ".html")

    if result.returncode != 0 or not os.path.exists(caminho_html):
        print("Erro na conversão:", result.stderr)
        return None

    return caminho_html

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        arquivos = request.files.getlist("files")
        htmls_convertidos = []

        for arquivo in arquivos:
            if arquivo and allowed_file(arquivo.filename):
                temp_doc = salvar_arquivo_temporario(arquivo)

                # Se for .doc, converte primeiro para .docx
                ext = os.path.splitext(temp_doc)[1].lower()
                if ext == ".doc":
                    temp_docx = converter_para_docx(temp_doc)
                else:
                    temp_docx = temp_doc

                if not temp_docx:
                    continue

                html_convertido = converter_para_html(temp_docx)
                if html_convertido:
                    limpar_html_moderno(html_convertido)
                    htmls_convertidos.append(html_convertido)

        if not htmls_convertidos:
            return "Nenhum arquivo foi convertido com sucesso."

        if len(htmls_convertidos) == 1:
            return send_file(htmls_convertidos[0], as_attachment=True)

        # Compactar múltiplos HTMLs
        zip_path = os.path.join(CONVERTED_FOLDER, f"{uuid.uuid4()}.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for html_file in htmls_convertidos:
                zipf.write(html_file, os.path.basename(html_file))

        return send_file(zip_path, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
