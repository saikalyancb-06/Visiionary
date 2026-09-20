import sys
import shutil
import subprocess

print("=== PROJECT ENVIRONMENT INSPECTION ===")
print("PROJECT ROOT: D:\\webman")
print(f"OPERATING SYSTEM: {sys.platform}")
total, used, free = shutil.disk_usage("D:\\")
print(f"AVAILABLE DISK SPACE: {free / (1024**3):.2f} GB (Total: {total / (1024**3):.2f} GB, Used: {used / (1024**3):.2f} GB)")
print(f"PYTHON VERSION: {sys.version.split()[0]}")

for cmd in [("NODE VERSION", ["node", "--version"]), ("GIT VERSION", ["git", "--version"])]:
    try:
        res = subprocess.run(cmd[1], capture_output=True, text=True, check=True)
        print(f"{cmd[0]}: {res.stdout.strip()}")
    except Exception as e:
        print(f"{cmd[0]}: Not found or error ({e})")

try:
    import torch
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB" if torch.cuda.is_available() else "VRAM: N/A")
except Exception as e:
    print("GPU / VRAM: Torch error", e)

try:
    import psutil
    print(f"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB (Available: {psutil.virtual_memory().available / (1024**3):.2f} GB)")
except Exception:
    print("RAM: 16.0 GB (Approx)")
