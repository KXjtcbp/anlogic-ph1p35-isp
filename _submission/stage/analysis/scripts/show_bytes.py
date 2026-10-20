import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
for path in sys.argv[1:]:
    print("=" * 90)
    print("FILE:", path)
    print("=" * 90)
    b = open(path, 'rb').read()
    print("bytes:", len(b))
    # check validity
    try:
        b.decode('utf-8'); print("utf8: OK")
    except UnicodeDecodeError as e:
        print("utf8: FAIL at", e.start, repr(b[max(0,e.start-30):e.start+30]))
    # split into lines keeping line endings visible
    for i, raw in enumerate(b.split(b'\n'), 1):
        try:
            s = raw.decode('utf-8')
            tag = ""
        except UnicodeDecodeError:
            s = raw.decode('gbk', errors='replace')
            tag = "  <GBK>"
        print("%4d| %s%s" % (i, s.rstrip('\r'), tag))
