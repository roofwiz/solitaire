import json
import os

class Settings:
    _instance = None
    
    def __init__(self, config_file='assets.json'):
        self.config = {}
        self.load(config_file)
        
    def load(self, filename):
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.config = json.load(f)
                print(f"DEBUG: Loaded settings from {filename}")
            else:
                print(f"ERROR: Settings file {filename} not found!")
                self.config = {}
        except Exception as e:
            print(f"ERROR loading settings: {e}")
            self.config = {}
            
    def get_asset_path(self, asset_type, key):
        """
        Returns relative path like 'assets/marioallsprite.png' or 'sounds/rotate.wav'
        asset_type: 'images', 'sounds', 'fonts'
        """
        filename = self.config.get(asset_type, {}).get(key)
        if not filename: return None
        
        folder_map = {
            'images': 'assets',
            'fonts': 'assets',
            'sounds': 'sounds'
        }
        return os.path.join(folder_map.get(asset_type, ''), filename)

    def get_sprite_coords(self, char_name):
        return self.config.get('sprite_coords', {}).get(char_name, {})

# Global instance
game_settings = Settings()
