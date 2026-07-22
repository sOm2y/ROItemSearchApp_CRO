import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError

from scripts.sync_divine_pride_items import (
    DivinePrideItem,
    classify_candidate_name,
    fetch_item_with_retry,
    get_verified_item_ids,
    parse_item_page,
    read_all_item_ids,
    read_source_item_ids,
    run_sync,
    update_override_payload,
)
from scripts.approve_simplified_divine_pride_names import (
    build_korean_bigram_set,
    is_approved_variant_alias,
    is_equivalent_chinese_variant,
    is_simplified_chinese_name,
    is_suspected_korean_mojibake,
)


SAMPLE_HTML = """
<html>
<head>
  <meta property="og:title" content="Item: 影子行家战靴 [1]">
  <meta property="og:url"
        content="https://www.divine-pride.net/database/item/24208/cRO">
</head>
<body>
  <table class="mon_table">
    <tr><td><p>第一行。<br>
      系列: <font color="#777777">影子装备</font>
    </p></td></tr>
  </table>
  <table class="mon_table"><tr><td><p>不应采用的历史说明</p></td></tr></table>
</body>
</html>
"""


class DivinePrideSyncTests(unittest.TestCase):
    def test_simplified_chinese_approval_classification(self):
        self.assertTrue(is_simplified_chinese_name("影子行家战靴 II"))
        self.assertFalse(is_simplified_chinese_name("影子行家戰靴"))
        self.assertFalse(is_simplified_chinese_name("Shadow Boots"))
        self.assertFalse(is_simplified_chinese_name("그림자 부츠"))
        self.assertTrue(
            is_equivalent_chinese_variant("暗神官卡片", "闇神官卡片")
        )
        self.assertFalse(
            is_equivalent_chinese_variant("山茶花发簪", "山茶花の髪飾り")
        )
        self.assertTrue(
            is_approved_variant_alias(
                4671,
                "暗●妖术师 西里亚卡片",
                "闇·元素使 西里亚卡片",
            )
        )

    def test_korean_mojibake_is_not_approved_as_chinese(self):
        review_items = {
            "1": {"candidate_name": "의상 악마의 속삭임"},
        }
        bigrams = build_korean_bigram_set(review_items)
        self.assertTrue(
            is_suspected_korean_mojibake(
                "狼惑 厩付狼 加昏烙",
                "(服饰)恶魔的耳语",
                bigrams,
            )
        )
        self.assertFalse(
            is_suspected_korean_mojibake("榴莲", "榴梿", bigrams)
        )

    def test_parse_current_item_name_and_description(self):
        item = parse_item_page(SAMPLE_HTML, item_id=24208, server="cRO")
        self.assertEqual(item.name, "影子行家战靴")
        self.assertEqual(
            item.description,
            ["第一行。", "系列: ^777777影子装备^000000"],
        )

    def test_reject_mismatched_item_page(self):
        with self.assertRaises(ValueError):
            parse_item_page(SAMPLE_HTML, item_id=24209, server="cRO")

    def test_reject_placeholder_item_names(self):
        for placeholder in ("(null)", "null", "Item Name", "[PH] Item Name"):
            html = SAMPLE_HTML.replace(
                "影子行家战靴 [1]",
                placeholder,
            )
            with self.subTest(placeholder=placeholder):
                with self.assertRaises(ValueError):
                    parse_item_page(html, item_id=24208, server="cRO")

    def test_update_name_only_preserves_existing_description(self):
        payload = {
            "items": {
                "24208": {
                    "description": ["人工说明"],
                }
            }
        }
        item = DivinePrideItem(
            item_id=24208,
            name="影子行家战靴",
            description=["网页说明"],
            url="https://www.divine-pride.net/database/item/24208/cRO",
            server="cRO",
        )
        update_override_payload(
            payload,
            [item],
            include_description=False,
            checked_at="2026-07-20",
        )

        entry = payload["items"]["24208"]
        self.assertEqual(entry["name"], "影子行家战靴")
        self.assertEqual(entry["description"], ["人工说明"])
        self.assertEqual(entry["source"]["fields"], ["name"])

    def test_full_id_list_excludes_zero_and_invalid_keys(self):
        payload = {
            "items": {
                "0": {"name": "无"},
                "100": {"name": "物品"},
                "bad": {"name": "错误"},
            }
        }
        self.assertEqual(read_all_item_ids(payload), [100])

    def test_source_id_list_reads_complete_lua_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir, "items.lua")
            source_path.write_text(
                '[0] = {},\n[100] = {},\n  [200] = {},\n',
                encoding="utf-8",
            )
            self.assertEqual(read_source_item_ids([source_path]), [100, 200])

    def test_verified_ids_require_matching_provider_server_and_name(self):
        payload = {
            "items": {
                "100": {
                    "source": {
                        "provider": "Divine Pride",
                        "server": "cRO",
                        "fields": ["name"],
                    }
                },
                "200": {
                    "source": {
                        "provider": "Other",
                        "server": "cRO",
                        "fields": ["name"],
                    }
                },
                "300": {
                    "source": {
                        "provider": "Divine Pride",
                        "server": "kRO",
                        "fields": ["name"],
                    }
                },
            }
        }
        self.assertEqual(
            get_verified_item_ids([payload], server="cRO"),
            {100},
        )

    def test_retry_uses_backoff_and_returns_attempt_count(self):
        calls = []
        sleeps = []

        def flaky_fetcher(item_id, *, server, timeout):
            calls.append(item_id)
            if len(calls) < 3:
                raise URLError("temporary")
            return DivinePrideItem(
                item_id=item_id,
                name="测试物品",
                description=[],
                url=f"https://example.test/{item_id}",
                server=server,
            )

        item, attempts = fetch_item_with_retry(
            100,
            server="cRO",
            timeout=1,
            retries=3,
            retry_backoff=2,
            fetcher=flaky_fetcher,
            sleeper=sleeps.append,
        )
        self.assertEqual(item.name, "测试物品")
        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [2, 4])

    def test_changed_and_foreign_names_require_review(self):
        self.assertEqual(classify_candidate_name("苹果", "苹果"), [])
        self.assertIn(
            "missing_local_name",
            classify_candidate_name("", "苹果"),
        )
        self.assertIn(
            "different_from_local",
            classify_candidate_name("苹果", "青苹果"),
        )
        english_reasons = classify_candidate_name("宠物蛋", "Pet Egg")
        self.assertIn("different_from_local", english_reasons)
        self.assertIn("replaced_chinese_with_non_chinese", english_reasons)
        self.assertIn(
            "contains_japanese_kana",
            classify_candidate_name("宠物蛋", "ペットの卵"),
        )
        self.assertIn(
            "contains_hangul",
            classify_candidate_name("宠物蛋", "펫 알"),
        )

    def test_changed_name_is_written_to_review_not_runtime_overlay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "verified.json"
            review_output = root / "review.json"

            def fetcher(item_id, *, server, timeout):
                return DivinePrideItem(
                    item_id=item_id,
                    name="网站候选名称",
                    description=[],
                    url=f"https://example.test/{item_id}",
                    server=server,
                )

            status = run_sync(
                [100],
                base_payload={"items": {"100": {"name": "本地名称"}}},
                output=output,
                review_output=review_output,
                state_file=root / "state.json",
                failure_report=root / "failures.json",
                server="cRO",
                include_description=False,
                write=True,
                plan_only=False,
                skip_verified=False,
                resume=False,
                limit=None,
                delay=0,
                timeout=1,
                retries=0,
                retry_backoff=0,
                checkpoint_every=1,
                fetcher=fetcher,
                sleeper=lambda _seconds: None,
            )

            self.assertEqual(status, 0)
            verified = (
                json.loads(output.read_text(encoding="utf-8"))
                if output.exists()
                else {"items": {}}
            )
            review = json.loads(review_output.read_text(encoding="utf-8"))
            self.assertEqual(verified["items"], {})
            self.assertEqual(
                review["items"]["100"]["local_name"],
                "本地名称",
            )
            self.assertEqual(
                review["items"]["100"]["candidate_name"],
                "网站候选名称",
            )

    def test_batch_checkpoint_and_resume(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "verified.json"
            review_output = root / "review.json"
            state_file = root / "state.json"
            failure_report = root / "failures.json"
            base_payload = {
                "items": {
                    "100": {"name": "旧名称一"},
                    "200": {"name": "旧名称二"},
                }
            }

            def first_fetcher(item_id, *, server, timeout):
                if item_id == 200:
                    raise ValueError("missing page")
                return DivinePrideItem(
                    item_id=item_id,
                    name="旧名称一",
                    description=[],
                    url=f"https://example.test/{item_id}",
                    server=server,
                )

            first_status = run_sync(
                [100, 200],
                base_payload=base_payload,
                output=output,
                review_output=review_output,
                state_file=state_file,
                failure_report=failure_report,
                server="cRO",
                include_description=False,
                write=True,
                plan_only=False,
                skip_verified=False,
                resume=False,
                limit=None,
                delay=0,
                timeout=1,
                retries=0,
                retry_backoff=0,
                checkpoint_every=1,
                fetcher=first_fetcher,
                sleeper=lambda _seconds: None,
            )
            self.assertEqual(first_status, 2)
            self.assertIn(
                "100",
                json.loads(output.read_text(encoding="utf-8"))["items"],
            )
            first_state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(first_state["completed"], [100])
            self.assertIn("200", first_state["failed"])

            calls = []

            def second_fetcher(item_id, *, server, timeout):
                calls.append(item_id)
                return DivinePrideItem(
                    item_id=item_id,
                    name="旧名称二",
                    description=[],
                    url=f"https://example.test/{item_id}",
                    server=server,
                )

            second_status = run_sync(
                [100, 200],
                base_payload=base_payload,
                output=output,
                review_output=review_output,
                state_file=state_file,
                failure_report=failure_report,
                server="cRO",
                include_description=False,
                write=True,
                plan_only=False,
                skip_verified=False,
                resume=True,
                limit=None,
                delay=0,
                timeout=1,
                retries=0,
                retry_backoff=0,
                checkpoint_every=1,
                fetcher=second_fetcher,
                sleeper=lambda _seconds: None,
            )
            self.assertEqual(second_status, 0)
            self.assertEqual(calls, [200])
            second_state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(second_state["completed"], [100, 200])
            self.assertEqual(second_state["failed"], {})


if __name__ == "__main__":
    unittest.main()
