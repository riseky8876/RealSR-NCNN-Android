#!/usr/bin/env python3
import sys, re

path = sys.argv[1]
with open(path) as f:
    content = f.read()

# Print all existing string names so we can see what's already there
existing = re.findall(r'name="([^"]+)"', content)
print("=== Existing strings ===")
for e in sorted(existing):
    print(f"  {e}")
print(f"Total: {len(existing)}")

# Add ALL strings referenced by the layouts — safe to add duplicates
# because we check 'name=X' not in content before adding
new_entries = [
    'colorize', 'Colorize',
    'dir_menu_entry', 'Batch Process',
    'dir_process_title', 'Batch Process',
    'dir_input_label', 'Input Directory',
    'dir_select_btn', 'Select',
    'dir_input_hint', 'Select input directory',
    'dir_output_label', 'Output Directory',
    'dir_output_hint', 'Select output directory',
    'dir_auto_output_label', 'Auto output directory',
    'dir_model_label', 'Model',
    'dir_start_btn', 'Start',
    'dir_stop_btn', 'Stop',
    'dir_log_hint', 'Log will appear here',
    'dir_input_invalid', 'Invalid input directory',
    'dir_input_path_error', 'Input path error',
    'dir_output_path_error', 'Output path error',
    'dir_model_error', 'Model error',
    'dir_no_selected', 'No file selected',
    'dir_no_supported_commands', 'No supported commands',
    'dir_service_error', 'Service error',
    'dir_log_starting', 'Starting...',
    'dir_log_complete', 'Complete',
    'dir_log_output_to', 'Output to:',
    'dir_file_count', 'File count:',
    'dir_select_input_prompt', 'Select input folder',
    'dir_select_output_prompt', 'Select output folder',
    'dir_auto_output_format', 'Auto',
    'dir_output_format', 'Output format',
    'hide_programs_title', 'Hide programs',
    'hide_realsr', 'Hide RealSR',
    'hide_srmd', 'Hide SRMD',
    'hide_realcugan', 'Hide RealCUGAN',
    'hide_waifu', 'Hide Waifu2x',
    'hide_waifu2x', 'Hide Waifu2x',
    'hide_resize', 'Hide Resize',
    'hide_magick', 'Hide ImageMagick',
    'hide_anime', 'Hide Anime4k',
    'hide_anime4k', 'Hide Anime4k',
    'hide_mnnsr', 'Hide MNNSR',
    'save_name', 'Save name',
    'save_name3', 'Save name (3rd)',
]

# Scan layout files for ANY missing @string/ references
import os, glob
layout_dir = os.path.dirname(os.path.dirname(path)) + '/layout'
layout_strings = set()
if os.path.exists(layout_dir):
    for xml in glob.glob(layout_dir + '/*.xml'):
        with open(xml) as f:
            refs = re.findall(r'@string/([a-z0-9_]+)', f.read())
            layout_strings.update(refs)

print(f"\n=== Strings referenced in layouts ({len(layout_strings)}) ===")
missing_from_file = [s for s in sorted(layout_strings) if f'name="{s}"' not in content]
print(f"Missing: {missing_from_file}")

# Build inject block
inject = ''
it = iter(new_entries)
for name, value in zip(it, it):
    if f'name="{name}"' not in content:
        inject += f'    <string name="{name}">{value}</string>\n'
        print(f'  + {name}')

# Add any layout-referenced strings not yet covered
for name in missing_from_file:
    if f'name="{name}"' not in content and f'name="{name}"' not in inject:
        inject += f'    <string name="{name}">{name.replace("_", " ").title()}</string>\n'
        print(f'  + {name} (auto)')

# Arrays
for arr_name, items in [('dir_output_format', ['jpg','png','webp']), ('name3', ['Default','Custom','Date'])]:
    if f'name="{arr_name}"' not in content:
        inject += f'    <string-array name="{arr_name}">\n'
        for item in items:
            inject += f'        <item>{item}</item>\n'
        inject += f'    </string-array>\n'
        print(f'  + array:{arr_name}')

if inject:
    content = content.replace('</resources>', inject + '</resources>')
    with open(path, 'w') as f:
        f.write(content)
    print('\nstrings.xml patched OK')
else:
    print('\nstrings.xml already up to date')
