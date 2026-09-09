import os, re

def find_discord():
    js_path = os.path.expandvars(r'%AppData%\LuaToolsGui\plugin\public\luatools.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        for m in re.finditer(r'https?://[^\s"\'`<>]*discord[^\s"\'`<>]*', text):
            print(f"Found URL: {m.group(0)} at pos {m.start()}")

if __name__ == '__main__':
    find_discord()
