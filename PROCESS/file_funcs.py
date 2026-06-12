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


def match_grib_variable(file_path, file_names, grib_names):
    """
    Return the matching GRIB variable name for a file path.

    This looks for any value in file_names that is contained in the file's
    basename. When a match is found, the function uses the corresponding
    key to look up the GRIB name in grib_names.

    Returns a tuple of (file_key, grib_name), or (None, None) if no match.
    """
    basename = os.path.basename(file_path).lower()
    for key, file_value in file_names.items():
        if str(file_value).lower() in basename:
            return key, grib_names.get(key)

    print(f"Warning: no matching file_names entry found for '{file_path}'")
    return None, None