import os
import glob
import re

res_dir = os.path.join("src", "LuaToolsGui", "Resources")

plugin_translations = {
    "Strings.resx": "Plugins",
    "Strings.tr.resx": "Eklentiler",
    "Strings.de.resx": "Plugins",
    "Strings.fr.resx": "Extensions",
    "Strings.es.resx": "Plugins",
    "Strings.es-419.resx": "Plugins",
    "Strings.it.resx": "Plugin",
    "Strings.pt-BR.resx": "Plugins",
    "Strings.pt-PT.resx": "Plugins",
    "Strings.ru.resx": "Плагины",
    "Strings.uk.resx": "Плагіни",
    "Strings.pl.resx": "Wtyczki",
    "Strings.nl.resx": "Plug-ins",
    "Strings.cs.resx": "Doplňky",
    "Strings.hu.resx": "Bővítmények",
    "Strings.ro.resx": "Pluginuri",
    "Strings.el.resx": "Πρόσθετα",
    "Strings.da.resx": "Plugins",
    "Strings.sv.resx": "Insticksprogram",
    "Strings.fi.resx": "Lisäosat",
    "Strings.nb.resx": "Programtillegg",
    "Strings.bg.resx": "Приставки",
    "Strings.id.resx": "Plugin",
    "Strings.vi.resx": "Tiện ích mở rộng",
    "Strings.th.resx": "ปลั๊กอิน",
    "Strings.ja.resx": "プラグイン",
    "Strings.ko.resx": "플러그인",
    "Strings.zh-Hans.resx": "插件",
    "Strings.zh-Hant.resx": "外掛程式",
    "Strings.ar.resx": "الإضافات",
}

for filename in os.listdir(res_dir):
    if not filename.endswith(".resx") or not filename.startswith("Strings"):
        continue
    filepath = os.path.join(res_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Add Nav_Plugins if not present
    if 'name="Nav_Plugins"' not in content:
        val = plugin_translations.get(filename, "Plugins")
        tag = f'  <data name="Nav_Plugins" xml:space="preserve"><value>{val}</value></data>\n</root>'
        content = content.replace("</root>", tag)

    # If Turkish, ensure natural phrases
    if filename == "Strings.tr.resx":
        content = re.sub(r'<data name="Nav_Add" xml:space="preserve"><value>.*?</value></data>', '<data name="Nav_Add" xml:space="preserve"><value>Oyun Ekle</value></data>', content)
        content = re.sub(r'<data name="Nav_Manage" xml:space="preserve"><value>.*?</value></data>', '<data name="Nav_Manage" xml:space="preserve"><value>Oyunları Yönet</value></data>', content)
        content = re.sub(r'<data name="Nav_Mode" xml:space="preserve"><value>.*?</value></data>', '<data name="Nav_Mode" xml:space="preserve"><value>Modlar</value></data>', content)
        content = re.sub(r'<data name="Nav_Builds" xml:space="preserve"><value>.*?</value></data>', '<data name="Nav_Builds" xml:space="preserve"><value>Depolar</value></data>', content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Translations updated successfully.")
