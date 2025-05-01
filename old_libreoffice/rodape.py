def limpar_html_moderno(path):
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Remove <div title="footer">
    for footer in soup.find_all("div", attrs={"title": "footer"}):
        footer.decompose()

    # Substitui align="center" por style="text-align: center;"
    for p in soup.find_all("p", align=True):
        align = p["align"]
        del p["align"]
        p["style"] = f"text-align: {align};" + (f" {p.get('style', '')}".strip())

    # Ajusta regra de CSS global <style> p { ... }
    for style in soup.find_all("style"):
        if style.string and "p {" in style.string:
            linhas = style.string.splitlines()
            novas_linhas = []
            for linha in linhas:
                if linha.strip().startswith("p {"):
                    if "margin-top:" not in linha:
                        # Garante que todas declarações terminem com ponto e vírgula
                        linha = linha.replace("{", "{ ").replace("}", " }")
                        partes = linha.split("{", 1)
                        seletor = partes[0]
                        regras = partes[1].split("}", 1)[0].strip()

                        # Corrige regras sem ; no final
                        if not regras.endswith(";"):
                            regras += ";"

                        # Garante que cada regra termine com ;
                        regras = "; ".join([r.strip().rstrip(";") for r in regras.split(";") if r.strip()]) + ";"

                        # Adiciona margin-top: 0;
                        regras += " margin-top: 0;"
                        linha = f"{seletor}{{ {regras} }}"

                novas_linhas.append(linha)
            style.string = "\n".join(novas_linhas)

    # A partir da segunda <table>, adiciona width: 900px
    tables = soup.find_all("table")
    for i, table in enumerate(tables[1:], start=2):  # começa do segundo
        style_atual = table.get("style", "")
        if "width" not in style_atual:
            table["style"] = f"{style_atual.strip()}; width: 900px;".strip("; ")

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(soup))

