#!/usr/bin/env python3
"""Verify cRO item names against public Divine Pride item pages.

The command previews changes by default. In full mode, exact name matches are
recorded in the verified layer while different or non-Chinese candidates are
routed to a review file without changing runtime names. Description syncing is
opt-in because pages may contain historical variants.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "lang" / "items" / "zh_CN_overrides.json"
DEFAULT_BATCH_OUTPUT = (
    ROOT / "lang" / "items" / "zh_CN_divine_pride.json"
)
DEFAULT_REVIEW_OUTPUT = (
    ROOT / "lang" / "items" / "zh_CN_divine_pride_review.json"
)
DEFAULT_BASE_LOCALE = ROOT / "lang" / "items" / "zh_CN.json"
DEFAULT_SOURCE_PATHS = (
    ROOT / "data" / "iteminfo_new.lua",
    ROOT / "data" / "User_iteminfo_new.lua",
)
DEFAULT_STATE_FILE = ROOT / "build" / "divine_pride_item_sync_state.json"
DEFAULT_FAILURE_REPORT = (
    ROOT / "build" / "divine_pride_item_sync_failures.json"
)
BASE_URL = "https://www.divine-pride.net/database/item"
NUMERIC_SLOT_SUFFIX_RE = re.compile(r"\s+\[(\d+)]$")
SOURCE_ITEM_ID_RE = re.compile(r"^\s*\[(\d+)]\s*=", re.MULTILINE)
INVALID_ITEM_NAME_RE = re.compile(
    r"^(?:\(null\)|null|item name|\[ph\]\s*item name)$",
    re.IGNORECASE,
)
HAN_RE = re.compile(r"[\u3400-\u9fff]")
HIRAGANA_KATAKANA_RE = re.compile(r"[\u3040-\u30ff]")
HANGUL_RE = re.compile(r"[\u1100-\u11ff\uac00-\ud7af]")

try:
    from opencc import OpenCC

    _T2S_CONVERTER = OpenCC("t2s")
except ImportError:  # pragma: no cover - optional developer dependency
    _T2S_CONVERTER = None


@dataclass(frozen=True)
class DivinePrideItem:
    item_id: int
    name: str
    description: list[str]
    url: str
    server: str


class DivinePrideItemParser(HTMLParser):
    """Extract the current item title and primary description from one page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.og_title = ""
        self.og_url = ""
        self._table_depth = 0
        self._target_table_depth: int | None = None
        self._capture_description = False
        self._description_complete = False
        self._description_chunks: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {
            str(key).lower(): str(value or "")
            for key, value in attrs
        }

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()
        attributes = self._attrs(attrs)

        if tag == "meta":
            property_name = attributes.get("property", "").lower()
            if property_name == "og:title":
                self.og_title = attributes.get("content", "").strip()
            elif property_name == "og:url":
                self.og_url = attributes.get("content", "").strip()

        if tag == "table":
            self._table_depth += 1
            classes = set(attributes.get("class", "").split())
            if (
                self._target_table_depth is None
                and "mon_table" in classes
                and not self._description_complete
            ):
                self._target_table_depth = self._table_depth

        if self._target_table_depth is None or self._description_complete:
            return

        if tag == "p" and not self._capture_description:
            self._capture_description = True
            return

        if not self._capture_description:
            return
        if tag == "br":
            self._description_chunks.append("\n")
        elif tag == "font":
            color = attributes.get("color", "").lstrip("#")
            if re.fullmatch(r"[0-9A-Fa-f]{6}", color):
                self._description_chunks.append(f"^{color}")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture_description and tag == "font":
            self._description_chunks.append("^000000")
        elif self._capture_description and tag == "p":
            self._capture_description = False
            self._description_complete = True

        if tag == "table":
            if self._target_table_depth == self._table_depth:
                self._target_table_depth = None
            self._table_depth = max(0, self._table_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._capture_description:
            self._description_chunks.append(data)

    def item_name(self) -> str:
        prefix = "Item:"
        name = self.og_title.strip()
        if name.casefold().startswith(prefix.casefold()):
            name = name[len(prefix):].strip()
        return NUMERIC_SLOT_SUFFIX_RE.sub("", name).strip()

    def description_lines(self) -> list[str]:
        raw = "".join(self._description_chunks).replace("\r", "")
        return [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in raw.splitlines()
            if line.strip()
        ]


def parse_item_page(
    html: str,
    *,
    item_id: int,
    server: str = "cRO",
) -> DivinePrideItem:
    parser = DivinePrideItemParser()
    parser.feed(html)
    name = parser.item_name()
    expected_suffix = f"/database/item/{item_id}/{server}".casefold()
    if not name:
        raise ValueError(f"Divine Pride 页面没有物品名称：{item_id}")
    if (
        name.casefold().startswith("unknown item")
        or INVALID_ITEM_NAME_RE.fullmatch(name)
    ):
        raise ValueError(f"Divine Pride 尚无 cRO 物品名称：{item_id}")
    if parser.og_url and not parser.og_url.casefold().endswith(expected_suffix):
        raise ValueError(
            f"Divine Pride 页面 ID/服务器不匹配：{parser.og_url}"
        )
    return DivinePrideItem(
        item_id=item_id,
        name=name,
        description=parser.description_lines(),
        url=f"{BASE_URL}/{item_id}/{server}",
        server=server,
    )


def fetch_item(
    item_id: int,
    *,
    server: str = "cRO",
    timeout: float = 30.0,
) -> DivinePrideItem:
    url = f"{BASE_URL}/{item_id}/{server}"
    request = Request(
        url,
        headers={
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": (
                "ROItemSearchApp_CRO localization verifier "
                "(https://github.com/sOm2y/ROItemSearchApp_CRO)"
            ),
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")
    return parse_item_page(
        html,
        item_id=item_id,
        server=server,
    )


def load_items_file(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {"_meta": {}, "items": {}}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 根节点必须是 JSON 对象")
    items = payload.setdefault("items", {})
    if not isinstance(items, dict):
        raise ValueError(f"{path} 的 items 必须是 JSON 对象")
    return payload


def update_override_payload(
    payload: dict[str, object],
    fetched_items: Iterable[DivinePrideItem],
    *,
    include_description: bool = False,
    checked_at: str | None = None,
) -> None:
    items = payload.setdefault("items", {})
    if not isinstance(items, dict):
        raise ValueError("覆盖文件的 items 必须是 JSON 对象")
    checked_at = checked_at or datetime.now().astimezone().date().isoformat()

    for item in fetched_items:
        item_key = str(item.item_id)
        previous = items.get(item_key, {})
        entry = dict(previous) if isinstance(previous, dict) else {}
        entry["name"] = item.name
        fields = ["name"]
        if include_description:
            if not item.description:
                raise ValueError(f"Divine Pride 页面没有物品说明：{item.item_id}")
            entry["description"] = item.description
            fields.append("description")
        entry["source"] = {
            "provider": "Divine Pride",
            "url": item.url,
            "server": item.server,
            "checked_at": checked_at,
            "fields": fields,
        }
        items[item_key] = entry


def classify_candidate_name(
    local_name: object,
    candidate_name: object,
) -> list[str]:
    local = str(local_name or "").strip()
    candidate = str(candidate_name or "").strip()
    reasons: list[str] = []
    if not local:
        reasons.append("missing_local_name")
    elif candidate != local:
        reasons.append("different_from_local")
    if HIRAGANA_KATAKANA_RE.search(candidate):
        reasons.append("contains_japanese_kana")
    if HANGUL_RE.search(candidate):
        reasons.append("contains_hangul")
    if HAN_RE.search(local) and not HAN_RE.search(candidate):
        reasons.append("replaced_chinese_with_non_chinese")
    if "\ufffd" in candidate:
        reasons.append("contains_replacement_character")
    if (
        _T2S_CONVERTER is not None
        and _T2S_CONVERTER.convert(candidate) != candidate
    ):
        reasons.append("contains_traditional_characters")
    return reasons


def update_review_payload(
    payload: dict[str, object],
    item: DivinePrideItem,
    *,
    local_name: str,
    reasons: Iterable[str],
    checked_at: str | None = None,
) -> None:
    items = payload.setdefault("items", {})
    if not isinstance(items, dict):
        raise ValueError("审核文件的 items 必须是 JSON 对象")
    checked_at = checked_at or datetime.now().astimezone().date().isoformat()
    items[str(item.item_id)] = {
        "local_name": local_name,
        "candidate_name": item.name,
        "reasons": list(dict.fromkeys(str(reason) for reason in reasons)),
        "source": {
            "provider": "Divine Pride",
            "url": item.url,
            "server": item.server,
            "checked_at": checked_at,
            "fields": ["name"],
        },
    }


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def read_item_ids(raw_ids: list[int], ids_file: Path | None) -> list[int]:
    item_ids = list(raw_ids)
    if ids_file is not None:
        content = ids_file.read_text(encoding="utf-8")
        item_ids.extend(int(value) for value in re.findall(r"\d+", content))
    return [item_id for item_id in dict.fromkeys(item_ids) if item_id > 0]


def read_all_item_ids(base_payload: dict[str, object]) -> list[int]:
    items = base_payload.get("items", {})
    if not isinstance(items, dict):
        return []
    result: list[int] = []
    for raw_item_id in items:
        try:
            item_id = int(raw_item_id)
        except (TypeError, ValueError):
            continue
        if item_id > 0:
            result.append(item_id)
    return sorted(set(result))


def read_source_item_ids(
    source_paths: Iterable[Path] = DEFAULT_SOURCE_PATHS,
) -> list[int]:
    item_ids: set[int] = set()
    for source_path in source_paths:
        content = source_path.read_text(encoding="utf-8")
        item_ids.update(
            item_id
            for raw_item_id in SOURCE_ITEM_ID_RE.findall(content)
            if (item_id := int(raw_item_id)) > 0
        )
    return sorted(item_ids)


def get_verified_item_ids(
    payloads: Iterable[dict[str, object]],
    *,
    server: str,
) -> set[int]:
    verified: set[int] = set()
    for payload in payloads:
        items = payload.get("items", {})
        if not isinstance(items, dict):
            continue
        for raw_item_id, raw_entry in items.items():
            if not isinstance(raw_entry, dict):
                continue
            source = raw_entry.get("source", {})
            if not isinstance(source, dict):
                continue
            fields = source.get("fields", [])
            if (
                source.get("provider") != "Divine Pride"
                or str(source.get("server", "")).casefold()
                != server.casefold()
                or not isinstance(fields, list)
                or "name" not in fields
            ):
                continue
            try:
                verified.add(int(raw_item_id))
            except (TypeError, ValueError):
                continue
    return verified


def load_sync_state(
    path: Path,
    *,
    server: str,
    output: Path,
) -> dict[str, object]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        state = {}
    if not isinstance(state, dict):
        raise ValueError(f"{path} 根节点必须是 JSON 对象")

    meta = state.get("_meta", {})
    if meta and isinstance(meta, dict):
        prior_server = str(meta.get("server", ""))
        prior_output = str(meta.get("output", ""))
        if prior_server and prior_server.casefold() != server.casefold():
            raise ValueError(
                f"断点文件服务器为 {prior_server}，当前为 {server}"
            )
        if (
            prior_output
            and Path(prior_output).resolve() != output.resolve()
        ):
            raise ValueError(
                f"断点文件输出为 {prior_output}，当前为 {output}"
            )

    completed = state.get("completed", [])
    failed = state.get("failed", {})
    return {
        "_meta": {
            "provider": "Divine Pride",
            "server": server,
            "output": str(output.resolve()),
        },
        "completed": (
            [int(item_id) for item_id in completed]
            if isinstance(completed, list)
            else []
        ),
        "failed": failed if isinstance(failed, dict) else {},
    }


def new_sync_state(*, server: str, output: Path) -> dict[str, object]:
    return {
        "_meta": {
            "provider": "Divine Pride",
            "server": server,
            "output": str(output.resolve()),
        },
        "completed": [],
        "failed": {},
    }


def fetch_item_with_retry(
    item_id: int,
    *,
    server: str,
    timeout: float,
    retries: int,
    retry_backoff: float,
    fetcher: Callable[..., DivinePrideItem] = fetch_item,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[DivinePrideItem, int]:
    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        try:
            return (
                fetcher(item_id, server=server, timeout=timeout),
                attempt,
            )
        except HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or attempt >= attempts:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt >= attempts:
                raise
        sleeper(retry_backoff * attempt)
    raise RuntimeError(f"无法抓取 Item ID {item_id}")


def _sync_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_sync(
    item_ids: list[int],
    *,
    base_payload: dict[str, object],
    output: Path,
    review_output: Path = DEFAULT_REVIEW_OUTPUT,
    state_file: Path,
    failure_report: Path,
    server: str,
    include_description: bool,
    write: bool,
    plan_only: bool,
    skip_verified: bool,
    resume: bool,
    limit: int | None,
    delay: float,
    timeout: float,
    retries: int,
    retry_backoff: float,
    checkpoint_every: int,
    html_file: Path | None = None,
    fetcher: Callable[..., DivinePrideItem] = fetch_item,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    override_payload = load_items_file(output)
    review_payload = load_items_file(review_output)
    manual_payload = (
        load_items_file(DEFAULT_OUTPUT)
        if output.resolve() != DEFAULT_OUTPUT.resolve()
        else {"items": {}}
    )
    verified_ids = (
        get_verified_item_ids(
            [override_payload, review_payload, manual_payload],
            server=server,
        )
        if skip_verified
        else set()
    )
    state = (
        load_sync_state(
            state_file,
            server=server,
            output=output,
        )
        if resume
        else new_sync_state(server=server, output=output)
    )
    completed_ids = {
        int(item_id)
        for item_id in state.get("completed", [])
    } if resume else set()

    pending_ids = [
        item_id
        for item_id in item_ids
        if item_id not in verified_ids and item_id not in completed_ids
    ]
    pending_before_limit = len(pending_ids)
    if limit is not None:
        pending_ids = pending_ids[:limit]

    print(
        "同步计划："
        f"输入 {len(item_ids)}，"
        f"已校对跳过 {len(set(item_ids) & verified_ids)}，"
        f"断点跳过 {len(set(item_ids) & completed_ids - verified_ids)}，"
        f"待处理 {pending_before_limit}，"
        f"本批 {len(pending_ids)}。"
    )
    if plan_only:
        return 0
    if not pending_ids:
        print("没有需要处理的 Item ID。")
        return 0

    base_items = base_payload.get("items", {})
    output_items = override_payload.get("items", {})
    review_items = review_payload.get("items", {})
    failed = state.get("failed", {})
    if not isinstance(failed, dict):
        failed = {}
        state["failed"] = failed
    state_completed = set(completed_ids)
    successful = 0
    dirty_output = False
    dirty_review = False
    processed_since_checkpoint = 0

    def checkpoint() -> None:
        nonlocal dirty_output, dirty_review, processed_since_checkpoint
        state["completed"] = sorted(state_completed)
        meta = state.setdefault("_meta", {})
        if isinstance(meta, dict):
            meta["updated_at"] = _sync_timestamp()
        if write and dirty_output:
            output_meta = override_payload.setdefault("_meta", {})
            if isinstance(output_meta, dict):
                output_meta.update(
                    {
                        "language": "zh_CN",
                        "provider": "Divine Pride",
                        "server": server,
                        "updated_at": _sync_timestamp(),
                        "verified_item_count": (
                            len(output_items)
                            if isinstance(output_items, dict)
                            else 0
                        ),
                    }
                )
            atomic_write_json(output, override_payload)
            dirty_output = False
        if write and dirty_review:
            review_meta = review_payload.setdefault("_meta", {})
            if isinstance(review_meta, dict):
                review_meta.update(
                    {
                        "language": "zh_CN",
                        "provider": "Divine Pride",
                        "server": server,
                        "updated_at": _sync_timestamp(),
                        "review_item_count": (
                            len(review_items)
                            if isinstance(review_items, dict)
                            else 0
                        ),
                        "purpose": (
                            "Candidates rejected from automatic runtime "
                            "overrides pending manual review."
                        ),
                    }
                )
            atomic_write_json(review_output, review_payload)
            dirty_review = False
        if write:
            atomic_write_json(state_file, state)
        processed_since_checkpoint = 0

    try:
        for index, item_id in enumerate(pending_ids, start=1):
            try:
                if html_file is not None:
                    item = parse_item_page(
                        html_file.read_text(encoding="utf-8"),
                        item_id=item_id,
                        server=server,
                    )
                    attempts = 1
                else:
                    item, attempts = fetch_item_with_retry(
                        item_id,
                        server=server,
                        timeout=timeout,
                        retries=retries,
                        retry_backoff=retry_backoff,
                        fetcher=fetcher,
                        sleeper=sleeper,
                    )
            except (OSError, ValueError, HTTPError, URLError) as error:
                failed[str(item_id)] = {
                    "error": str(error),
                    "failed_at": _sync_timestamp(),
                }
                print(
                    f"[{index}/{len(pending_ids)}] "
                    f"{item_id}: FAILED: {error}",
                    file=sys.stderr,
                )
            else:
                existing_entry = (
                    output_items.get(str(item_id))
                    if isinstance(output_items, dict)
                    else None
                )
                base_entry = (
                    base_items.get(str(item_id))
                    if isinstance(base_items, dict)
                    else None
                )
                current_name = ""
                if isinstance(existing_entry, dict):
                    current_name = str(existing_entry.get("name", ""))
                if not current_name and isinstance(base_entry, dict):
                    current_name = str(base_entry.get("name", ""))
                review_reasons = classify_candidate_name(
                    current_name,
                    item.name,
                )
                disposition = "REVIEW" if review_reasons else "OK"
                print(
                    f"[{index}/{len(pending_ids)}] {item_id}: "
                    f"{current_name or '<本地缺失>'} -> {item.name} "
                    f"[{disposition}] (attempt {attempts})"
                )
                if include_description and not write:
                    for line in item.description:
                        print(f"  {line}")
                if write:
                    if review_reasons:
                        update_review_payload(
                            review_payload,
                            item,
                            local_name=current_name,
                            reasons=review_reasons,
                        )
                        if (
                            isinstance(output_items, dict)
                            and output.resolve()
                            != DEFAULT_OUTPUT.resolve()
                        ):
                            dirty_output = (
                                output_items.pop(str(item_id), None) is not None
                                or dirty_output
                            )
                        dirty_review = True
                    else:
                        update_override_payload(
                            override_payload,
                            [item],
                            include_description=include_description,
                        )
                        if isinstance(review_items, dict):
                            dirty_review = (
                                review_items.pop(str(item_id), None) is not None
                                or dirty_review
                            )
                        dirty_output = True
                    state_completed.add(item_id)
                    failed.pop(str(item_id), None)
                successful += 1

            processed_since_checkpoint += 1
            if write and processed_since_checkpoint >= checkpoint_every:
                checkpoint()
            if index < len(pending_ids) and html_file is None:
                sleeper(delay)
    finally:
        if write:
            checkpoint()

    report_payload = {
        "_meta": {
            "provider": "Divine Pride",
            "server": server,
            "generated_at": _sync_timestamp(),
            "requested": len(pending_ids),
            "successful": successful,
            "failed": len(failed),
        },
        "failures": failed,
    }
    atomic_write_json(failure_report, report_payload)
    print(
        f"本批完成：成功 {successful}，失败 {len(failed)}；"
        f"失败报告：{failure_report}"
    )
    return 2 if failed else 0


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("item_ids", nargs="*", type=int)
    argument_parser.add_argument("--ids-file", type=Path)
    argument_parser.add_argument(
        "--all",
        action="store_true",
        help="使用简体基础物品语言包中的全部 Item ID。",
    )
    argument_parser.add_argument("--server", default="cRO")
    argument_parser.add_argument("--output", type=Path)
    argument_parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
    )
    argument_parser.add_argument(
        "--include-description",
        action="store_true",
        help="同时采用页面当前显示的 cRO 说明；默认只核对名称。",
    )
    argument_parser.add_argument(
        "--write",
        action="store_true",
        help="写入覆盖文件；省略时仅预览。",
    )
    argument_parser.add_argument(
        "--plan",
        action="store_true",
        help="只显示全量规模、跳过数量和本批数量，不发起请求。",
    )
    verified_group = argument_parser.add_mutually_exclusive_group()
    verified_group.add_argument(
        "--skip-verified",
        action="store_true",
        help="跳过已有 Divine Pride 名称来源记录的 Item ID。",
    )
    verified_group.add_argument(
        "--refresh-verified",
        action="store_true",
        help="全量模式也重新抓取已经校对的 Item ID。",
    )
    argument_parser.add_argument(
        "--resume",
        action="store_true",
        help="读取断点文件并跳过已经成功写入的 Item ID。",
    )
    argument_parser.add_argument("--limit", type=int)
    argument_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="批量请求之间的间隔秒数，默认 1 秒。",
    )
    argument_parser.add_argument("--timeout", type=float, default=30.0)
    argument_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="可重试网络错误的重试次数，默认 3 次。",
    )
    argument_parser.add_argument(
        "--retry-backoff",
        type=float,
        default=2.0,
        help="重试退避基数秒数，默认 2 秒。",
    )
    argument_parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help="每成功/失败处理多少项保存一次断点，默认 25。",
    )
    argument_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
    )
    argument_parser.add_argument(
        "--failure-report",
        type=Path,
        default=DEFAULT_FAILURE_REPORT,
    )
    argument_parser.add_argument(
        "--html-file",
        type=Path,
        help="使用本地保存的页面测试单个 Item ID，不发起网络请求。",
    )
    args = argument_parser.parse_args()

    base_payload = load_items_file(DEFAULT_BASE_LOCALE)
    item_ids = read_item_ids(args.item_ids, args.ids_file)
    if args.all:
        item_ids = list(
            dict.fromkeys(
                [
                    *item_ids,
                    *read_all_item_ids(base_payload),
                    *read_source_item_ids(),
                ]
            )
        )
    if not item_ids:
        argument_parser.error("至少提供一个 Item ID、--ids-file 或 --all")
    if args.html_file is not None and len(item_ids) != 1:
        argument_parser.error("--html-file 只能搭配一个 Item ID")
    if args.all and not args.plan and not args.write:
        argument_parser.error("--all 必须搭配 --plan 或 --write")
    if args.resume and not args.write:
        argument_parser.error("--resume 必须搭配 --write")
    if args.delay < 0 or args.retry_backoff < 0:
        argument_parser.error("--delay 和 --retry-backoff 不能小于 0")
    if args.retries < 0:
        argument_parser.error("--retries 不能小于 0")
    if args.limit is not None and args.limit <= 0:
        argument_parser.error("--limit 必须大于 0")
    if args.checkpoint_every <= 0:
        argument_parser.error("--checkpoint-every 必须大于 0")

    output = args.output or (
        DEFAULT_BATCH_OUTPUT if args.all else DEFAULT_OUTPUT
    )
    skip_verified = (
        args.skip_verified
        or (args.all and not args.refresh_verified)
    )
    return run_sync(
        item_ids,
        base_payload=base_payload,
        output=output,
        review_output=args.review_output,
        state_file=args.state_file,
        failure_report=args.failure_report,
        server=args.server,
        include_description=args.include_description,
        write=args.write,
        plan_only=args.plan,
        skip_verified=skip_verified,
        resume=args.resume,
        limit=args.limit,
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        retry_backoff=args.retry_backoff,
        checkpoint_every=args.checkpoint_every,
        html_file=args.html_file,
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("已中断；写入模式下可使用 --resume 继续。", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, HTTPError, URLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
