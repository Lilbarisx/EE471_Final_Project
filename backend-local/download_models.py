import os
import urllib.request
import zipfile

# EasyOCR Model URLs
MODELS = {
    "craft_mlt_25k.zip": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip"
}

target_dir = os.path.expanduser(r"~\.EasyOCR\model")
os.makedirs(target_dir, exist_ok=True)

def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(100, (downloaded * 100) / total_size) if total_size > 0 else 0
    print(f"\rDownloading... {percent:.1f}% ({downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB)", end="")

for name, url in MODELS.items():
    dest_path = os.path.join(target_dir, name)
    extracted_pth = dest_path.replace(".zip", ".pth")
    
    if os.path.exists(extracted_pth):
        print(f"\n{name.replace('.zip', '')} is already downloaded and extracted.")
        continue
        
    print(f"\nDownloading {name} from {url}...")
    try:
        urllib.request.urlretrieve(url, dest_path, download_progress)
        print(f"\nExtracting {name}...")
        with zipfile.ZipFile(dest_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(dest_path)
        print(f"Successfully downloaded and extracted {name}!")
    except Exception as e:
        print(f"\nError downloading {name}: {e}")
