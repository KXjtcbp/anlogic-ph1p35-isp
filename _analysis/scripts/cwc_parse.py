# -*- coding: utf-8 -*-
"""ChipWatcher CSV 閲囬泦鏁版嵁鐨勫畬鏁翠綋妫€ + 鍐呭鍒嗘瀽銆?鏍煎紡锛氭瘡琛?Sample,Trigger,<128涓?/1>,tlast,tuser,tvalid,<40涓?/1>,tlast,tuser,tvalid
鍗虫瘡涓俊鍙峰鍑轰负銆屽搴︿釜 0/1 瀛楃銆嶇殑浜岃繘鍒朵覆锛圡SB 鍦ㄥ厛锛夈€?"""
import os, sys, re, hashlib
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FILES = [
    ("鍏ㄩ粦",   r"E:\FPGA\鍏ㄩ粦.csv"),
    ("瀹ゅ唴甯稿厜", r"E:\FPGA\瀹ゅ唴甯稿厜.csv"),
    ("test1",  r"E:\FPGA\raw_exports\test1.csv"),
]

COLS = ["Sample","Trigger","ISP_tdata","ISP_tlast","ISP_tuser","ISP_tvalid",
        "AXIS_tdata","AXIS_tlast","AXIS_tuser","AXIS_tvalid"]
WID  = {"ISP_tdata":128, "AXIS_tdata":40}

