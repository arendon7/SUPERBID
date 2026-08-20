import sqlite3
from openpyxl import Workbook
from superbid_collector.fasecolda import import_fasecolda_excel
def test_fasecolda_excel_import(tmp_path):
 p=tmp_path/"guia.xlsx";wb=Workbook();ws=wb.active;ws.append(["Texto preliminar"]);ws.append(["Codigo","HomologoCo","Marca","Clase","Referencia1","Referencia2","Referencia3","Servicio",2024,2025,2026]);ws.append(["08001190","08032065","RENAULT","AUTOMOVIL","SANDERO","EXPRESSION","MT 1600CC","Particular",42000,45000,58700]);wb.save(p);c=sqlite3.connect(":memory:");r=import_fasecolda_excel(c,p);assert r["values_inserted"]==3;assert c.execute("SELECT value_cop FROM fasecolda_values WHERE model_year=2026").fetchone()[0]==58700000
