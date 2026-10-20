#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annotate.py —— 给 Verilog 文件只加注释（不改任何代码字符）

用法:
    python annotate.py spec.json [--apply]

spec.json 结构:
{
  "files": [
    {
      "path": "video_in.v",              # 相对 hdl_source
      "header": ["行1", "行2", ...],      # 插在文件最顶端（timescale 之前），末尾自动换行
      "inserts": [                        # 在 anchor 行之前插入 lines
        {"anchor": "<原文件某一行的完整内容>", "lines": ["//---- xxx ----", "// yyy"]},
        ...
      ]
    }
  ]
}

保证:
  * 按原编码 (utf-8 / gbk) 读、同编码写；换行原样保留（不翻译 newline）。
  * 每个 anchor 必须恰好匹配一行，否则报错退出（不写文件）。
  * 插入内容只使用注释行，Python 侧断言每行 strip 后以 '//' 开头。
  * 校验: 去掉所有注释列之后的代码序列必须与原文一致（结构一致性检查）。
"""
import json, sys, os

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BAK = r"E:\FPGA\_backup\20261009_comments\video"


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def decode(raw):
    """返回 (text, encoding, bom) —— encoding 为回写时应使用的编码名，bom 表示原文是否带 UTF-8 BOM"""
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8"), "utf-8", True
    try:
        return raw.decode("utf-8"), "utf-8", False
    except UnicodeDecodeError:
        return raw.decode("gbk"), "gbk", False


def split_keepends(text):
    """按 '\\n' 切分但保留行尾，返回行列表（不丢任何字节语义）"""
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        if i < len(lines) - 1:
            out.append(ln + "\n")
        else:
            if ln != "":
                out.append(ln)
    return out


def norm(line):
    """锚点匹配用：去掉 // 尾注释、再去掉首尾空白，只比较代码部分
    （生成 spec 时缩进/尾注释写得不完全一致也能命中）"""
    return line.rstrip("\r\n").split("//")[0].strip()


def code_only(line):
    """剥离 // 注释与首尾空白，用于结构一致性比较（不处理块注释字符串，够用）"""
    return line.rstrip("\r\n").split("//")[0].strip()


def main():
    spec_path = sys.argv[1]
    apply = "--apply" in sys.argv
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    for fspec in spec["files"]:
        rel = fspec["path"]
        path = os.path.join(SRC, rel)
        raw = read_bytes(path)
        text, enc, bom = decode(raw)
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = split_keepends(text)

        # 备份
        if apply:
            os.makedirs(BAK, exist_ok=True)
            bak = os.path.join(BAK, rel.replace("/", "__").replace("\\", "__") + ".bak")
            with open(bak, "wb") as f:
                f.write(raw)
            print("备份 ->", bak)

        # 校验 anchors（按去空白归一化匹配，避免生成 spec 时缩进写错）
        inserts = fspec.get("inserts", [])
        seqs = fspec.get("insert_seqs", [])
        resolved = []          # (idx, lines, after)
        for ins in inserts:
            a = norm(ins["anchor"])
            hits = [i for i, ln in enumerate(lines) if norm(ln) == a]
            if len(hits) != 1:
                print("!! anchor matches %d time(s) (%s): %r" % (len(hits), rel, a))
                sys.exit(3)
            resolved.append((hits[0], ins["lines"], bool(ins.get("after"))))
        # 同一 anchor 需要多点插入时用 insert_seqs：每个列表内的 anchor 必须按行号严格递增出现
        for seq in seqs:
            cur = -1
            for ins in seq:
                a = norm(ins["anchor"])
                hits = [i for i, ln in enumerate(lines) if i > cur and norm(ln) == a]
                if not hits:
                    print("!! insert_seq anchor not found in order (%s): %r" % (rel, a))
                    sys.exit(3)
                cur = hits[0]
                resolved.append((cur, ins["lines"], bool(ins.get("after"))))

        # 同一行最多允许一个 after 插入，避免注释互相插队
        seen_after = set()
        for idx, _addl, aft in resolved:
            if aft:
                if idx in seen_after:
                    print("!! 同一行有多个 after 插入 (%s): %r" % (rel, lines[idx]))
                    sys.exit(5)
                seen_after.add(idx)

        # after 插入统一折算为"插在下一行之前"；再按行号倒序插入，保证行号不失效
        resolved = [(idx + 1 if aft else idx, addl) for idx, addl, aft in resolved]
        resolved.sort(key=lambda x: -x[0])

        for idx, addlines in resolved:
            # 沿用被插入行自身使用的换行符，避免在同一文件内引入新的换行风格
            eol = "\r\n" if lines[idx].endswith("\r\n") else "\n"
            add = []
            for s in addlines:
                assert s == "" or s.strip().startswith("//"), "非注释行: %r" % s
                add.append(s + eol)
            lines[idx:idx] = add

        head_eol = "\r\n" if lines[0].endswith("\r\n") else nl
        head = [h + head_eol for h in fspec["header"]]
        lines[0:0] = head

        new = "".join(lines)
        newraw = (b"\xef\xbb\xbf" if bom else b"") + new.encode(enc)

        # 结构一致性：逐行剥离注释后与原行完全一致
        old_lines = split_keepends(text)
        new_code = [code_only(l) for l in split_keepends(new) if code_only(l) != ""]
        old_code = [code_only(l) for l in old_lines if code_only(l) != ""]
        if new_code != old_code:
            print("!! 结构不一致: %s" % rel)
            for i, (a, b) in enumerate(zip(old_code, new_code)):
                if a != b:
                    print("   第 %d 处: 原=%r 新=%r" % (i, a, b))
                    break
            print("   长度 %d -> %d" % (len(old_code), len(new_code)))
            sys.exit(4)

        if apply:
            with open(path, "wb") as f:
                f.write(newraw)
            print("已写入 %-32s enc=%-8s 代码行 %d 不变  插入注释 %d 行  段落 %d"
                  % (rel, enc, len(new_code), len(new_code) and (len(split_keepends(new)) - len(old_lines)), len(inserts)))
        else:
            print("dry-run %-30s OK  代码行 %d 不变  新增 %d 行"
                  % (rel, len(new_code), len(split_keepends(new)) - len(old_lines)))


if __name__ == "__main__":
    main()
