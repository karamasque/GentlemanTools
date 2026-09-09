import os

def run():
    js_path = os.path.expandvars(r'%AppData%\LuaToolsGui\plugin\public\luatools.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        replaces = [
            ("LuaTools \u2022", "GentlemanStation \u2022"),
            ("LuaTools \u00b7", "GentlemanStation \u00b7"),
            ("LuaTools •", "GentlemanStation •"),
            ("LuaTools ·", "GentlemanStation ·"),
            ("LuaTools -", "GentlemanStation -"),
            ("LuaTools:", "GentlemanStation:"),
            ("LuaTools ", "GentlemanStation "),
            ("\"LuaTools\"", "\"GentlemanStation\""),
            ("'LuaTools'", "'GentlemanStation'"),
            ("Lua.Tools", "GentlemanStation"),
            ("Lua Tools", "GentlemanStation"),
            ("LuaTools", "GentlemanStation"),
        ]

        for old, new in replaces:
            content = content.replace(old, new)

        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated AppData luatools.js successfully!")

if __name__ == '__main__':
    run()
