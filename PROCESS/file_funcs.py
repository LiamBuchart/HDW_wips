import os

def find_files(directory, substring):
    """
    Search for files in the given directory whose names contain the substring.
    Returns a list of matching file paths.
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory '{directory}' does not exist or is not accessible.")

    matches = []
    substring_lower = substring.lower()

    try:
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path) and substring_lower in entry.lower():
                matches.append(full_path)
    except PermissionError:
        print(f"Permission denied while accessing '{directory}'.")
    except OSError as e:
        print(f"Error reading directory '{directory}': {e}")

    return matches