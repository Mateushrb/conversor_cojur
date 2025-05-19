import win32com.client
import chardet
from pathlib import Path

def converter_doc_para_html(doc_path: Path, output_dir: Path) -> Path:
    nome_base = doc_path.stem
    html_path = output_dir / f"{nome_base}.html"

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(str(doc_path.resolve()))
        doc.SaveAs(str(html_path.resolve()), FileFormat=8)  # wdFormatHTML
        doc.Close()
    finally:
        word.Quit()

    # Detectar codificação
    with open(html_path, 'rb') as f:
        bin_data = f.read()
        encoding = chardet.detect(bin_data)['encoding'] or 'latin1'

    texto = bin_data.decode(encoding, errors='replace')
    texto = texto.replace(
        '<meta http-equiv=Content-Type content="text/html; charset=windows-1252">',
        '<meta http-equiv=Content-Type content="text/html; charset="UTF-8">'
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(texto)

    return html_path