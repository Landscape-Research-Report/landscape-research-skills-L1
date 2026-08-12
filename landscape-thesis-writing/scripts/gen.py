#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
landscape-thesis-writing —— 风景园林学位论文「常用语 / 语句结构」生成辅助脚本

作用：把上一轮对 42 篇风景园林学位论文蒸馏得到的「分章节写作范式」
（references/templates.json）转成可直接用于起草论文文字的「生成简报」。

输入：章节类型（--chapter）+ 用户给定的事实/要素（--facts，JSON）。
输出：
  1) 该章节高频领域术语（保证用词专业、覆盖学科词汇）
  2) 高频句首词（保证开头多样、贴近范式）
  3) 句式模板库（结构模式 + 抽象槽位 + 真实例句）—— LLM 据此组句
  4) 初稿骨架：用用户事实填充槽位，产出可直接改写的句子草稿

不联网、不编造事实；只做「范式检索 + 槽位填充」的机械辅助，
最终成稿由 LLM 在 SKILL 流程中按 rules.md 润色定稿。
"""

import json
import os
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "..", "references", "templates.json")


def load_templates():
    with open(TEMPLATES, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    return s.replace(" ", "").replace("　", "")


def match_chapter(data, key):
    if key in data:
        return key
    nk = norm(key)
    for k in data:
        if norm(k) == nk:
            return k
    # substring match
    for k in data:
        if nk and nk in norm(k):
            return k
    # reverse: key is substring of a known key
    for k in data:
        if norm(k) in nk:
            return k
    return None


def fill_slot(slot, facts):
    """Replace [X] placeholders in a slot string using facts dict."""
    import re
    out = slot
    for m in re.findall(r"\[([^\[\]]+)\]", slot):
        token = m.strip()
        # try exact, then first matching fact key contained in token
        if token in facts:
            out = out.replace("[" + m + "]", facts[token])
        else:
            repl = None
            for fk, fv in facts.items():
                if fk and (fk in token or token in fk):
                    repl = fv
                    break
            if repl is not None:
                out = out.replace("[" + m + "]", repl)
            # else leave [X] as placeholder for user to fill
    return out


def cmd_list(data):
    print("可用章节类型（--chapter 取值）：")
    for i, k in enumerate(data.keys(), 1):
        v = data[k]
        chars = v.get("chars", 0)
        ntmpl = len(v.get("templates", []))
        print(f"  {i:>2}. {k}  (范式句例≈{chars}字, 句式模板{ntmpl}类)")


def cmd_gen(data, chapter, facts, top_terms=20, top_openers=15, top_tmpl=8, draft=True):
    key = match_chapter(data, chapter)
    if not key:
        print(f"[错误] 未找到章节「{chapter}」。可用章节见 --list。", file=sys.stderr)
        sys.exit(2)
    v = data[key]
    print(f"# 生成简报：{key}\n")

    terms = v.get("terms", [])[:top_terms]
    print(f"## 一、推荐领域术语（优先覆盖，避免口语化）")
    print("、".join(t for t, _ in terms))
    print()

    openers = v.get("openers", [])[:top_openers]
    print(f"## 二、推荐句首词（开头多样化，贴近范式）")
    print("、".join(o for o, _ in openers))
    print()

    templates = v.get("templates", [])[:top_tmpl]
    print(f"## 三、句式模板库（结构 + 槽位 + 真实例句）")
    for label, info in templates:
        slot = info.get("slot", "")
        exs = info.get("examples", [])[:2]
        cnt = info.get("count", 0)
        print(f"- 模式：{label}  ｜ 出现频次≈{cnt}")
        print(f"  抽象槽位：{slot}")
        if exs:
            for e in exs:
                print(f"  真实例句：{e}")
    print()

    if draft and facts:
        print(f"## 四、初稿骨架（已用你给的事实填充槽位，供改写）")
        used = set()
        for label, info in templates:
            slot = info.get("slot", "")
            filled = fill_slot(slot, facts)
            if "[" in filled:
                # not all placeholders filled; still show as scaffold
                pass
            tag = "[占位待补]" if "[" in filled else "[可改写]"
            print(f"- {filled}  {tag}")
        print()
        print("提示：把以上骨架扩展为 2–4 句连贯段落；术语从「一」中取，开头从「二」中取；")
        print("      成稿后按 references/rules.md 的 R1–R12 自检（尤其 R1 短句、R7 强动词）。")


def main():
    ap = argparse.ArgumentParser(description="风景园林学位论文句式生成辅助")
    ap.add_argument("--list", action="store_true", help="列出所有章节类型")
    ap.add_argument("--chapter", "-c", help="章节类型（可用 --list 查看）")
    ap.add_argument("--facts", "-f", help='事实/要素 JSON，如 \'{"对象":"城市公园","特征":"康养功能不足"}\'')
    ap.add_argument("--top-terms", type=int, default=20)
    ap.add_argument("--top-openers", type=int, default=15)
    ap.add_argument("--top-tmpl", type=int, default=8)
    ap.add_argument("--no-draft", action="store_true", help="不生成初稿骨架")
    args = ap.parse_args()

    data = load_templates()
    if args.list or not args.chapter:
        cmd_list(data)
        if not args.chapter:
            print("\n用法示例：")
            print('  python gen.py -c "绪论 / 研究背景" -f \'{"对象":"城市公园","特征":"康养功能不足","手段":"空间优化","目的":"提升健康效益"}\'')
        return

    facts = {}
    if args.facts:
        try:
            facts = json.loads(args.facts)
        except Exception as e:
            print(f"[错误] --facts 不是合法 JSON：{e}", file=sys.stderr)
            sys.exit(2)
    cmd_gen(data, args.chapter, facts,
            top_terms=args.top_terms, top_openers=args.top_openers,
            top_tmpl=args.top_tmpl, draft=not args.no_draft)


if __name__ == "__main__":
    main()
