import urllib.request
import json
import os

components = [
    "button", "input", "label", "select", "dialog", "dropdown-menu", 
    "table", "badge", "avatar", "card", "form", "textarea", "checkbox", 
    "separator", "sheet", "tooltip"
]

base_url = "https://ui.shadcn.com/registry/styles/new-york/"

ui_dir = os.path.join("src", "components", "ui")
os.makedirs(ui_dir, exist_ok=True)

for comp in components:
    try:
        url = f"{base_url}{comp}.json"
        print(f"Fetching {comp}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for file_data in data.get("files", []):
                file_name = file_data["name"]
                content = file_data["content"]
                file_path = os.path.join(ui_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
        print(f"Saved {comp}")
    except Exception as e:
        print(f"Error for {comp}: {e}")
