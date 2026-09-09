import os, base64, re

icon_path = r'C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\src\LuaToolsGui\gentleman-icon.png'
with open(icon_path, 'rb') as f:
    icon_b64 = base64.b64encode(f.read()).decode('ascii')
data_url = f'data:image/png;base64,{icon_b64}'

js_path = r'C:\Users\kilic\AppData\Roaming\LuaToolsGui\plugin\public\luatools.js'
if os.path.exists(js_path):
    with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
        js = f.read()
    
    # Replace data:image/png;base64,...
    js = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+', data_url, js)
    js = js.replace('"LuaTools/luatools-icon.png"', f'"{data_url}"')
    js = js.replace("'LuaTools/luatools-icon.png'", f"'{data_url}'")
    js = js.replace('"luatools-icon.png"', f'"{data_url}"')
    js = js.replace("'luatools-icon.png'", f"'{data_url}'")
    
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js)
    print('Updated luatools.js with GentlemanStation icon dataUrl!')

for target in [
    r'C:\Users\kilic\AppData\Roaming\LuaToolsGui\plugin\public\luatools-icon.png',
    r'C:\Users\kilic\AppData\Roaming\LuaToolsGui\plugin\luatools-icon.png',
    r'C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\dist\luatools-icon.png',
    r'C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\dist\gentleman-icon.png'
]:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(icon_path, 'rb') as src, open(target, 'wb') as dst:
        dst.write(src.read())
    print('Copied icon to:', target)
