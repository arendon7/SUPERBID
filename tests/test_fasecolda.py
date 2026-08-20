import sqlite3
from pathlib import Path
from openpyxl import Workbook

from superbid_collector.fasecolda import import_fasecolda_excel

def test_fasecolda_excel_import(tmp_path: Path):
    p = tmp_path / "guia.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Texto preliminar"])
    ws.append(["Codigo","HomologoCo","Marca","Clase","Referencia1","Referencia2","Referencia3","Servicio",2024,2025,2026])
    ws.append(["08001190","08032065","RENAULT","AUTOMOVIL","SANDERO","EXPRESSION","MT 1600CC","Particular",42000,45000,58700])
    wb.save(p)

    c = sqlite3.connect(":memory:")
    result = import_fasecolda_excel(c, p)
    assert result["values_inserted"] == 3
    row = c.execute("SELECT value_cop FROM fasecolda_values WHERE model_year=2026").fetchone()
    assert row[0] == 58_700_000


def test_fasecolda_reimport_is_idempotent(tmp_path: Path):
    p = tmp_path / "guia.xlsx"
    wb = Workbook(); ws = wb.active
    ws.append(["Codigo","HomologoCo","Marca","Clase","Referencia1","Referencia2","Referencia3","Servicio",2024,2025,2026])
    ws.append(["08001190","08032065","RENAULT","AUTOMOVIL","SANDERO","EXPRESSION","MT 1600CC","Particular",42000,45000,58700])
    wb.save(p)
    c=sqlite3.connect(":memory:")
    import_fasecolda_excel(c,p)
    import_fasecolda_excel(c,p)
    assert c.execute("select count(*) from fasecolda_values").fetchone()[0]==3
    assert c.execute("select count(distinct record_key) from fasecolda_values").fetchone()[0]==3
