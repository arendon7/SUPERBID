import os
from superbid_collector.storage import Store
from superbid_collector.discovery import add_discovery_source

db=os.getenv("SUPERBID_DB","superbid.db")
s=Store(db); s.init()

# Keep these configurable. If Superbid changes listing routes, add the current public
# vehicle listing/search pages here via CLI instead of changing collector code.
print("DB initialized:",db)
print("Add public Superbid listing pages with:")
print('superbid add-discovery-source "https://www.superbid.com.co/..." --db',db)
