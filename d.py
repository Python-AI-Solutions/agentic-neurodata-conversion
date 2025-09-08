from pathlib import Path
from urllib.parse import urlparse, parse_qs
from dandi.dandiapi import DandiAPIClient

LINK = input("Paste your DANDI link: ").strip()

parsed = urlparse(LINK)
parts = parsed.path.strip("/").split("/")
if len(parts) < 3 or parts[0] != "dandiset":
    raise SystemExit("❌ Not a valid DANDI dandiset URL")
dandiset_id = parts[1]
version = parts[2]
prefix = parse_qs(parsed.query).get("location", [""])[0].lstrip("/")

print(f"\n📂 Parsed:\n  Dandiset: {dandiset_id}\n  Version : {version}\n  Prefix  : {prefix}\n")

OUT = Path(f"./{dandiset_id}")
OUT.mkdir(parents=True, exist_ok=True)

with DandiAPIClient() as client:
    ds = client.get_dandiset(dandiset_id, version)
    for asset in ds.get_assets_with_path_prefix(prefix):
        if not asset.path.endswith(".nwb"):
            continue
        local_path = OUT / asset.path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"⬇️  Downloading: {asset.path}")
        asset.download(local_path)   # no 'existing' here

print("\n✅ All done!")
