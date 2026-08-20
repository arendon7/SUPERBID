import json
from superbid_collector.attachments import extract_json_attachments


def test_extract_peritaje_from_product_custom_json():
    embedded=json.dumps({
        "fields":[
            {"label":"Informe de peritaje","value":"https://files.example.com/peritaje-123.pdf"},
            {"label":"Color","value":"Rojo"}
        ]
    })
    payload={"product":{"productCustomJson":embedded}}
    rows=extract_json_attachments(payload)
    assert len(rows)==1
    assert rows[0]["kind"]=="PERITAJE"
    assert rows[0]["url"].endswith("peritaje-123.pdf")
    assert rows[0]["source"]=="embedded_json"
