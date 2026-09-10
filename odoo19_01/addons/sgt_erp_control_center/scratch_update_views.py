import re
import os

filepath = '/home/maitrinh/odoo/odoo19_01/addons/sgt_erp_control_center/views/theme_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We only want to replace fields inside the <form> view, specifically inside <page> tags.
# A regex to find <field name="xxx" widget="color"/> and replace it with:
# <label for="xxx"/>
# <div class="o_row">
#     <field name="xxx"/>
#     <field name="xxx" widget="color" nolabel="1"/>
# </div>

def replacer(match):
    indent = match.group(1)
    field_name = match.group(2)
    return f'{indent}<label for="{field_name}"/>\n{indent}<div class="o_row">\n{indent}    <field name="{field_name}"/>\n{indent}    <field name="{field_name}" widget="color" nolabel="1"/>\n{indent}</div>'

# Regex: find lines like `[whitespace]<field name="some_name" widget="color"/>`
# We'll apply this only to the form view block to avoid messing up tree/kanban views.
# So let's split the file or just be careful. 
# Wait, list view also has primary_color and navbar_bg with widget="color", but they are on a single line.
# `<field name="primary_color" widget="color"/>` in `<list>` or `<kanban>` doesn't have `<label>`, so we shouldn't replace them.
# The ones we want to replace are inside `<page ...>` or `<group>`.

# Let's write a smarter regex that checks if the field is inside a <group>.
# Actually, the indent for fields inside groups is usually 40 spaces: `                                        <field ...`
# Let's just find any `<field name="([^"]+)" widget="color"/>` that starts with at least 32 spaces.

new_content = re.sub(r'( {32,})<field name="([^"]+)" widget="color"/>', replacer, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated theme_views.xml")
