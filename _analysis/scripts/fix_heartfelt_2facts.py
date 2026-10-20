# -*- coding: utf-8 -*-
"""就地修正报告 §4.2 里两条与事实不符/不确切的表述（不重新插入，只改已有段落）。

1) 「怀疑是伽马参数不对，换了几组试」→ 点名真实换过的参数组
   （依据：`_analysis/lut/` 下存在 gamma_lut_p118_k125 / p128_k145 /
     p118_k125_toe16 / log_k10 / twoseg_p160_a050 等多组，见文件 mtime 10-10）
2) 「只写下今天能交出去的那一件」→ 删除（用户确认未发生，进度按当天可用时间推进）
"""
import os
import sys

from docx import Document

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORT = r"E:\FPGA\比赛报告_填空版_20261019.docx"

OLD1 = "后来又怀疑是伽马参数不对，换了几组试。"
NEW1 = ("后来又怀疑是曲线参数不对，把拐点和强度换过几组，"
        "P=118/k=1.25、P=128/k=1.45、P=160 两段都试了。")

OLD2 = ("后来我换了个很笨的办法，焦虑上来的时候不去算还差多少，只写下今天能交出去的那一件。"
        "进度没因此变快，但我从“担心整件事”变成“先做完手上这一件”，就不慌了。")
NEW2 = ("后来说不上有什么办法，就是当天能推多少推多少，一天一天往下做。"
        "回过头看，那段焦虑没持续太久。项目一旦开始有能跑起来的东西，担心就自己少了。")


def replace_in_para(p, old, new):
    """把段落正文里的 old 换成 new，保留第一个 run 的格式。

    做法：整段重写成一个 run（该段本来就是纯正文，无局部加粗/变色）。
    """
    if old not in p.text:
        return False
    r0 = p.runs[0]
    for r in p.runs[1:]:
        r._element.getparent().remove(r._element)
    r0.text = p.text.replace(old, new)
    return True


def main():
    d = Document(REPORT)
    hit1 = hit2 = 0
    for p in d.paragraphs:
        if replace_in_para(p, OLD1, NEW1):
            hit1 += 1
            print("修 1 →", p.text[:60], "…")
        if replace_in_para(p, OLD2, NEW2):
            hit2 += 1
            print("修 2 →", p.text[-60:], "…")
    if hit1 != 1 or hit2 != 1:
        raise SystemExit("命中数不对：修1=%d 修2=%d（应各为 1）" % (hit1, hit2))
    d.save(REPORT)
    print("已保存 %s  %d B" % (REPORT, os.path.getsize(REPORT)))


if __name__ == "__main__":
    main()
