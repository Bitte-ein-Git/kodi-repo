import os
import datetime
import subprocess
import html
import sys

# --- Configuration ---
ROOT_DIR = '.'  # Directory where the script is run
# Items to ignore in listings and traversal
EXCLUDE_ITEMS = ['.git', '.github', '.gitignore', 'html_generator.py', 'README.md', '__pycache__', 'index.html'] # Added 'index.html' generally
GITHUB_REPO_URL = "https://github.com/Bitte-ein-Git/kodi-repo" # Optional: URL for the README link

# Folders containing addons where we stop descending *inside* the addon folder
ADDON_PARENT_FOLDERS = ['repo', 'zips']
# Specific path where addons are one level deeper and pruning happens at depth 3
SPECIAL_ADDON_PATH_PREFIX = ['repo', 'zips'] # Corresponds to "repo/zips/"

# --- HTML template for subdirectory index.html ---
# (Keep the SUBDIR_INDEX_HTML_TEMPLATE template from the previous version)
SUBDIR_INDEX_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Index of /{current_path}</title>
    <style>
        body {{ font-family: sans-serif; margin: 2em; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        a {{ text-decoration: none; color: #0066cc; }}
        a:hover {{ text-decoration: underline; }}
        .dir {{ font-weight: bold; }}
        /* Align size and date columns to the right */
        td.size, td.date {{ white-space: nowrap; text-align: right; padding-left: 2em; }}
        th.size, th.date {{ text-align: right; padding-left: 2em; }} /* Align headers too */
    </style>
</head>
<body>
    <h1>Index of /{current_path}</h1>
    <table>
        <tr><th>Name</th><th class="size">Size</th><th class="date">Last modified</th></tr>
        <tr><td class="dir"><a href="../">../</a></td><td class="size">--</td><td class="date">--</td></tr>
        {table_rows}
    </table>
</body>
</html>
"""

def format_size(size_bytes):
    """Converts bytes into a human-readable format (KB, MB, GB)."""
    if size_bytes is None:
        return "--"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.1f} MB"
    else:
        return f"{size_bytes/1024**3:.1f} GB"

def get_git_last_modified(path):
    """Tries to get the last modified date via Git, falls back to OS."""
    abs_path = os.path.abspath(path)
    repo_dir = None
    try:
        is_windows = sys.platform.startswith('win')
        git_root_result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True, cwd=os.path.dirname(abs_path) or '.',
            shell=is_windows
        )
        repo_dir = git_root_result.stdout.strip()

        relative_path_to_repo = os.path.relpath(abs_path, start=repo_dir)
        git_path = relative_path_to_repo.replace(os.path.sep, '/')

        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cI', '--', git_path],
            capture_output=True, text=True, check=True, cwd=repo_dir,
            startupinfo=None, shell=is_windows
        )
        iso_date_str = result.stdout.strip()

        if iso_date_str:
            if iso_date_str.endswith('Z'):
                 iso_date_str = iso_date_str[:-1] + '+00:00'
            try:
                if sys.version_info < (3, 7) and ':' == iso_date_str[-3:-2]:
                   no_colon_iso_date_str = iso_date_str[:-3]+iso_date_str[-2:]
                   dt_object = datetime.datetime.strptime(no_colon_iso_date_str, '%Y-%m-%dT%H:%M:%S%z')
                else:
                    dt_object = datetime.datetime.fromisoformat(iso_date_str)
                return dt_object.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                 print(f"  Warning: Could not parse Git date '{iso_date_str}' for {git_path}. Falling back.")
                 pass
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, OSError):
        pass

    try:
        mtime = os.path.getmtime(abs_path)
        dt_object = datetime.datetime.fromtimestamp(mtime)
        return dt_object.strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "--"

def generate_index_files(root_dir):
    """Generates index.html for subdirectories, skipping the root, with depth limits."""
    abs_root_dir = os.path.abspath(root_dir)
    print(f"Starting generation in directory: {abs_root_dir}")
    print(f"Skipping index.html generation for the root directory: {abs_root_dir}")

    dir_list_wrapper = [None]

    for current_dir, dirs, files in os.walk(root_dir, topdown=True):
        dir_list_wrapper[0] = dirs
        abs_current_dir = os.path.abspath(current_dir)

        # --- Skip processing the root directory itself for index generation ---
        if abs_current_dir == abs_root_dir:
            print("  Processing root directory (only for traversal)...")
            # Filter dirs and files in root to continue traversal correctly
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in EXCLUDE_ITEMS]
            # No need to process files or generate index for root
            continue # Move to the next directory in os.walk

        # --- Process subdirectories ---
        relative_path_os = os.path.relpath(abs_current_dir, abs_root_dir)
        depth = 0
        path_components = []
        relative_path_display = ""
        if relative_path_os != '.':
            relative_path_norm = relative_path_os.replace(os.path.sep, '/')
            path_components = relative_path_norm.split('/')
            depth = len(path_components)
            relative_path_display = relative_path_norm

        print(f"  Processing: {abs_current_dir} (Depth: {depth})")

        # --- Filter directories and files ---
        original_dirs = list(dirs)
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in EXCLUDE_ITEMS]
        files = [f for f in files if not f.startswith('.') and f not in EXCLUDE_ITEMS and f != 'index.html'] # Exclude index.html from listing

        # --- Depth Pruning Logic ---
        prune_children = False
        if depth > 0:
            is_special_path_prefix = (path_components[:len(SPECIAL_ADDON_PATH_PREFIX)] == SPECIAL_ADDON_PATH_PREFIX)
            if depth == 2 and path_components[0] in ADDON_PARENT_FOLDERS and not is_special_path_prefix:
                prune_children = True
                print(f"    -> Is Addon folder type 1 ('{path_components[0]}/<addon>'). Pruning children.")
            elif depth == 3 and is_special_path_prefix:
                 prune_children = True
                 print(f"    -> Is Addon folder type 2 ('repo/zips/<addon>'). Pruning children.")

        if prune_children:
            print(f"       (Will not descend into subdirectories of: {abs_current_dir})")
            dirs[:] = []

        # --- Collect data for index ---
        items_data = []
        current_level_dirs = dir_list_wrapper[0]
        for name in sorted(current_level_dirs):
            path = os.path.join(current_dir, name)
            items_data.append({
                'name': name + '/',
                'path': path,
                'is_dir': True,
                'size': None,
                'modified_date': get_git_last_modified(path)
            })

        for name in sorted(files):
            path = os.path.join(current_dir, name)
            size = None
            try:
                size = os.path.getsize(path)
            except OSError:
                pass
            items_data.append({
                'name': name,
                'path': path,
                'is_dir': False,
                'size': size,
                'modified_date': get_git_last_modified(path)
            })

        # --- Generate HTML Table Rows (only needed for subdirs now) ---
        table_rows_html = ""
        # Add parent directory link (always needed for subdirs)
        table_rows_html += '<tr><td class="dir"><a href="../">../</a></td><td class="size">--</td><td class="date">--</td></tr>\n'

        for item in items_data:
            safe_name = html.escape(item['name'])
            css_class = 'dir' if item['is_dir'] else ''
            size_str = format_size(item['size'])
            date_str = item['modified_date']
            table_rows_html += f'<tr><td class="{css_class}"><a href="{safe_name}">{safe_name}</a></td><td class="size">{size_str}</td><td class="date">{date_str}</td></tr>\n'

        # --- Generate HTML for Subdirectory ---
        index_file_path = os.path.join(current_dir, 'index.html')
        final_html = SUBDIR_INDEX_HTML_TEMPLATE.format(
            current_path=html.escape(relative_path_display),
            table_rows=table_rows_html
        )

        # --- Write index.html file ---
        try:
            with open(index_file_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"    -> '{index_file_path}' created/updated.")
        except IOError as e:
            print(f"    Error writing '{index_file_path}': {e}")

    print("Generation finished.")


# --- Start script ---
if __name__ == "__main__":
    generate_index_files(ROOT_DIR)
