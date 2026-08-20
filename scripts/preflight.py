from __future__ import annotations
import os,sys
from pathlib import Path
warnings=[]; errors=[]
if not os.getenv("SUPERBID_ADMIN_TOKEN"): warnings.append("SUPERBID_ADMIN_TOKEN no configurado")
db=os.getenv("SUPERBID_DB","superbid.db"); p=Path(db)
try:
    p.parent.mkdir(parents=True,exist_ok=True); t=p.parent/".write-test"; t.write_text("ok"); t.unlink()
except Exception as exc: errors.append(f"Directorio DB no escribible: {exc}")
if not os.getenv("SUPERBID_DISCOVERY_URLS"): warnings.append("SUPERBID_DISCOVERY_URLS vacío")
if not os.getenv("MELI_ACCESS_TOKEN"): warnings.append("MELI_ACCESS_TOKEN vacío")
print("Preflight")
for x in warnings: print("WARN:",x)
for x in errors: print("ERROR:",x)
sys.exit(1 if errors else 0)
