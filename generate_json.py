import os
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from git import Repo
from tqdm import tqdm

# --- CONFIG ---
winget_repo_url = "https://github.com/microsoft/winget-pkgs.git"
output_json = "winget_packages.json"

print("🔄 Cloning Winget repository (shallow)...")
local_repo_path = tempfile.mkdtemp()
Repo.clone_from(winget_repo_url, local_repo_path, depth=1)

print("📦 Parsing manifests and filtering entries...")
manifest_root = Path(local_repo_path) / "manifests"
apps = []

# Recursively find all YAML files in manifest directory
yaml_files = list(manifest_root.rglob("*.yaml"))

# First pass: build a dictionary of app_id to list of YAML file paths
app_id_to_files = {}
for metadata_file in yaml_files:
    try:
        with open(metadata_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        continue

    app_id = data.get("PackageIdentifier")
    if not app_id:
        continue

    app_id_to_files.setdefault(app_id, []).append(metadata_file)

# Second pass: process each app's YAMLs to select the best entry
for app_id in tqdm(app_id_to_files, desc="🔍 Processing manifests", unit="app"):
    yaml_list = app_id_to_files[app_id]
    selected_data = None

    for metadata_file in yaml_list:
        try:
            with open(metadata_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            continue

        description = data.get("Description") or ""
        if description.strip():
            selected_data = data
            break

    if not selected_data:
        # fallback to first YAML if none have description
        try:
            with open(yaml_list[0], encoding="utf-8") as f:
                selected_data = yaml.safe_load(f)
        except Exception:
            continue

    debug = False  # Set to True to enable debug logging
    name = selected_data.get("PackageName") or ""
    publisher = selected_data.get("Publisher")
    description = selected_data.get("Description") or ""

    # Skip duplicate app IDs (already unique here)
    # Skip non-ASCII name or description
    # if not name.isascii() or not description.isascii():
    #     continue

    # Skip bad entries
    # if not app_id or not name or not publisher:
    #     if debug: print(f"Skipping due to missing fields: {app_id}")
    #     continue
    # if "placeholder" in name.lower() or "tbd" in name.lower():
    #     if debug: print(f"Skipping due to placeholder/tbd name: {app_id}")
    #     continue
    # if len(description.strip()) < 15:
    #     if debug: print(f"Skipping due to short description: {app_id}")
    #     continue

    # Known icons for popular apps
    popular_icons = {
        "Google.Chrome": "/icons/chrome.png",
        "Mozilla.Firefox": "/icons/firefox.png",
        "VideoLAN.VLC": "/icons/vlc.png",
        "Notepad++.Notepad++": "/icons/notepadpp.png"
    }
    default_icon = "/icons/intunify-default.png"
    icon_url = popular_icons.get(app_id, default_icon)

    apps.append({
        "id": app_id,
        "name": name,
        "publisher": publisher,
        "description": description.strip(),
        "icon": icon_url
    })

apps.sort(key=lambda x: x["name"].lower())

# Save output
output_path = Path.cwd() / output_json
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(apps, f, indent=2, ensure_ascii=False)

print(f"✅ Saved {len(apps)} apps to: {output_json}")

# Cleanup
try:
    shutil.rmtree(local_repo_path)
    print("🧹 Temporary clone removed.")
except Exception as e:
    print("⚠️ Could not clean up temp folder (safe to ignore on Windows):", e)