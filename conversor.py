import os
from pathlib import Path
import win32com.client
import chardet


def converter_doc_para_html(diretorio_entrada: str, diretorio_saida: str):
    entrada = Path(diretorio_entrada)
    saida = Path(diretorio_saida)

    if not entrada.exists():
        raise FileNotFoundError(f'Diretório de entrada não encontrado: {entrada}')
    if not saida.exists():
        saida.mkdir(parents=True)

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    for arquivo in entrada.iterdir():
        if arquivo.suffix.lower() in ['.doc', '.docx']:
            nome_base = arquivo.stem
            caminho_saida = saida / f"{nome_base}.html"

            # Abrir e salvar como HTML
            doc = word.Documents.Open(str(arquivo.resolve()))
            doc.SaveAs(str(caminho_saida.resolve()), FileFormat=8)  # wdFormatHTML
            doc.Close()

            # Detectar codificação original do HTML
            with open(caminho_saida, 'rb') as f:
                conteudo_binario = f.read()
                resultado = chardet.detect(conteudo_binario)
                encoding_origem = resultado['encoding']

            if not encoding_origem:
                print(f"⚠️ Não foi possível detectar a codificação de {caminho_saida.name}, assumindo 'latin1'")
                encoding_origem = 'latin1'

            # Reabrir como texto com codificação correta
            conteudo_texto = conteudo_binario.decode(encoding_origem, errors='replace')

            # Substituir charset para UTF-8
            conteudo_texto = conteudo_texto.replace(
                '<meta http-equiv=Content-Type content="text/html; charset=windows-1252">',
                '<meta http-equiv=Content-Type content="text/html; charset="UTF-8">'
            )

            # Regravar com UTF-8
            with open(caminho_saida, 'w', encoding='utf-8') as f:
                f.write(conteudo_texto)

            print(f"✅ Convertido: {arquivo.name} → {caminho_saida.name} (UTF-8)")

    word.Quit()


if __name__ == "__main__":
    diretorio_base = Path(__file__).parent
    entrada = diretorio_base / "entrada"
    saida = diretorio_base / "saida"
    converter_doc_para_html(str(entrada), str(saida))