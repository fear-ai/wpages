#!/usr/bin/env python3
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
# Windows-invalid filename characters plus ASCII control bytes (0x00-0x1F, 0x7F).
INVALID_CHARS_RE = re.compile("[<>:\"/\\\\|?*\x00-\x1F\x7F]")
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff"}
BLOCKED_SCHEMES = {
    "about",
    "blob",
    "chrome",
    "chrome-extension",
    "data",
    "file",
    "filesystem",
    "javascript",
    "moz-extension",
    "vbscript",
}


@dataclass
class FilterCounts:
    re_control: int = 0
    re_zero: int = 0
    re_tab: int = 0
    re_nl: int = 0
    re_non_ascii: int = 0
    rep_chars: int = 0


@dataclass
class SanitizeCounts:
    blocks_rm: int = 0
    comments_rm: int = 0
    tags_rm: int = 0
    entities_rm: int = 0
    anchors_conv: int = 0
    images_conv: int = 0
    headings_conv: int = 0
    lists_conv: int = 0
    tables_conv: int = 0
    blocks_conv: int = 0
    blocked_scheme_links: int = 0
    blocked_scheme_images: int = 0
    other_scheme_links: int = 0
    other_scheme_images: int = 0


def decode_mysql_escapes(text: str) -> str:
    if not text:
        return ""
    return text.replace("\\r", "\n").replace("\\n", "\n").replace("\\t", "\t")


def prepare_output_dir(out_dir: Path, *, label: str = "output") -> None:
    if out_dir.exists() and not out_dir.is_dir():
        raise OSError(format_path_not_dir(label, out_dir))
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(format_dir_create_error(label, out_dir, exc))


def write_text_check(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    errors: str | None = None,
    label: str = "output",
) -> None:
    if path.exists() and path.is_dir():
        raise OSError(format_path_is_dir(label, path))
    try:
        if errors is None:
            path.write_text(text, encoding=encoding)
        else:
            path.write_text(text, encoding=encoding, errors=errors)
    except OSError as exc:
        raise OSError(format_file_write_error(label, path, exc))


def make_dump_notags_sink(
    path: Path,
    *,
    encoding: str,
    errors: str | None,
) -> Callable[[str], None]:
    def sink(text: str) -> None:
        write_text_check(
            path,
            text,
            encoding=encoding,
            errors=errors,
            label="dump notags",
        )

    return sink


def write_bytes_check(
    path: Path,
    data: bytes,
    *,
    label: str = "output",
) -> None:
    if path.exists() and path.is_dir():
        raise OSError(format_path_is_dir(label, path))
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise OSError(format_file_write_error(label, path, exc))


def open_text_check(
    path: Path,
    *,
    mode: str = "r",
    encoding: str = "utf-8",
    errors: str = "replace",
    newline: str | None = None,
    label: str = "input",
):
    try:
        return path.open(
            mode,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise OSError(format_file_read_error(label, path, exc))


def read_text_check(
    path: Path,
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
    label: str = "input",
) -> str:
    handle = open_text_check(
        path,
        mode="r",
        encoding=encoding,
        errors=errors,
        label=label,
    )
    with handle:
        return handle.read()


def format_path_not_dir(label: str, path: Path) -> str:
    return f"{label} path is not a directory: {path}"


def format_dir_not_dir(label: str, path: Path) -> str:
    return f"{label} is not a directory: {path}"


def format_dir_create_error(label: str, path: Path, exc: OSError) -> str:
    return f"{label} directory could not be created: {path} ({exc})"


def format_path_is_dir(label: str, path: Path) -> str:
    return f"{label} path is a directory: {path}"


def format_file_write_error(label: str, path: Path, exc: OSError) -> str:
    return f"{label} file could not be written: {path} ({exc})"


def format_file_read_error(label: str, path: Path, exc: OSError) -> str:
    return f"{label} file could not be read: {path} ({exc})"


def filter_characters(
    text: str,
    replace_char: str,
    *,
    keep_newlines: bool = True,
    keep_tabs: bool = True,
    ascii_only: bool = True,
    counts: FilterCounts | None = None,
) -> str:
    normalized = unicodedata.normalize("NFKD", text) if ascii_only else text
    out: list[str] = []
    last_replaced = False
    for ch in normalized:
        if ch == "\n":
            if keep_newlines:
                out.append("\n")
                last_replaced = False
            else:
                if counts is not None:
                    counts.re_nl += 1
                if replace_char and not last_replaced:
                    out.append(replace_char)
                    if counts is not None:
                        counts.rep_chars += 1
                    last_replaced = True
            continue
        if ch == "\t":
            if keep_tabs:
                out.append("\t")
                last_replaced = False
            else:
                if counts is not None:
                    counts.re_tab += 1
                if replace_char and not last_replaced:
                    out.append(replace_char)
                    if counts is not None:
                        counts.rep_chars += 1
                    last_replaced = True
            continue
        code = ord(ch)
        is_control = code < 0x20 or code == 0x7F
        is_zero_width = ch in ZERO_WIDTH
        is_non_ascii = code >= 0x80
        if is_control or is_zero_width or (ascii_only and is_non_ascii):
            if counts is not None:
                if is_control:
                    counts.re_control += 1
                elif is_zero_width:
                    counts.re_zero += 1
                elif is_non_ascii:
                    counts.re_non_ascii += 1
            if replace_char and not last_replaced:
                out.append(replace_char)
                if counts is not None:
                    counts.rep_chars += 1
                last_replaced = True
            continue
        out.append(ch)
        last_replaced = False
    return "".join(out)


def _normalize_filename_base(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    normalized = INVALID_CHARS_RE.sub("-", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.strip(" .")
    return normalized


def _truncate_base(base: str, max_len: int) -> str:
    if max_len < 1:
        return ""
    if len(base) > max_len:
        base = base[:max_len]
    return base.rstrip(" .")


def _apply_suffix(base: str, suffix_num: int, max_base_len: int) -> str:
    suffix = f"_{suffix_num}"
    max_root_len = max_base_len - len(suffix)
    root = _truncate_base(base, max_root_len) if max_root_len > 0 else ""
    if not root:
        root = _truncate_base("page", max_root_len)
    return f"{root}{suffix}"


def safe_filename(
    name: str,
    ext: str = ".txt",
    *,
    existing: set[str] | None = None,
) -> str:
    ext = ext or ""
    max_len = 255
    max_base_len = max_len - len(ext)
    if max_base_len < 1:
        ext = ext[:max_len]
        max_base_len = max_len - len(ext)
    base = _normalize_filename_base(name)
    base = _truncate_base(base, max_base_len)
    if not base:
        base = _truncate_base("page", max_base_len)
    base_root = base
    counter = 0
    if base_root.upper() in WINDOWS_RESERVED_NAMES:
        counter = 1
        base = _apply_suffix(base_root, counter, max_base_len)

    filename = f"{base}{ext}"
    if existing:
        while filename in existing:
            counter += 1
            base = _apply_suffix(base_root, counter, max_base_len)
            filename = f"{base}{ext}"

    return filename


def strip_footer(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip().lower() in {"resources", "community"}:
            stripped = "\n".join(lines[:idx]).rstrip()
            return f"{stripped}\n" if stripped else ""
    return text
