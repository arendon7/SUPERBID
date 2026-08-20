from superbid_collector.attachments import classify_attachment,extract_html_attachments,extract_json_attachments
def test_classify_peritaje():assert classify_attachment("Informe de Peritaje","https://x.com/a.pdf")=="PERITAJE"
def test_html_attachment_extraction():
    rows=extract_html_attachments("https://www.superbid.com.co/oferta/x-1234567",'<a href="/docs/peritaje_123.pdf">Peritaje vehículo</a><a href="/foo">Inicio</a>');assert len(rows)==1 and rows[0]["kind"]=="PERITAJE" and rows[0]["url"].startswith("https://www.superbid.com.co/")
def test_json_attachment_extraction():
    rows=extract_json_attachments({"attachments":[{"name":"Informe técnico de inspección","download_url":"https://cdn.example.com/peritaje.pdf"},{"name":"Contrato","url":"https://cdn.example.com/contrato.pdf"}]});assert any(x["kind"]=="PERITAJE" for x in rows);assert any(x["kind"]=="CONTRATO" for x in rows)
