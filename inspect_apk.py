
import zipfile
import os

apk_path = r"c:\Users\eric\React Projects\Mario-Tetris-main\build\web\mario-tetris-main.apk"

if not os.path.exists(apk_path):
    print(f"APK not found at {apk_path}")
    exit()

try:
    with zipfile.ZipFile(apk_path, 'r') as z:
        print(f"Inspecting {apk_path}...")
        files = []
        for info in z.infolist():
            files.append((info.filename, info.file_size))
            
        # Sort by size descending
        files.sort(key=lambda x: x[1], reverse=True)
        
        print("\nTop 20 Largest Files in APK:")
        for name, size in files[:20]:
            print(f"{size/1024/1024:.2f} MB - {name}")

except Exception as e:
    print(f"Error: {e}")
