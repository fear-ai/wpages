#!/usr/bin/env python3
import argparse
import html
import re
from collections.abc import Callable
from pathlib import Path

from pages_cli import (
    add_common_args,
    add_dump_args,
    add_filter_args,
    emit_db_warnings,
    error,
    info_page_count,
    load_focus_entries,
    parse_dump_check,
    resolve_filter_args,
    validate_limits,
    warn,
)
from pages_util import (
    BLOCKED_SCHEMES,
    FilterCounts,
    SanitizeCounts,
    decode_mysql_escapes,
    filter_characters,
    make_dump_notags_sink,
    prepare_output_dir,
    write_text_check,
    safe_filename,
    strip_footer,
)
from pages_focus import match_entries

ANCHOR_RE = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
IMG_RE = re.compile(r"(?is)<img\b[^>]*>")
HTTP_SCHEMES = {"http", "https"}
BIDI_CONTROLS = {
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff"}
LIST_TAGS = ("ul", "ol", "li")
TABLE_TAGS = ("table", "tr", "td", "th")


def _extract_attr(tag: str, name: str) -> str:
    pattern = rf'(?i)\b{name}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^"\'>\s]+))'
    match = re.search(pattern, tag)
    if not match:
        return ""
    for group in match.groups():
        if group is not None:
            return group.strip()
    return ""


def _suppress_url_chars(url: str) -> str:
    if not url:
        return ""
    cleaned: list[str] = []
    for ch in url:
        if ch.isspace():
            continue
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            continue
        if ch in ZERO_WIDTH or ch in BIDI_CONTROLS:
            continue
        cleaned.append(ch)
    return "".join(cleaned)


def _get_scheme(url: str) -> str:
    match = re.match(r"(?i)^\s*([a-z][a-z0-9+.-]*):", url)
    if not match:
        return ""
    return match.group(1).lower()


def _mark_scheme_relative(url: str) -> str:
    if url.startswith("//"):
        return f"{{scheme?}}:{url}"
    return url


def _format_missing_scheme(label: str, url: str, title: str) -> str:
    marked = _mark_scheme_relative(url)
    if label:
        if title:
            return f'{label} ({marked} "{title}")'
        return f"{label} ({marked})"
    if title:
        return f'{marked} "{title}"'
    return marked


def _format_scheme_relative(
    label: str,
    url: str,
    title: str,
    counts: SanitizeCounts | None,
    *,
    is_image: bool,
) -> str | None:
    if not url.startswith("//"):
        return None
    if counts is not None:
        if is_image:
            counts.missing_scheme_images += 1
        else:
            counts.missing_scheme_links += 1
    return _format_missing_scheme(label, url, title)


def _count_tags(text: str, tag: str) -> tuple[int, int]:
    open_count = len(re.findall(rf"(?i)<{tag}\b[^>]*>", text))
    close_count = len(re.findall(rf"(?i)</{tag}\s*>", text))
    return open_count, close_count


def _structure_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    list_details: list[str] = []
    for tag in LIST_TAGS:
        open_count, close_count = _count_tags(text, tag)
        if open_count != close_count:
            list_details.append(f"<{tag}> {open_count} != </{tag}> {close_count}")
    if list_details:
        warnings.append("Malformed list structure: " + "; ".join(list_details))
    table_details: list[str] = []
    for tag in TABLE_TAGS:
        open_count, close_count = _count_tags(text, tag)
        if open_count != close_count:
            table_details.append(f"<{tag}> {open_count} != </{tag}> {close_count}")
    if table_details:
        warnings.append("Malformed table structure: " + "; ".join(table_details))
    return warnings


def _strip_inline_tags(text: str) -> str:
    return re.sub(r"(?s)<[^>]+>", " ", text)


def _strip_blocks_comments(text: str, counts: SanitizeCounts | None) -> str:
    text, blocks_rm = re.subn(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    if counts is not None:
        counts.blocks_rm += blocks_rm
    text, comments_rm = re.subn(r"(?s)<!--.*?-->", " ", text)
    if counts is not None:
        counts.comments_rm += comments_rm
    return text


def _extract_anchor_parts(attrs: str, inner: str) -> tuple[str, str, str]:
    url = html.unescape(_extract_attr(attrs, "href")).strip()
    url = _suppress_url_chars(url)
    inner_text = _strip_inline_tags(inner)
    inner_text = html.unescape(inner_text).strip()
    title = html.unescape(_extract_attr(attrs, "title")).strip()
    return url, inner_text, title


def _extract_image_parts(tag: str) -> tuple[str, str, str]:
    src = html.unescape(_extract_attr(tag, "src")).strip()
    src = _suppress_url_chars(src)
    alt = html.unescape(_extract_attr(tag, "alt")).strip()
    title = html.unescape(_extract_attr(tag, "title")).strip()
    return src, alt, title


def _anchor_image_label(inner: str) -> str:
    match = IMG_RE.search(inner)
    if not match:
        return ""
    _, alt, _ = _extract_image_parts(match.group(0))
    return alt or "image"


def _convert_anchor(match: re.Match[str], counts: SanitizeCounts | None = None) -> str:
    attrs = match.group(1) or ""
    inner = match.group(2) or ""
    url, inner_text, title = _extract_anchor_parts(attrs, inner)
    if not inner_text and inner:
        inner_text = _anchor_image_label(inner) or inner_text
    scheme_relative = _format_scheme_relative(
        inner_text,
        url,
        title,
        counts,
        is_image=False,
    )
    if scheme_relative is not None:
        return scheme_relative
    scheme = _get_scheme(url)
    if url and scheme in BLOCKED_SCHEMES:
        label = inner_text or "link"
        if counts is not None:
            counts.blocked_scheme_links += 1
        return f"{{{label}}}"
    if scheme and scheme not in HTTP_SCHEMES:
        if counts is not None:
            counts.other_scheme_links += 1
    if inner_text and url:
        if title:
            return f'{inner_text} ({url} "{title}")'
        return f"{inner_text} ({url})"
    if url:
        if title:
            return f'{url} "{title}"'
        return url
    return inner_text


def _convert_anchor_md(match: re.Match[str], counts: SanitizeCounts | None = None) -> str:
    attrs = match.group(1) or ""
    inner = match.group(2) or ""
    url, inner_text, title = _extract_anchor_parts(attrs, inner)
    scheme_relative = _format_scheme_relative(
        inner_text,
        url,
        title,
        counts,
        is_image=False,
    )
    if scheme_relative is not None:
        return scheme_relative
    scheme = _get_scheme(url)
    if url and scheme in BLOCKED_SCHEMES:
        label = inner_text or "link"
        if counts is not None:
            counts.blocked_scheme_links += 1
        return f"{{{label}}}"
    if scheme and scheme not in HTTP_SCHEMES:
        if counts is not None:
            counts.other_scheme_links += 1
    if not inner_text:
        inner_text = url
    if url:
        if title:
            return f'[{inner_text}]({url} "{title}")'
        return f"[{inner_text}]({url})"
    return inner_text


def _convert_image_md(match: re.Match[str], counts: SanitizeCounts | None = None) -> str:
    tag = match.group(0)
    src, alt, title = _extract_image_parts(tag)
    scheme_relative = _format_scheme_relative(
        alt,
        src,
        title,
        counts,
        is_image=True,
    )
    if scheme_relative is not None:
        return scheme_relative
    scheme = _get_scheme(src)
    if src and scheme in BLOCKED_SCHEMES:
        label = alt or "image"
        if counts is not None:
            counts.blocked_scheme_images += 1
        return f"{{{label}}}"
    if scheme and scheme not in HTTP_SCHEMES:
        if counts is not None:
            counts.other_scheme_images += 1
    if src:
        if title:
            return f'![{alt}]({src} "{title}")'
        return f"![{alt}]({src})"
    if alt:
        return alt
    return ""


def _number_ordered_lists(
    text: str,
    *,
    counts: SanitizeCounts | None = None,
) -> str:
    list_items = 0

    def replace_block(match: re.Match[str]) -> str:
        body = match.group(1)
        count = 0

        def replace_li(_: re.Match[str]) -> str:
            nonlocal count
            nonlocal list_items
            count += 1
            list_items += 1
            prefix = "\n" if count > 1 else ""
            return f"{prefix}{count}. "

        body = re.sub(r"(?i)<li\b[^>]*>", replace_li, body)
        body = re.sub(r"(?i)</li\s*>", "", body)
        return "\n" + body + "\n"

    result = re.sub(r"(?is)<ol\b[^>]*>(.*?)</ol\s*>", replace_block, text)
    if counts is not None:
        counts.lists_conv += list_items
    return result


def _normalize_lines(text: str, table_delim: str) -> str:
    lines = text.split("\n")
    lines = _merge_dangling_markers(lines)
    lines = _drop_list_blank_lines(lines)
    out_lines: list[str] = []
    blank = False
    for line in lines:
        if table_delim == "\t":
            parts = line.split("\t")
            parts = [re.sub(r"[ \t]+", " ", part).strip() for part in parts]
            parts = [
                _separate_adjacent_inline(part, markdown=False) for part in parts
            ]
            line = "\t".join(parts)
        else:
            line = re.sub(r"[ \t]+", " ", line).strip()
            line = _separate_adjacent_inline(line, markdown=False)
        if table_delim and line.startswith(table_delim):
            line = line[len(table_delim) :]
        if not line:
            if not blank:
                out_lines.append("")
                blank = True
            continue
        blank = False
        out_lines.append(line)
    cleaned = "\n".join(out_lines).strip()
    if cleaned:
        cleaned += "\n"
    return cleaned


def _normalize_markdown(text: str) -> str:
    lines = text.split("\n")
    lines = _merge_dangling_markers(lines)
    lines = _drop_list_blank_lines(lines)
    out_lines: list[str] = []
    blank = False
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            out_lines.append(line.strip())
            blank = False
            continue
        if in_code:
            out_lines.append(line.rstrip())
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = _separate_adjacent_inline(line, markdown=True)
        if not line:
            if not blank:
                out_lines.append("")
                blank = True
            continue
        blank = False
        out_lines.append(line)
    cleaned = "\n".join(out_lines).strip()
    if cleaned:
        cleaned += "\n"
    return cleaned


def clean_content(
    text: str,
    *,
    table_delim: str,
    replace_char: str,
    keep_tabs: bool = True,
    keep_newlines: bool = True,
    ascii_only: bool = True,
    raw: bool = False,
    counts: SanitizeCounts | None = None,
    filter_counts: FilterCounts | None = None,
    notags_sink: Callable[[str], None] | None = None,
) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = decode_mysql_escapes(text)

    # Remove scripts, styles, and comments to avoid inline code.
    text = _strip_blocks_comments(text, counts)

    # Preserve link destinations before stripping tags.
    text, anchors_conv = ANCHOR_RE.subn(lambda m: _convert_anchor(m, counts), text)
    if counts is not None:
        counts.anchors_conv += anchors_conv

    # Convert structural tags to line breaks or delimiters.
    text, blocks_conv = re.subn(r"(?i)<br\s*/?>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, headings_conv = re.subn(
        r"(?i)<h([1-6])[^>]*>",
        lambda m: f"\n{'#' * int(m.group(1))} ",
        text,
    )
    if counts is not None:
        counts.headings_conv += headings_conv
    text, blocks_conv = re.subn(r"(?i)</h[1-6]>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text = _number_ordered_lists(text, counts=counts)
    text, lists_conv = re.subn(r"(?i)<li[^>]*>", "- ", text)
    if counts is not None:
        counts.lists_conv += lists_conv
    text, blocks_conv = re.subn(r"(?i)</li>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?i)</?(ul|ol)[^>]*>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text = re.sub(r"\n{2,}- ", "\n- ", text)
    text = re.sub(r"(?i)<tr[^>]*>", "", text)
    text, blocks_conv = re.subn(r"(?i)</tr>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, tables_conv = re.subn(r"(?i)<t[dh][^>]*>", table_delim, text)
    if counts is not None:
        counts.tables_conv += tables_conv
    text = re.sub(r"(?i)</t[dh]>", "", text)
    text = re.sub(r"(?i)</?(table|thead|tbody|tfoot)[^>]*>", "", text)
    text, blocks_conv = re.subn(
        r"(?i)</?(p|div|section|article|header|footer|blockquote|figure|figcaption|form|label|input|textarea|button|pre|code|hr)[^>]*>",
        "\n",
        text,
    )
    if counts is not None:
        counts.blocks_conv += blocks_conv

    # Strip all remaining tags.
    text, tags_rm = re.subn(r"(?s)<[^>]+>", " ", text)
    if counts is not None:
        counts.tags_rm += tags_rm
    if notags_sink is not None:
        notags_sink(text)

    # Decode entities and normalize line endings.
    if counts is not None:
        counts.entities_rm += len(re.findall(r"&[A-Za-z0-9#]+;", text))
    text = html.unescape(text).replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Filter control, zero-width, and non-ASCII characters.
    if not raw:
        text = filter_characters(
            text,
            replace_char,
            keep_tabs=keep_tabs,
            keep_newlines=keep_newlines,
            ascii_only=ascii_only,
            counts=filter_counts,
        )

    return _normalize_lines(text, table_delim)


def clean_md(
    text: str,
    *,
    replace_char: str,
    keep_tabs: bool = True,
    keep_newlines: bool = True,
    ascii_only: bool = True,
    raw: bool = False,
    counts: SanitizeCounts | None = None,
    filter_counts: FilterCounts | None = None,
    notags_sink: Callable[[str], None] | None = None,
) -> str:
    if not text:
        return ""
    # Decode literal escape sequences from mysql -e output.
    text = decode_mysql_escapes(text)

    # Remove scripts, styles, and comments to avoid inline code.
    text = _strip_blocks_comments(text, counts)

    # Code blocks first.
    text, blocks_conv = re.subn(r"(?is)<pre\b[^>]*>\s*<code\b[^>]*>", "\n```\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?is)</code\s*>\s*</pre\s*>", "\n```\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?is)<pre\b[^>]*>", "\n```\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?is)</pre\s*>", "\n```\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv

    # Headings.
    text, headings_conv = re.subn(
        r"(?i)<h([1-6])[^>]*>",
        lambda m: f"\n{'#' * int(m.group(1))} ",
        text,
    )
    if counts is not None:
        counts.headings_conv += headings_conv
    text, blocks_conv = re.subn(r"(?i)</h[1-6]>", "\n\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv

    # Emphasis and inline code.
    text = re.sub(r"(?i)<(?:strong|b)\b[^>]*>", "**", text)
    text = re.sub(r"(?i)</(?:strong|b)\s*>", "**", text)
    text = re.sub(r"(?i)<(?:em|i)\b[^>]*>", "*", text)
    text = re.sub(r"(?i)</(?:em|i)\s*>", "*", text)
    text = re.sub(r"(?i)<code\b[^>]*>", "`", text)
    text = re.sub(r"(?i)</code\s*>", "`", text)

    # Paragraphs and breaks.
    text, blocks_conv = re.subn(r"(?i)<br\s*/?>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?i)<p[^>]*>", "\n\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?i)</p>", "\n\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(
        r"(?i)</?(div|section|article|header|footer|blockquote|figure|figcaption)[^>]*>",
        "\n\n",
        text,
    )
    if counts is not None:
        counts.blocks_conv += blocks_conv

    # Lists.
    text = _number_ordered_lists(text, counts=counts)
    text, lists_conv = re.subn(r"(?i)<li[^>]*>", "\n- ", text)
    if counts is not None:
        counts.lists_conv += lists_conv
    text = re.sub(r"(?i)</li>", "", text)
    text, blocks_conv = re.subn(r"(?i)</?(ul|ol)[^>]*>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text = re.sub(r"\n{2,}- ", "\n- ", text)

    # Tables.
    text, blocks_conv = re.subn(r"(?i)<tr[^>]*>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, blocks_conv = re.subn(r"(?i)</tr>", "\n", text)
    if counts is not None:
        counts.blocks_conv += blocks_conv
    text, tables_conv = re.subn(r"(?i)<t[dh][^>]*>", " | ", text)
    if counts is not None:
        counts.tables_conv += tables_conv
    text = re.sub(r"(?i)</t[dh]>", "", text)
    text = re.sub(r"(?i)</?(table|thead|tbody|tfoot)[^>]*>", "\n", text)
    text = re.sub(r"\n\s*\|\s*", "\n", text)

    # Links and images.
    text, images_conv = IMG_RE.subn(lambda m: _convert_image_md(m, counts), text)
    if counts is not None:
        counts.images_conv += images_conv
    text, anchors_conv = ANCHOR_RE.subn(lambda m: _convert_anchor_md(m, counts), text)
    if counts is not None:
        counts.anchors_conv += anchors_conv

    # Strip all remaining tags.
    text, tags_rm = re.subn(r"(?s)<[^>]+>", " ", text)
    if counts is not None:
        counts.tags_rm += tags_rm
    if notags_sink is not None:
        notags_sink(text)

    # Decode entities and normalize line endings.
    if counts is not None:
        counts.entities_rm += len(re.findall(r"&[A-Za-z0-9#]+;", text))
    text = html.unescape(text).replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Filter control, zero-width, and non-ASCII characters.
    if not raw:
        text = filter_characters(
            text,
            replace_char,
            keep_tabs=keep_tabs,
            keep_newlines=keep_newlines,
            ascii_only=ascii_only,
            counts=filter_counts,
        )

    return _normalize_markdown(text)


def _table_delimiter(name: str) -> str:
    if name == "tab":
        return "\t"
    return ","


def _is_marker_line(text: str) -> bool:
    stripped = text.strip()
    if stripped == "-":
        return True
    if re.fullmatch(r"\d+\.", stripped):
        return True
    if re.fullmatch(r"#{1,6}", stripped):
        return True
    return False


def _merge_dangling_markers(lines: list[str]) -> list[str]:
    merged: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if _is_marker_line(stripped):
            jdx = idx + 1
            while jdx < len(lines) and not lines[jdx].strip():
                jdx += 1
            if jdx < len(lines):
                next_line = lines[jdx].strip()
                if next_line and not _is_marker_line(next_line):
                    merged.append(f"{stripped} {next_line}")
                    idx = jdx + 1
                    continue
                if next_line and _is_marker_line(next_line):
                    idx = jdx
                    continue
            else:
                idx += 1
                continue
        merged.append(line)
        idx += 1
    return merged


def _separate_adjacent_inline(line: str, *, markdown: bool) -> str:
    if markdown:
        line = re.sub(r"\)\s*(?=[!\[])", ") ", line)
        line = re.sub(r"\)\s*(?=[A-Za-z0-9])", ") ", line)
        line = re.sub(r"\)\s*(?=\{)", ") ", line)
    else:
        line = re.sub(r"\)\s*(?=[A-Za-z0-9\[{])", ") ", line)
    return line


def _drop_list_blank_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            prev_line = cleaned[-1] if cleaned else ""
            jdx = idx + 1
            while jdx < len(lines) and not lines[jdx].strip():
                jdx += 1
            if jdx < len(lines):
                next_line = lines[jdx]
                if _is_list_item_line(prev_line) and _is_list_item_line(next_line):
                    idx = jdx
                    continue
        cleaned.append(line)
        idx += 1
    return cleaned


def _is_list_item_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith("- "):
        return True
    return re.match(r"^\d+\.\s+", stripped) is not None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract page content from a mysql tab dump and write per-page .txt files."
    )
    parser.set_defaults(output_dir=".")
    add_common_args(
        parser,
        prefix_default=False,
        case_default=True,
        prefix_help="Enable prefix matching (default: off).",
        case_help="Use case-sensitive matching (default: on).",
    )
    parser.add_argument(
        "--footer",
        action="store_true",
        help="Keep footer-like sections (Resources/Community) instead of stripping them.",
    )
    parser.add_argument(
        "--table-delim",
        choices=("comma", "tab"),
        default="comma",
        help="Delimiter for table fallback rows (default: comma).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown"),
        default="text",
        help="Output format: text or markdown (default: text).",
    )
    add_dump_args(parser, include_notags=True)
    add_filter_args(parser)
    args = parser.parse_args()

    if not validate_limits(args.lines, args.max_bytes):
        return 1
    if args.permit:
        args.strict_header = False
        args.strict_columns = False

    filter_args = resolve_filter_args(args, keep_tabs_default=True)
    if filter_args is None:
        return 1
    replace_char, ascii_only, keep_tabs, keep_newlines, raw = filter_args
    output_encoding = "utf-8" if raw or not ascii_only else "ascii"
    output_errors = "ignore" if output_encoding == "ascii" else "strict"
    table_delim = _table_delimiter(args.table_delim)
    output_format = args.format
    output_ext = ".md" if output_format == "markdown" else ".txt"

    use_prefix = args.use_prefix if args.use_prefix is not None else False
    case_sensitive = args.case_sensitive if args.case_sensitive is not None else True

    pages_path = Path(args.pages)
    focus_entries = load_focus_entries(pages_path, case_sensitive)
    if focus_entries is None:
        return 1
    strict_header = args.strict_header
    strict_columns = args.strict_columns
    input_path = Path(args.input)
    dump_rows_dir = Path(args.dump_rows) if args.dump_rows else None
    result = parse_dump_check(
        input_path,
        max_lines=args.lines,
        max_bytes=args.max_bytes,
        use_csv=args.csvin,
        include_content=True,
        strict_header=strict_header,
        strict_columns=strict_columns,
        dump_rows_dir=dump_rows_dir,
    )
    if result is None:
        return 1
    emit_db_warnings(
        result,
        input_path,
        strict_header=strict_header,
        strict_columns=strict_columns,
    )
    if not focus_entries:
        error("pages list must include at least one page name.")
        return 1

    output_dir = Path(args.output_dir)
    try:
        prepare_output_dir(output_dir)
    except OSError as exc:
        error(str(exc))
        return 1

    rows = result.rows
    for match in match_entries(
        focus_entries, rows, case_sensitive=case_sensitive, use_prefix=use_prefix
    ):
        if match.row is None:
            warn(f"Missing page: {match.entry.name}")
            continue
        for message in _structure_warnings(match.row.content):
            warn(f"{message} in page '{match.entry.name}'")
        notags_path = (
            output_dir / safe_filename(match.entry.name, "_notags.txt")
            if args.notags
            else None
        )
        if output_format == "markdown":
            counts = SanitizeCounts()
            filter_counts = FilterCounts()
            try:
                cleaned = clean_md(
                    match.row.content,
                    replace_char=replace_char,
                    keep_tabs=keep_tabs,
                    keep_newlines=keep_newlines,
                    ascii_only=ascii_only,
                    raw=raw,
                    counts=counts,
                    filter_counts=filter_counts,
                    notags_sink=(
                        None
                        if notags_path is None
                        else make_dump_notags_sink(
                            notags_path,
                            encoding=output_encoding,
                            errors=output_errors,
                        )
                    ),
                )
            except OSError as exc:
                error(str(exc))
                return 1
        else:
            counts = SanitizeCounts()
            filter_counts = FilterCounts()
            try:
                cleaned = clean_content(
                    match.row.content,
                    table_delim=table_delim,
                    replace_char=replace_char,
                    keep_tabs=keep_tabs,
                    keep_newlines=keep_newlines,
                    ascii_only=ascii_only,
                    raw=raw,
                    counts=counts,
                    filter_counts=filter_counts,
                    notags_sink=(
                        None
                        if notags_path is None
                        else make_dump_notags_sink(
                            notags_path,
                            encoding=output_encoding,
                            errors=output_errors,
                        )
                    ),
                )
            except OSError as exc:
                error(str(exc))
                return 1
        if counts.other_scheme_links:
            warn(
                f"Non-HTTP scheme links: {counts.other_scheme_links} in page '{match.entry.name}'"
            )
        if counts.other_scheme_images:
            warn(
                f"Non-HTTP scheme images: {counts.other_scheme_images} in page '{match.entry.name}'"
            )
        if counts.missing_scheme_links:
            warn(
                f"Missing scheme links: {counts.missing_scheme_links} in page '{match.entry.name}'"
            )
        if counts.missing_scheme_images:
            warn(
                f"Missing scheme images: {counts.missing_scheme_images} in page '{match.entry.name}'"
            )
        if not args.footer:
            cleaned = strip_footer(cleaned)
        out_path = output_dir / safe_filename(match.entry.name, output_ext)
        try:
            write_text_check(
                out_path,
                cleaned,
                encoding=output_encoding,
                errors=output_errors,
                label="output",
            )
        except OSError as exc:
            error(str(exc))
            return 1
        print(f"Wrote {out_path} ({match.row.id}, {match.label})")
        info_page_count("Blocks removed", counts.blocks_rm, match.entry.name)
        info_page_count("Comments removed", counts.comments_rm, match.entry.name)
        info_page_count("Tags removed", counts.tags_rm, match.entry.name)
        info_page_count("Entities removed", counts.entities_rm, match.entry.name)
        info_page_count("Anchors converted", counts.anchors_conv, match.entry.name)
        info_page_count("Images converted", counts.images_conv, match.entry.name)
        info_page_count("Headings converted", counts.headings_conv, match.entry.name)
        info_page_count("List items converted", counts.lists_conv, match.entry.name)
        info_page_count("Table cells converted", counts.tables_conv, match.entry.name)
        info_page_count("Blocks converted", counts.blocks_conv, match.entry.name)
        info_page_count(
            "Blocked scheme links", counts.blocked_scheme_links, match.entry.name
        )
        info_page_count(
            "Blocked scheme images", counts.blocked_scheme_images, match.entry.name
        )
        info_page_count(
            "Missing scheme links", counts.missing_scheme_links, match.entry.name
        )
        info_page_count(
            "Missing scheme images", counts.missing_scheme_images, match.entry.name
        )
        info_page_count(
            "Control chars removed", filter_counts.re_control, match.entry.name
        )
        info_page_count("Zero-width removed", filter_counts.re_zero, match.entry.name)
        info_page_count("Tabs removed", filter_counts.re_tab, match.entry.name)
        info_page_count("Newlines removed", filter_counts.re_nl, match.entry.name)
        info_page_count(
            "Non-ASCII removed", filter_counts.re_non_ascii, match.entry.name
        )
        info_page_count(
            "Replacement chars", filter_counts.rep_chars, match.entry.name
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
