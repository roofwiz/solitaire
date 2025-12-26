import http.server
import socketserver
import urllib.parse
import subprocess
import os
import webbrowser
import sys
import json

PORT = 8080

# 1. Regenerate Guide (Skipped for stability)
# print("Regenerating Asset Browser HTML...")
# subprocess.run([sys.executable, "generate_asset_browser.py"])

# Load Assets for validation
try:
    with open('assets.json', 'r') as f:
        ASSETS = json.load(f)
except:
    ASSETS = {}

class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Handle Edit Request
        if self.path.startswith("/edit"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            cat = params.get('cat', [None])[0]
            spr = params.get('spr', [None])[0]
            
            if cat and spr:
                target_spr = spr
                # Resolve smart name
                coords = ASSETS.get('sprite_coords', {}).get(cat, {})
                if spr in coords:
                    target_spr = spr
                elif f"{spr}_1" in coords:
                    target_spr = f"{spr}_1"
                
                print(f"Opening Editor for {cat}/{target_spr}...")
                # Use 'py' launcher to avoid path issues
                subprocess.Popen(["py", "asset_editor.py", cat, target_spr])
            
            # Return 204 No Content (so page doesn't reload)
            self.send_response(204)
            self.end_headers()
            return
            
        elif self.path.startswith("/update_slot"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            sym = params.get('sym', [None])[0]
            cat = params.get('cat', [None])[0]
            spr = params.get('spr', [None])[0]
            
            if sym and cat and spr:
                print(f"Updating Slot: {sym} -> {cat}/{spr}")
                # Update src/slot_machine.py
                try:
                    p = "src/slot_machine.py"
                    with open(p, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    found = False
                    # Look for: 'sym': (..., ...)
                    # Regex might be safer given formatting variations
                    import re
                    pattern = re.compile(rf"'{sym}':\s*\('.+',\s*'.+'\)")
                    replacement = f"'{sym}': ('{cat}', '{spr}')"
                    
                    for line in lines:
                        if ignore_next := False: pass # logic placehold
                        
                        if f"'{sym}':" in line and not found:
                            # Simple string replacement if on one line
                            if re.search(pattern, line):
                                new_line = re.sub(pattern, replacement, line)
                                new_lines.append(new_line)
                                found = True
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                            
                    with open(p, 'w') as f:
                        f.writelines(new_lines)
                        
                    print("File updated.")
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                    
                    # Optional: Restart slots if running? 
                    # Complex to manage detached content.
                    return
                except Exception as e:
                    print(f"Update failed: {e}")
                    self.send_error(500, str(e))
                    return

        return super().do_GET()

print(f"Starting Asset Studio on http://localhost:{PORT}")
webbrowser.open(f"http://localhost:{PORT}/asset_browser.html")

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), StudioHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
