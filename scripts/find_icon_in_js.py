with open(r'C:\Users\kilic\AppData\Roaming\LuaToolsGui\plugin\public\luatools.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

for m in re.finditer(r'img\.src\s*=|createElement\(["\']img["\']\)|GetIconDataUrl|luatools-icon', text):
    s = max(0, m.start() - 120)
    e = min(len(text), m.end() + 250)
    print('='*40)
    print(text[s:e].encode('ascii', errors='replace').decode('ascii'))
