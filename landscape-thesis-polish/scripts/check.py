# -*- coding: utf-8 -*-
"""风景园林学位论文润色 · 机械问题检测器（check.py · 语料实测版）

基于 42 篇风景园林学位论文（chapters.json）的实测统计，标记本批论文真正高频、
可改的本地弱点：长句（仅>150字多分句）、弱动词名词化、多层"的"、模糊量词、
迂回表达、生硬被动、空泛套话。

注意：因此/然而/综上所述（1379次/36篇）、随着…、采用…方法、结果表明 等
属于本学科**必要范式**，本检测器**有意不标记**，润色时应保留。

用法:
  python check.py input.txt [--top 50] [--out report.md]
  python check.py - < input.txt          # 从 stdin 读
依赖：仅标准库。
"""
import sys, re, argparse, collections

SENT = re.compile(r"[^。！？；\n]{4,}(?:[。！？；]|$)")

RULES = {
    "R1长句": (
        re.compile(r"^.{150,}$", re.S),
        "长句常态（本批中位60字、p90=152）：仅当>150字且含多分句/多层'的'、需回读时才拆分，勿普遍拆短",
    ),
    "R3弱动词名词化": (
        re.compile(r"(加以|予以|开展|实现)(了)?[一-鿿]{2,10}"),
        "删弱动词（加以/予以/开展/实现），用裸动词或更具体动词（开展实验→实验；实现了目标→达成目标；加以考虑→考虑）；注：'进行'经用户明确可用、不强制改，故不标记",
    ),
    "R4多层\"的\"": (
        re.compile(r"的[^，。；]{0,16}的[^，。；]{0,16}的|的的"),
        "多层'的'定语链，拆短句、换'其中/该/其'或介词结构",
    ),
    "R5模糊量词": (
        re.compile(r"(一些|较多|一定程度|部分|若干|某些|少量|某种程度)的?"),
        "模糊量词，换具体数字/比例/明确范围；查不到则标明来源（据调查/样本显示）",
    ),
    "R6迂回表达": (
        re.compile(r"通过[^，。；]{0,15}(方式|手段|途径)|起到[^，。；]{0,12}作用"),
        "通过…的方式/手段改直接动词；起到…作用改具体动词（发挥/提供/促进/支撑）",
    ),
    "R7生硬被动": (
        re.compile(r"被[^，。；]{0,12}所|由[^，。；]{0,12}(完成|实施)"),
        "生硬被动（被…所/由…完成），改主动点明施事；方法/结果句被动可保留（注：'进行'经用户明确可用，由…进行不标记）",
    ),
    "R9空泛套话": (
        re.compile(r"具有重要的[^，。；]{0,8}意义|不可或缺|至关重要|举足轻重|日益|越来越"),
        "空泛套话：可作轻强调但不堆叠；'具有重要意义'须指明何种意义（理论/现实/方法）",
    ),
    "R13破折号": (
        re.compile(r"——"),
        "少用破折号：非必要不用'——'引导解释/列举，改逗号、分号或另起分句",
    ),
    "R16空泛修饰": (
        re.compile(r"系统性|综合性|整体性|根本性|实质性|全方位"),
        "空泛修饰：删无对应论证的'系统性/综合性/整体性/根本性/实质性/全方位'等词，或换具体说明",
    ),
    "R18非常见符号": (
        re.compile(r"[≠≈→⇒⇌]"),
        "人文社科论文非公式语境禁用 ≠/≈/→/⇒ 等替代自然语言，改写'不同于/导致/指向'等",
    ),
    "R20二元对立": (
        re.compile(r"这不是[^。；：]{0,30}而是"),
        "忌'这不是…而是…'二元对立强行转折（AI 套路），改平实对比或递进",
    ),
    "R29孪生词": (
        re.compile(r"研究与分析|研究和分析|合作与交流|合作和交流|真实性与艺术性|真实性和艺术性|归纳与总结|归纳和总结|提升与优化|分析与研究|交流与合作的?"),
        "拆'和/或/与'孪生词冗余（研究与分析/合作与交流/真实性与艺术性…），择一或并得更准词",
    ),
}


def scan(text):
    hits = []
    for i, m in enumerate(SENT.finditer(text), 1):
        s = m.group(0).strip()
        if not s:
            continue
        for name, (rgx, sug) in RULES.items():
            if rgx.search(s):
                hits.append((i, name, sug, s))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="输入文件；'-' 表示从 stdin 读取")
    ap.add_argument("--top", type=int, default=0, help="最多输出条数，0=全部")
    ap.add_argument("--out", help="将报告写入文件（同时仍打印）")
    args = ap.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()

    hits = scan(text)
    counter = collections.Counter(h[1] for h in hits)

    lines = []
    lines.append("# 润色问题检测报告（语料实测版 · landscape-thesis-polish）\n")
    lines.append("> 本检测器只标记本批 42 篇论文实测高频、可改的本地弱点；")
    lines.append("> 因此/然而/随着…/采用…方法/结果表明 等必要范式**有意不标记**，润色时保留。\n")
    lines.append(f"共扫描到 **{len(hits)}** 处疑似问题。按规则分布：\n")
    for name, n in counter.most_common():
        lines.append(f"- {name}：{n}")
    lines.append("\n---\n")
    for idx, (si, name, sug, s) in enumerate(hits, 1):
        if args.top and idx > args.top:
            break
        lines.append(f"### [{idx}] 句子#{si} · {name}\n")
        lines.append(f"- 原文：{s}\n")
        lines.append(f"- 建议：{sug}\n")

    report = "\n".join(lines)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[written] {args.out}")
    print(report)


if __name__ == "__main__":
    main()
