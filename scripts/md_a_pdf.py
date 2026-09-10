"""Convierte el informe.md a PDF usando fpdf2 (Python puro, sin dependencias externas)."""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

FUENTES_DIR = Path("docs/fuentes")
FUENTE_REGULAR = FUENTES_DIR / "DejaVuSans.ttf"
FUENTE_BOLD = FUENTES_DIR / "DejaVuSans-Bold.ttf"
FUENTE_ITALIC = FUENTES_DIR / "DejaVuSans-Oblique.ttf"
FUENTE_BOLD_ITALIC = FUENTES_DIR / "DejaVuSans-BoldOblique.ttf"
FUENTE_MONO = FUENTES_DIR / "DejaVuSansMono.ttf"


def _asegurar_fuentes() -> None:
    """Descarga fuentes DejaVu si no existen (solo la primera vez)."""
    if FUENTE_REGULAR.exists() and FUENTE_BOLD.exists() and FUENTE_MONO.exists():
        return
    import urllib.request
    import zipfile
    import io

    FUENTES_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip"
    print(f"Descargando fuentes DejaVu desde {url}...")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.namelist():
            if not member.endswith(".ttf"):
                continue
            nombre = Path(member).name
            if nombre in {"DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf", "DejaVuSansMono.ttf"}:
                with z.open(member) as src, open(FUENTES_DIR / nombre, "wb") as dst:
                    dst.write(src.read())
    print(f"Fuentes descargadas en {FUENTES_DIR}")


_asegurar_fuentes()


