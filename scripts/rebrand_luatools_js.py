import os
import re
import base64

def main():
    p = os.path.expandvars(r'%AppData%\LuaToolsGui\plugin\public\luatools.js')
    if not os.path.exists(p):
        print("luatools.js not found in AppData")
        return

    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()

    icon_path = os.path.expandvars(r'%AppData%\LuaToolsGui\plugin\public\luatools-icon.png')
    if os.path.exists(icon_path):
        with open(icon_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        new_icon_data_url = f"data:image/png;base64,{b64}"
    else:
        new_icon_data_url = None

    # Let's inspect data url
    if new_icon_data_url:
        content = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+', new_icon_data_url, content)

    # Replace user-facing brand strings while preserving code structure
    # In Turkish: "LuaTools ile Ekle" -> "GentlemanStation ile Ekle", "LuaTools - Menü" / "LuaTools · Menü" -> "GentlemanStation · Menü"
    content = content.replace("LuaTools · Menü", "GentlemanStation · Menü")
    content = content.replace("LuaTools - Menü", "GentlemanStation - Menü")
    content = content.replace("LuaTools · Menu", "GentlemanStation · Menu")
    content = content.replace("LuaTools - Menu", "GentlemanStation - Menu")
    content = content.replace("LuaTools · Fixes Menu", "GentlemanStation · Fixes Menu")
    content = content.replace("LuaTools · AIO Fixes Menu", "GentlemanStation · AIO Fixes Menu")
    content = content.replace("LuaTools · Added Games", "GentlemanStation · Added Games")
    content = content.replace("LuaTools ile Ekle", "GentlemanStation ile Ekle")
    content = content.replace("Add via LuaTools", "Add via GentlemanStation")
    content = content.replace("Add to LuaTools", "Add to GentlemanStation")
    content = content.replace("Remove via LuaTools", "Remove via GentlemanStation")
    content = content.replace("LuaTools'tan Kaldır", "GentlemanStation'dan Kaldır")
    content = content.replace('"LuaTools"', '"GentlemanStation"')
    content = content.replace('\\"LuaTools\\"', '\\"GentlemanStation\\"')
    content = content.replace("LuaTools Fixes", "GentlemanStation Fixes")
    content = content.replace("LuaTools Settings", "GentlemanStation Settings")

    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Successfully rebranded luatools.js! Length:", len(content))

if __name__ == '__main__':
    main()
