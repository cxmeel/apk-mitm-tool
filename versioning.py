import os
import re
import sys


VERSION_FILE_NAME = "VERSION"
VERSION_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def get_base_dir():
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return bundle_dir
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_version_file_path():
    return os.path.join(get_base_dir(), VERSION_FILE_NAME)


def validate_version(version):
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(
            f"Invalid version '{version}'. Expected format: v<major>.<minor>.<patch>."
        )
    return version


def parse_version(version):
    match = VERSION_PATTERN.fullmatch(validate_version(version))
    return tuple(int(part) for part in match.groups())


def read_version():
    with open(get_version_file_path(), "r", encoding="utf-8") as version_file:
        return validate_version(version_file.read().strip())
