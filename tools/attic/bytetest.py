import csv
for n in (189, 195, 200, 205, 210):
    pre, suf = f"BYTES{n} ", " END"
    txt = pre + "." * (n - len(pre) - len(suf)) + suf
    assert len(txt) == n, (n, len(txt))
    row = dict(file="game1.msg", record=0, offset="0x00000031", speaker="65",
               node="00", bytes_used=20, bytes_free=216,
               chinese="起床啦！快來吃早飯！", english=txt)
    with open(f"bytetest{n}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row)); w.writeheader(); w.writerow(row)
    print(f"bytetest{n}.csv -> {n} bytes, {-(-n//30)} lines")