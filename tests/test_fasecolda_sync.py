from openpyxl import Workbook

from superbid_collector.storage import Store
from superbid_collector.fasecolda import import_fasecolda_excel
from superbid_collector.fasecolda_sync import sync_fasecolda


class FakeRemote:
    def __init__(self):
        self.rows=[]
    def upsert(self, table, rows, on_conflict=None, returning=True):
        assert table == "fasecolda_values"
        assert on_conflict == "record_key"
        self.rows.extend(rows)
        return []


def test_sync_fasecolda_is_keyed(tmp_path):
    s=Store(tmp_path/"f.db"); s.init()
    x=tmp_path/"guia.xlsx"
    wb=Workbook(); ws=wb.active
    ws.append(["Codigo","HomologoCo","Marca","Clase","Referencia1","Referencia2","Referencia3","Servicio",2024,2025,2026])
    ws.append(["1","2","TOYOTA","AUTOMOVIL","COROLLA","XEI","AT","Particular",60000,65000,70000])
    wb.save(x)
    import_fasecolda_excel(s.conn,x)
    remote=FakeRemote()
    count=sync_fasecolda(s.conn,remote,batch_size=2)
    assert count == 3
    assert len(remote.rows) == 3
    assert all(row["record_key"] for row in remote.rows)