class InformePDF(FPDF):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_font("cuerpo", "", str(FUENTE_REGULAR))
        self.add_font("cuerpo", "B", str(FUENTE_BOLD))
        self.add_font("cuerpo", "I", str(FUENTE_ITALIC))
        self.add_font("cuerpo", "BI", str(FUENTE_BOLD_ITALIC))
        self.add_font("mono", "", str(FUENTE_MONO))
        self.set_font("cuerpo", "", 10)
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("cuerpo", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Agente Auditor Comunitario (AAC) - Sergio de la Cruz - ISY0101", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def footer(self) -> None:
        self.set_y(-10)
        self.set_font("cuerpo", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Pagina {self.page_no()} de {{nb}}", align="C")

    def titulo(self, texto: str, nivel: int = 1) -> None:
        if nivel == 1:
            self.set_font("cuerpo", "B", 13)
            self.set_text_color(20, 50, 80)
            self.ln(2)
            self.multi_cell(0, 6.5, texto, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(20, 50, 80)
            self.set_line_width(0.4)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(1.5)
        elif nivel == 2:
            self.set_font("cuerpo", "B", 11)
            self.set_text_color(20, 50, 80)
            self.ln(1.5)
            self.multi_cell(0, 5.5, texto, new_x="LMARGIN", new_y="NEXT")
            self.ln(0.3)
        elif nivel == 3:
            self.set_font("cuerpo", "B", 9.5)
            self.set_text_color(40, 80, 110)
            self.ln(0.5)
            self.multi_cell(0, 5, texto, new_x="LMARGIN", new_y="NEXT")
        else:
            self.set_font("cuerpo", "B", 9)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 5, texto, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def parrafo(self, texto: str) -> None:
        self.set_font("cuerpo", "", 9)
        self.multi_cell(0, 4.2, texto, new_x="LMARGIN", new_y="NEXT")
        self.ln(0.4)

    def codigo(self, texto: str) -> None:
        self.set_font("mono", "", 7)
        self.set_fill_color(240, 240, 240)
        self.set_x(self.l_margin)
        for linea in texto.split("\n"):
            self.cell(0, 3.5, linea, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_font("cuerpo", "", 9)
        self.ln(1.2)

    def bullet(self, texto: str, nivel: int = 0) -> None:
        self.set_font("cuerpo", "", 9)
        x_inicial = self.l_margin + nivel * 3
        self.set_x(x_inicial)
        self.cell(3.5, 4.2, "-")
        ancho = self.w - self.r_margin - self.get_x()
        self.multi_cell(ancho, 4.2, texto, new_x="LMARGIN", new_y="NEXT")

    def tabla(self, headers: list[str], filas: list[list[str]], anchos: list[int] | None = None) -> None:
        self.set_font("cuerpo", "B", 8)
        self.set_fill_color(230, 238, 248)
        self.set_text_color(20, 50, 80)
        if anchos is None:
            anchos = [int((self.w - self.l_margin - self.r_margin) / len(headers))] * len(headers)
        for i, h in enumerate(headers):
            self.cell(anchos[i], 5.5, h, border=1, fill=True, align="L")
        self.ln()
        self.set_font("cuerpo", "", 8)
        self.set_text_color(0, 0, 0)
        for fila in filas:
            if self.get_y() > self.h - 25:
                self.add_page()
            x_inicio = self.l_margin
            for i, celda in enumerate(fila):
                self.set_xy(x_inicio, self.get_y())
                self.multi_cell(anchos[i], 4, str(celda), border=1, align="L")
                x_inicio += anchos[i]
            self.set_y(self.get_y() + 0.1)
        self.ln(1.2)

    def separador(self) -> None:
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(2)


def parsear_markdown(texto: str) -> list[tuple[str, str]]:
    """Convierte markdown a lista de bloques (tipo, contenido)."""
    bloques: list[tuple[str, str]] = []
    lineas = texto.split("\n")
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        stripped = linea.strip()

        if not stripped:
            i += 1
            continue
        if stripped == "---":
            bloques.append(("separador", ""))
            i += 1
            continue
        if stripped.startswith("```"):
            i += 1
            contenido = []
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                contenido.append(lineas[i])
                i += 1
            i += 1
            bloques.append(("codigo", "\n".join(contenido)))
            continue
        if stripped.startswith("# "):
            bloques.append(("h1", stripped[2:].strip()))
        elif stripped.startswith("## "):
            bloques.append(("h2", stripped[3:].strip()))
        elif stripped.startswith("### "):
            bloques.append(("h3", stripped[4:].strip()))
        elif stripped.startswith("#### "):
            bloques.append(("h4", stripped[5:].strip()))
        elif stripped.startswith("- "):
            nivel = 0
            temp = stripped
            while temp.startswith("  "):
                nivel += 1
                temp = temp[2:]
            if temp.startswith("- "):
                bloques.append(("bullet", (nivel, temp[2:].strip())))
        elif stripped.startswith("|"):
            filas_tabla = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                filas_tabla.append([c.strip() for c in lineas[i].strip().strip("|").split("|")])
                i += 1
            if len(filas_tabla) >= 2:
                headers = filas_tabla[0]
                datos = []
                for fila in filas_tabla[2:]:
                    if any(c for c in fila):
                        datos.append(fila)
                bloques.append(("tabla", (headers, datos)))
            continue
        else:
            parrafo = []
            while i < len(lineas) and lineas[i].strip() and not any(
                lineas[i].strip().startswith(p) for p in ["#", "-", "|", "```", "---"]
            ):
                parrafo.append(lineas[i].strip())
                i += 1
            bloques.append(("parrafo", " ".join(parrafo)))
            continue
        i += 1
    return bloques


def limpiar_texto(texto: str) -> str:
    """Quita formato markdown inline (bold, italic, code, links)."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"\*(.+?)\*", r"\1", texto)
    texto = re.sub(r"`([^`]+)`", r"\1", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    return texto


def md_a_pdf(md_path: Path, pdf_path: Path) -> None:
    texto = md_path.read_text(encoding="utf-8")
    bloques = parsear_markdown(texto)

    pdf = InformePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=18, top=15, right=18)
    pdf.alias_nb_pages(alias="nb")
    pdf.add_page()

    for tipo, contenido in bloques:
        if tipo == "h1":
            pdf.titulo(limpiar_texto(contenido), 1)
        elif tipo == "h2":
            pdf.titulo(limpiar_texto(contenido), 2)
        elif tipo == "h3":
            pdf.titulo(limpiar_texto(contenido), 3)
        elif tipo == "h4":
            pdf.titulo(limpiar_texto(contenido), 4)
        elif tipo == "parrafo":
            pdf.parrafo(limpiar_texto(contenido))
        elif tipo == "codigo":
            pdf.codigo(contenido)
        elif tipo == "bullet":
            nivel, texto_bullet = contenido
            pdf.bullet(limpiar_texto(texto_bullet), nivel)
        elif tipo == "tabla":
            headers, filas = contenido
            pdf.tabla(headers, filas)
        elif tipo == "separador":
            pdf.separador()

    pdf.output(str(pdf_path))
    print(f"PDF generado: {pdf_path}")
    print(f"Total paginas: {pdf.page_no()}")


if __name__ == "__main__":
    base = Path(__file__).parent.parent
    md_a_pdf(base / "informe.md", base / "informe.pdf")
