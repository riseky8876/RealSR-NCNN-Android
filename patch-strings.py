#!/usr/bin/env python3
"""Patch strings.xml — add colorize string and all strings needed by newer app version"""
import sys, re, os

path = sys.argv[1]
with open(path) as f:
    content = f.read()

new_entries = [
    ('string', 'colorize', 'Colorize'),
    ('string', 'dir_menu_entry', 'Batch Process'),
    ('string', 'dir_process_title', 'Batch Process'),
    ('string', 'dir_input_label', 'Input Directory'),
    ('string', 'dir_select_btn', 'Select'),
    ('string', 'dir_input_hint', 'Select input directory'),
    ('string', 'dir_output_label', 'Output Directory'),
    ('string', 'dir_output_hint', 'Select output directory'),
    ('string', 'dir_auto_output_label', 'Auto output directory'),
    ('string', 'dir_model_label', 'Model'),
    ('string', 'dir_start_btn', 'Start'),
    ('string', 'dir_stop_btn', 'Stop'),
    ('string', 'dir_log_hint', 'Log will appear here'),
    ('string', 'dir_input_invalid', 'Invalid input directory'),
    ('string', 'dir_input_path_error', 'Input path error'),
    ('string', 'dir_output_path_error', 'Output path error'),
    ('string', 'dir_model_error', 'Model error'),
    ('string', 'dir_no_selected', 'No file selected'),
    ('string', 'dir_no_supported_commands', 'No supported commands'),
    ('string', 'dir_service_error', 'Service error'),
    ('string', 'dir_log_starting', 'Starting...'),
    ('string', 'dir_log_complete', 'Complete'),
    ('string', 'dir_log_output_to', 'Output to:'),
    ('string', 'dir_file_count', 'File count:'),
    ('string', 'dir_select_input_prompt', 'Select input folder'),
    ('string', 'dir_select_output_prompt', 'Select output folder'),
    ('string', 'dir_auto_output_format', 'Auto'),
    ('string', 'dir_output_format', 'Output format'),
    ('string', 'hide_programs_title', 'Hide programs'),
    ('string', 'hide_realsr', 'Hide RealSR'),
    ('string', 'hide_srmd', 'Hide SRMD'),
    ('string', 'hide_realcugan', 'Hide RealCUGAN'),
    ('string', 'hide_waifu', 'Hide Waifu2x'),
    ('string', 'hide_resize', 'Hide Resize'),
    ('string', 'hide_magick', 'Hide ImageMagick'),
    ('string', 'hide_anime', 'Hide Anime4k'),
    ('string', 'hide_mnnsr', 'Hide MNNSR'),
    ('string', 'save_name', 'Save name'),
    ('string', 'save_name3', 'Save name (3rd)'),
]

arrays = {
    'dir_output_format': ['jpg', 'png', 'webp'],
    'name3': ['Default', 'Custom', 'Date'],
}

inject = ''
for tag, name, value in new_entries:
    if f'name="{name}"' not in content:
        inject += f'    <string name="{name}">{value}</string>\n'
        print(f'  + {name}')
    else:
        print(f'  = {name} (exists)')

for name, items in arrays.items():
    if f'name="{name}"' not in content:
        inject += f'    <string-array name="{name}">\n'
        for item in items:
            inject += f'        <item>{item}</item>\n'
        inject += f'    </string-array>\n'
        print(f'  + array:{name}')
    else:
        print(f'  = array:{name} (exists)')

if inject:
    content = content.replace('</resources>', inject + '</resources>')
    with open(path, 'w') as f:
        f.write(content)
    print('strings.xml patched OK')
else:
    print('strings.xml already up to date')