def parse(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-8", "replace")
    lines = [l for l in txt.replace("\r\n","\n").replace("\r","\n").split("\n") if l.strip()]
    hdr = lines[0].split(",")
    rows = []
    bad = []
    for i, l in enumerate(lines[1:], 1):
        f = l.split(",")
        if len(f) != len(hdr):
            bad.append((i, len(f)))
            continue
        rows.append(f)
    return raw, hdr, rows, bad

def field_stats(hdr, rows):
    """姣忎釜瀛楁锛氬瓧绗﹂泦銆侀暱搴﹂泦鍚?""
    out = []
    for j, name in enumerate(hdr):
        lens, chars = Counter(), Counter()
        for r in rows:
            lens[len(r[j])] += 1
            for c in r[j]:
                chars[c] += 1
        out.append((name, dict(lens), "".join(sorted(chars))))
    return out

def bits(s, w):
    return [int(c) for c in s] if len(s) == w else None

def dec_raw10(s):
    """40 bit -> 4 x 10bit, MSB 鍏?""
    b = bits(s, 40)
    if b is None: return None
    v = [0]*4
    for k in range(4):
        for i in range(10):
            v[k] = (v[k] << 1) | b[k*10 + i]
    return v

def analyse(tag, path, verbose=True):
    raw, hdr, rows, bad = parse(path)
    print("=" * 90)
    print("### %s   %s" % (tag, path))
    print("    瀛楄妭 = %d   sha256 = %s" % (len(raw), hashlib.sha256(raw).hexdigest()[:24]))
    print("    琛ㄥご = %s" % hdr)
    print("    鏁版嵁琛?= %d   鍒楁暟寮傚父鐨勫潖琛?= %d %s" % (len(rows), len(bad), bad[:5]))
    fs = field_stats(hdr, rows)
    for name, lens, chars in fs:
        exp = WID.get(name)
        flag = ""
        if exp and list(lens.keys()) != [exp]:
            flag = "  <== 瀹藉害寮傚父锛堟湡鏈?%d锛? % exp
        if set(chars) - set("01"):
            flag += "  <== 闈炰簩杩涘埗瀛楃"
        print("      %-12s 闀垮害=%-14s 瀛楃闆?%s%s" % (name, lens, chars, flag))

    # 绱㈠紩瀹氫綅锛堜笁浠芥枃浠惰〃澶翠竴鑷达紝鐩存帴鎸夊垪搴忥級
    assert hdr[0] == "Sample" and hdr[1] == "Trigger" and hdr[5].endswith("tvalid") and hdr[9].endswith("tvalid"), hdr
    ix = {"Sample":0,"Trigger":1,"ISP_tdata":2,"ISP_tlast":3,"ISP_tuser":4,"ISP_tvalid":5,
          "AXIS_tdata":6,"AXIS_tlast":7,"AXIS_tuser":8,"AXIS_tvalid":9}
    isp_tv = [r[ix["ISP_tvalid"]] for r in rows]
    ax_tv  = [r[ix["AXIS_tvalid"]] for r in rows]
    isp_on = [i for i, v in enumerate(isp_tv) if v == "1"]
    ax_on  = [i for i, v in enumerate(ax_tv)  if v == "1"]
    print("    ISP_tvalid=1  鐨勬牱鏈暟 = %-6d 浣嶇疆: %s%s" % (
        len(isp_on), isp_on[:15], " ..." if len(isp_on) > 15 else ""))
    print("    AXIS_tvalid=1 鐨勬牱鏈暟 = %-6d 浣嶇疆: %s%s" % (
        len(ax_on), ax_on[:15], " ..." if len(ax_on) > 15 else ""))
    for nm, on in (("ISP", isp_on), ("AXIS", ax_on)):
        if len(on) > 1:
            d = [on[i+1]-on[i] for i in range(len(on)-1)]
            print("      %s 闂撮殧鐩存柟鍥? %s" % (nm, dict(Counter(d).most_common(8))))
    trig = [i for i, r in enumerate(rows) if r[ix["Trigger"]] != "0"]
    print("    Trigger 鏍囪琛?= %d %s" % (len(trig), trig[:10]))

    # ISP 128bit 闈為浂鏍锋湰
    nz_isp = [i for i, r in enumerate(rows) if set(r[ix["ISP_tdata"]]) != {"0"}]
    nz_ax  = [i for i, r in enumerate(rows) if set(r[ix["AXIS_tdata"]]) != {"0"}]
    print("    ISP_tdata 闈炲叏闆舵牱鏈?= %d" % len(nz_isp))
    print("    AXIS_tdata 闈炲叏闆舵牱鏈?= %d" % len(nz_ax))

    # ---- AXIS RAW10 ----
    print("    ---- S_axis_tdata[39:0] RAW10 瑙ｇ爜 (浠?tvalid=1 鐨勮) ----")
    raw_vals = []
    for i in ax_on:
        v = dec_raw10(rows[i][ix["AXIS_tdata"]])
        raw_vals.append((i, v))
    if not raw_vals:
        print("      (鏃犳湁鏁堟牱鏈?")
    for i, v in raw_vals[:20]:
        print("      sample %-5d -> %s" % (i, v))
    if len(raw_vals) > 20:
        print("      ... 鍏?%d 涓? % len(raw_vals))
    flat = [x for _, v in raw_vals for x in v]
    if flat:
        print("      鍊煎煙 [%d .. %d]  鍧囧€?%.2f  鏍锋湰鎬绘暟 %d" % (min(flat), max(flat), sum(flat)/len(flat), len(flat)))
        print("      鍚勫瓧娈靛潎鍊?= %s" % (
            [round(sum(v[k] for _, v in raw_vals)/len(raw_vals), 2) for k in range(4)]))

    # ---- ISP 杈撳嚭 ----
    print("    ---- S_ISP_O_tdata[127:0] 鍘熷鍒嗗潡锛堝墠 8 涓?tvalid=1 鐨勮锛屾寜 4x32bit 鍒囷級----")
    for i in isp_on[:8]:
        s = rows[i][ix["ISP_tdata"]]
        chunks = [s[k*32:(k+1)*32] for k in range(4)]
        print("      sample %-5d  " % i + " | ".join(chunks))
    return dict(tag=tag, path=path, hdr=hdr, rows=rows, isp_on=isp_on, ax_on=ax_on,
                raw_vals=raw_vals, nz_isp=nz_isp, nz_ax=nz_ax)

res = {}
for tag, p in FILES:
    if os.path.exists(p):
        res[tag] = analyse(tag, p)
    else:
        print("缂哄け: %s" % p)

print()
print("=" * 90)
print("### 涓や唤閲囬泦鐨勫樊寮傦紙鍏ㄩ粦 vs 瀹ゅ唴甯稿厜锛?)
a, b = res.get("鍏ㄩ粦"), res.get("瀹ゅ唴甯稿厜")
if a and b:
    print("    ISP_tvalid=1 鏁? %d vs %d" % (len(a["isp_on"]), len(b["isp_on"])))
    print("    AXIS_tvalid=1 鏁? %d vs %d" % (len(a["ax_on"]), len(b["ax_on"])))
    print("    ISP_tdata 闈為浂琛? %d vs %d" % (len(a["nz_isp"]), len(b["nz_isp"])))
    print("    AXIS_tdata 闈為浂琛? %d vs %d" % (len(a["nz_ax"]), len(b["nz_ax"])))
    # 閫愯姣旇緝 ISP_tdata
    diff = [i for i in range(min(len(a["rows"]), len(b["rows"])))
            if a["rows"][i][2] != b["rows"][i][2]]
    print("    ISP_tdata 鍐呭涓嶅悓鐨勮鏁?= %d / %d" % (len(diff), len(a["rows"])))
    print("    鍓?5 涓笉鍚岃鍙?= %s" % diff[:5])
    # ISP 鍊煎煙
    for nm, r in (("鍏ㄩ粦", a), ("瀹ゅ唴甯稿厜", b)):
        vals = []
        for i in r["isp_on"]:
            s = r["rows"][i][2]
            for k in range(4):
                c = s[k*32:(k+1)*32]
                vals.append(int(c, 2))
        if vals:
            print("    %s ISP 4x32bit 鍒嗗潡鍊煎煙 [%d .. %d] 鍧囧€?%.1f 鏍锋湰 %d" % (
                nm, min(vals), max(vals), sum(vals)/len(vals), len(vals)))
