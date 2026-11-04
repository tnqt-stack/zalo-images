#!/usr/bin/env python
"""Thống kê giữa phiên WeHa: dữ liệu ngày -> HTML -> PNG.
Dùng: python build.py 2026-11-04
Cần trong thư mục ngày: data.json (mẫu: 2026-11-04/data.json). Mã VN30F tháng gần nhất: python build.py --vn30f"""
import asyncio
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
W = 1400
SCALE = 1.3


def vn(x, d=0, sign=False):
    s = f"{abs(x):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    pre = ("+" if x > 0 else "−" if x < 0 else "") if sign else ("−" if x < 0 else "")
    return pre + s


def cls(x):
    return "up" if x > 0 else "down" if x < 0 else "flat"


def load(day):
    data = json.loads((ROOT / day / "data.json").read_text("utf8"))
    uni = json.loads((ROOT / "universe.json").read_text("utf8"))["groups"]
    return data, uni, data["pct"]


def check(data, uni):
    """Dữ liệu sai thì dừng (exit 4), không dựng ảnh để gửi khách."""
    e = []
    syms = [x for g in uni.values() for x in g]
    miss = [x for x in syms if x not in data.get("pct", {})]
    if miss:
        e.append(f"pct thiếu: {miss}")
    if any(abs(v) > 7.1 for v in data.get("pct", {}).values()):
        e.append("pct có mã vượt biên độ HOSE 7%")
    ix = data["index"]
    if not ix["low"] <= ix["value"] <= ix["high"]:
        e.append("index.value nằm ngoài cao/thấp")
    if abs(ix["value"] / ix["ref"] - 1) > .08:
        e.append("index lệch tham chiếu quá 8%")
    if len(data.get("series", [])) < 20:
        e.append("series ít hơn 20 điểm")
    for k in ("curr", "prev", "week1", "week2", "month"):
        a = data["liq"].get(k, [])
        if len(a) != 31 or a[-1] <= 0:
            e.append(f"liq.{k} phải đủ 31 mốc, mốc cuối > 0")
        if any(y < x for x, y in zip(a, a[1:])):
            e.append(f"liq.{k} không tăng dần")
    if data.get("morning_volume", 0) < 1e7:
        e.append("morning_volume quá nhỏ")
    for k in ("up", "down"):
        if len(data["contrib"].get(k, [])) < 4:
            e.append(f"contrib.{k} cần ít nhất 4 mã")
    if e:
        print(json.dumps({"loi": e}, ensure_ascii=False))
        sys.exit(4)


def pct(q, s):
    return q.get(s, 0.0)


def morning(data, day):
    """KL phiên sáng hôm nay so với lịch sử; tự ghi hôm nay vào history.json."""
    f = ROOT / "history.json"
    h = json.loads(f.read_text("utf8"))
    m = h["morning_volume"]
    m[day] = data["morning_volume"]
    h["morning_volume"] = {k: m[k] for k in sorted(m)[-40:]}
    f.write_text(json.dumps(h, ensure_ascii=False, indent=0), "utf8")
    past = [m[k] for k in sorted(m) if k < day]
    n = len(past[-20:])
    return m[day] / 1e6, past[-1] / 1e6, sum(past[-5:]) / 5e6, sum(past[-20:]) / n / 1e6, n


def vn30f_code(today=None):
    """Mã hợp đồng VN30F tháng gần nhất theo quy ước sàn, vd 41I1GB000 = 11/2026."""
    d = today or dt.date.today()
    y, m = d.year, d.month
    first = dt.date(y, m, 1)
    expiry = first + dt.timedelta(days=(3 - first.weekday()) % 7 + 14)
    if d > expiry:
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"41I1{chr(ord('G') + y - 2026)}{'123456789ABC'[m - 1]}000", f"VN30F {m:02d}/{y}"


def price_chart(data):
    pts = [(int(t[:2]) * 60 + int(t[3:5]), v) for t, v in data["series"]]
    ix = data["index"]
    ref = ix["ref"]
    w, h, l, r, t, b = 1320, 250, 16, 120, 14, 38

    def X(m):  # trục gộp nghỉ trưa: 09:15 -> 14:45
        m2 = m if m <= 690 else m - 90
        return l + (m2 - 555) / 240 * (w - l - r)

    lo = min(ix["low"], ref) - 7
    hi = max(ix["high"], ref) + 3

    def Y(v):
        return t + (hi - v) / (hi - lo) * (h - t - b)

    path = " ".join(f"{'M' if i == 0 else 'L'}{X(m):.1f},{Y(v):.1f}" for i, (m, v) in enumerate(pts))
    area = f"{path} L{X(pts[-1][0]):.1f},{Y(ref):.1f} L{X(pts[0][0]):.1f},{Y(ref):.1f} Z"
    yr = Y(ref)
    xe = X(pts[-1][0])
    ye = Y(pts[-1][1])
    lowp = min(pts, key=lambda p: p[1])
    ticks = "".join(
        f'<text x="{X(m):.1f}" y="{h-10}" text-anchor="middle" class="ax">{s}</text>'
        for m, s in [(570, "09:30"), (600, "10:00"), (630, "10:30"), (660, "11:00"), (690, "11:30")])
    xa = X(690) + 16
    return f'''<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="VN-Index theo nến 5 phút">
<defs><clipPath id="ab"><rect x="0" y="0" width="{w}" height="{yr:.1f}"/></clipPath>
<clipPath id="be"><rect x="0" y="{yr:.1f}" width="{w}" height="{h}"/></clipPath></defs>
<rect x="{xa:.1f}" y="{t}" width="{w-r-xa:.1f}" height="{h-t-b}" rx="8" fill="var(--surface-soft)"/>
<text x="{(xa+w-r)/2:.1f}" y="{h-b-24:.1f}" text-anchor="middle" class="note">Phiên chiều 13:00 – 14:45</text>
<path d="{area}" fill="var(--zone-up-fill)" clip-path="url(#ab)"/>
<path d="{area}" fill="var(--zone-down-fill)" clip-path="url(#be)"/>
<line x1="{l}" x2="{w-r}" y1="{yr:.1f}" y2="{yr:.1f}" stroke="var(--gold)" stroke-width="2" stroke-dasharray="8 6"/>
<path d="{path}" fill="none" stroke="var(--ink)" stroke-width="3.5" stroke-linejoin="round"/>
<circle cx="{X(lowp[0]):.1f}" cy="{Y(lowp[1]):.1f}" r="7" fill="var(--down)" stroke="#fff" stroke-width="2"/>
<text x="{X(lowp[0])-8:.1f}" y="{Y(lowp[1])+32:.1f}" class="lab" fill="var(--down)">Đáy {vn(ix['low'],2)}</text>
<circle cx="{xe:.1f}" cy="{ye:.1f}" r="8" fill="var(--ink)" stroke="#fff" stroke-width="2"/>
<text x="{xe+16:.1f}" y="{ye+8:.1f}" class="lab" fill="var(--ink)">{vn(pts[-1][1],2)}</text>
<text x="{w-r-8}" y="{yr+30:.1f}" text-anchor="end" class="lab" fill="var(--gold-strong)">Tham chiếu {vn(ref,2)}</text>
{ticks}</svg>'''


def liq_chart(liq):
    n = len(liq["curr"])
    s = 4
    avg = [(a + b + c) / 3 for a, b, c in zip(liq["week1"], liq["week2"], liq["month"])]
    w, h, l, r, t, b = 560, 330, 74, 18, 14, 42
    top = max(max(liq["curr"]), max(liq["prev"]), max(avg)) * 1.06

    def X(i):
        return l + (i - s) / (n - 1 - s) * (w - l - r)

    def Y(v):
        return t + (1 - v / top) * (h - t - b)

    def line(a, col, wd, dash=""):
        p = " ".join(f"{'M' if i == s else 'L'}{X(i):.1f},{Y(a[i]):.1f}" for i in range(s, n))
        return f'<path d="{p}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-linejoin="round" {dash}/>'

    grid = ""
    for v in range(0, int(top), 2000):
        grid += (f'<line x1="{l}" x2="{w-r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--border)"/>'
                 f'<text x="{l-10}" y="{Y(v)+7:.1f}" text-anchor="end" class="ax">{vn(v)}</text>')
    tk = "".join(
        f'<text x="{X(i):.1f}" y="{h-12}" text-anchor="{a}" class="ax">{lb}</text>'
        for i, lb, a in [(s, "09:20", "start"), (12, "10:00", "middle"), (24, "11:00", "middle"), (n - 1, "11:30", "end")])
    return f'''<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Thanh khoản lũy kế theo giờ">{grid}{tk}
{line(avg,'var(--s4)',3,'stroke-dasharray="9 7"')}{line(liq['prev'],'var(--gold)',3)}{line(liq['curr'],'var(--ink)',4.5)}
<circle cx="{X(n-1):.1f}" cy="{Y(liq['curr'][-1]):.1f}" r="7" fill="var(--ink)" stroke="#fff" stroke-width="2"/></svg>'''


def cmp_rows(rows):
    mx = max(v for _, v, _ in rows)
    out = ""
    for i, (lb, v, ch) in enumerate(rows):
        col = "var(--ink)" if i == 0 else "var(--s4)"
        c = "" if ch is None else f'<span class="chg {cls(ch)}">{vn(ch,1,True)}%</span>'
        out += (f'<div class="cmp"><span class="cl">{lb}</span><span class="cv">{vn(v)}</span><span class="cc">{c}</span>'
                f'<span class="cb"><i style="width:{v/mx*100:.1f}%;background:{col}"></i></span></div>')
    return out


def squarify(items, x, y, w, h):
    """items: [(key, area)] giảm dần, tổng diện tích = w*h. Trả [(key,x,y,w,h)]."""
    out = []
    items = list(items)

    def worst(row, s):
        a = sum(v for _, v in row)
        return max(max(s * s * v / a / a, a * a / (s * s * v)) for _, v in row)

    while items:
        s = min(w, h)
        row = [items[0]]
        i = 1
        while i < len(items) and worst(row + [items[i]], s) <= worst(row, s):
            row.append(items[i])
            i += 1
        items = items[i:]
        a = sum(v for _, v in row)
        if w >= h:
            cw = a / h
            yy = y
            for k, v in row:
                out.append((k, x, yy, cw, v / cw))
                yy += v / cw
            x += cw
            w -= cw
        else:
            ch = a / w
            xx = x
            for k, v in row:
                out.append((k, xx, y, v / ch, ch))
                xx += v / ch
            y += ch
            h -= ch
    return out


def heat_col(p):
    if p >= 2.5:
        return "h3u"
    if p >= 1:
        return "h2u"
    if p >= .1:
        return "h1u"
    if p > -.1:
        return "h0"
    if p > -1:
        return "h1d"
    if p > -2.5:
        return "h2d"
    return "h3d"


def heatmap(uni, q):
    W_, H_, strip = 1288, 560, 32
    tot = sum(sum(g.values()) for g in uni.values())
    gs = sorted(uni.items(), key=lambda kv: -sum(kv[1].values()))
    k = W_ * H_ / tot
    html = ""
    for name, x, y, w, h in squarify([(n, sum(g.values()) * k) for n, g in gs], 0, 0, W_, H_):
        g = uni[name]
        ih = h - strip
        sc = w * ih / sum(g.values())
        html += (f'<div class="hg" style="left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px">'
                 f'<b class="hl">{name}</b>')
        cells = sorted(((s, v * sc) for s, v in g.items()), key=lambda a: -a[1])
        for s, tx, ty, tw, th in squarify(cells, 0, strip, w, ih):
            p = pct(q, s)
            fs = min(64, tw / 3.3, th / 2.5)
            show = fs >= 17
            if fs < 17:
                fs = min(19, tw / 2.15, th / 1.25)
            row = not show and tw >= fs * 5.2
            rowc = " row" if row else ""
            sub = f'<small style="font-size:{max(15,fs*.6):.0f}px">{vn(p,2,True)}%</small>' if show or row else ""
            html += (f'<div class="ht {heat_col(p)}{rowc}" style="left:{tx:.1f}px;top:{ty:.1f}px;width:{tw:.1f}px;height:{th:.1f}px">'
                     f'<span style="font-size:{fs:.0f}px">{s}</span>{sub}</div>')
        html += "</div>"
    return f'<div class="heat" style="width:{W_}px;height:{H_}px">{html}</div>'


def contrib_chart(ct):
    rows = sorted(ct["up"], key=lambda a: -a[1]) + sorted(ct["down"], key=lambda a: -a[1])
    mx = max(abs(v) for _, v in rows)
    o = ""
    for s, v in rows:
        wd = abs(v) / mx * 46
        side = (f"left:50%;width:{wd:.1f}%;background:var(--up-bar)" if v > 0
                else f"right:50%;width:{wd:.1f}%;background:var(--down-bar)")
        o += (f'<div class="ctr"><span class="sy">{s}</span><span class="tr"><i style="{side}"></i></span>'
              f'<span class="chg {cls(v)} nv">{vn(v,2,True)}</span></div>')
    return o


def render(day):
    css = (ROOT / "style.css").read_text("utf8")
    data, uni, q = load(day)
    check(data, uni)
    ix = data["index"]
    liq = data["liq"]
    chg = ix["value"] - ix["ref"]
    chp = chg / ix["ref"] * 100
    d = dt.date.fromisoformat(day)
    dow = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][d.weekday()]
    dstr = d.strftime("%d/%m/%Y")
    cur, prev = liq["curr"][-1], liq["prev"][-1]
    avg3 = (liq["week1"][-1] + liq["week2"][-1] + liq["month"][-1]) / 3
    kl, klp, kl5, kl20, n20 = morning(data, day)
    vals = [pct(q, s) for g in uni.values() for s in g]
    up, dn = sum(v > 0 for v in vals), sum(v < 0 for v in vals)
    fl = len(vals) - up - dn
    ct = data["contrib"]
    ct = {"up": ct["up"][:4], "down": ct["down"][:4]}
    rest = chg - sum(v for _, v in ct["up"] + ct["down"])
    fr = data["foreign"]
    net = fr["net"] / 1e9
    dv = data["deriv"]
    dvc = (dv["price"] / dv["ref"] - 1) * 100
    basis = dv["price"] - dv["vn30"]
    ind = data["industries"]
    drag = ct["down"][0][0]
    lift = ct["up"][0][0]
    if chg >= 0:
        h1 = (f'VN-Index tăng <mark>{vn(abs(chg),2)} điểm</mark> sau phiên sáng; '
              f'{ind[0][0]}, {ind[1][0]} dẫn dắt, {drag} là lực cản lớn nhất')
    else:
        h1 = f'VN-Index giảm <mark>{vn(abs(chg),2)} điểm</mark> sau phiên sáng; {drag} đè chỉ số, {lift} nâng đỡ'
    pos = (ix["value"] - ix["low"]) / (ix["high"] - ix["low"])
    badge, bcls = (("Chốt sát đỉnh phiên", "up") if pos >= .8 else
                   ("Chốt gần đáy phiên", "down") if pos <= .2 else ("Chốt giữa biên độ", "mid"))
    hero_read = (f'Chỉ số xuống thấp nhất {vn(ix["low"],2)} quanh {ix["low_time"]}, sau đó hồi '
                 f'{vn(ix["value"]-ix["low"],1)} điểm và chốt phiên sáng {"trên" if chg >= 0 else "dưới"} tham chiếu.')
    vs_p = (cur / prev - 1) * 100
    vs_a = (cur / avg3 - 1) * 100

    def word(x):
        return "cao hơn" if x > 0 else "thấp hơn"

    liq_title = f'Thanh khoản {word(vs_p)} hôm qua {vn(abs(vs_p),1)}%, {word(vs_a)} TB 3 phiên {vn(abs(vs_a),1)}%'
    if vs_p > 0 and vs_a < 0 and kl > kl20:
        liq_read = (f"Dòng tiền ấm lên so với hôm qua. Khối lượng vượt TB {n20} phiên nhưng giá trị khớp lệnh vẫn dưới "
                    "3 phiên đối chiếu, nên chưa phải tín hiệu bùng nổ; cần phiên chiều xác nhận.")
    elif vs_p > 0 and vs_a < 0:
        liq_read = "Dòng tiền đã cải thiện so với hôm qua nhưng chưa vượt mức thường thấy, cần theo dõi thêm phiên chiều."
    elif vs_p > 0:
        liq_read = "Dòng tiền vào mạnh hơn cả hôm qua lẫn mức thường thấy cùng thời điểm."
    elif vs_a > 0:
        liq_read = "Dòng tiền chậm lại so với hôm qua nhưng vẫn trên mức thường thấy cùng thời điểm."
    else:
        liq_read = "Dòng tiền thấp hơn cả hôm qua lẫn mức thường thấy, thị trường đang thiếu lực giao dịch."
    names = sorted(((s, pct(q, s)) for g in uni.values() for s in g), key=lambda a: -a[1])
    best = " · ".join(f"{s} {vn(p,1,True)}%" for s, p in names[:5] if p > 0)
    worst = " · ".join(f"{s} {vn(p,1,True)}%" for s, p in names[::-1][:5] if p < 0)
    upn = sum(p > 0 for _, p in names)
    dnn = sum(p < 0 for _, p in names)
    fsell = " · ".join(f"{s} {vn(v,1,True)}" for s, v in fr["sell"][:4])
    fbuy = " · ".join(f"{s} {vn(v,1,True)}" for s, v in fr["buy"][:3])
    lead = "Bên tăng áp đảo" if up > dn * 1.3 else "Bên giảm áp đảo" if dn > up * 1.3 else "Cân bằng"
    netlist = ", ".join(s for s, _ in (fr["sell"] if net < 0 else fr["buy"])[:3])
    html = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Thống kê giữa phiên {dstr}</title><style>{css}</style></head><body><main class="canvas">
<header class="top"><img src="../assets/logo.png" alt="WeHa"><div class="meta"><span class="tag">Thống kê giữa phiên</span><b>Chốt phiên sáng · {data["time"]}</b><span>{dow}, {dstr}</span></div></header>
<h1 class="h1">{h1}</h1>
<section class="kpi">
<div class="card-hero"><div class="eyebrow">VN-Index · {data["time"]}</div><div class="display-score">{vn(ix["value"],2)}</div>
<div class="hrow"><span class="chg {cls(chg)} big">{vn(chg,2,True)} ({vn(chp,2,True)}%)</span><span class="badge b-{bcls}">{badge}</span></div>
<div class="how-to-read"><b>Cách đọc:</b> {hero_read}</div></div>
<div class="tiles">
<div class="stat-tile"><div class="stat-label">Biên độ phiên sáng</div><div class="stat-value">{vn(ix["high"]-ix["low"],1)}<span class="unit">điểm</span></div><div class="stat-sub">{vn(ix["low"],2)} – {vn(ix["high"],2)}</div></div>
<div class="stat-tile"><div class="stat-label">Giá trị khớp lệnh</div><div class="stat-value">{vn(cur)}<span class="unit">tỷ đồng</span></div><div class="stat-sub">Thỏa thuận thêm {vn(liq["put_through"])} tỷ đồng</div></div>
<div class="stat-tile"><div class="stat-label">Khối ngoại khớp lệnh</div><div class="stat-value {cls(net)}">{vn(net,0,True)}<span class="unit">tỷ đồng</span></div><div class="stat-sub">{"Bán ròng" if net < 0 else "Mua ròng"} mạnh {netlist}</div></div>
</div></section>
<h2 class="sh"><em>01</em>Diễn biến trong phiên</h2><p class="sub">VN-Index theo nến 5 phút · nét đứt: tham chiếu</p>
<div class="card">{price_chart(data)}</div>
<h2 class="sh"><em>02</em>{liq_title}</h2><p class="sub">Sàn HOSE · so sánh cùng thời điểm {data["time"]}</p>
<div class="card liq"><div class="lc"><div class="lg"><span><i style="background:var(--ink)"></i>Hôm nay</span><span><i style="background:var(--gold)"></i>Hôm qua</span><span><i class="dash"></i>TB 3 phiên*</span></div>
<div class="cap">Giá trị khớp lệnh lũy kế, tỷ đồng</div>{liq_chart(liq)}</div>
<div class="lr"><div class="ct">Giá trị khớp lệnh, tỷ đồng</div>{cmp_rows([("Hôm nay", cur, None), ("Hôm qua", prev, vs_p), ("TB 3 phiên*", avg3, vs_a)])}
<p class="fn">% là hôm nay so với mốc đó.</p></div><div class="lr"><div class="ct">KL phiên sáng, triệu cp**</div>{cmp_rows([("Hôm nay", kl, None), ("Hôm qua", klp, (kl/klp-1)*100), ("TB 5 phiên", kl5, (kl/kl5-1)*100), (f"TB {n20} phiên", kl20, (kl/kl20-1)*100)])}</div>
<div class="how-to-read wide"><b>Cách đọc:</b> {liq_read}<br><span class="fn">* Cùng giờ của 3 phiên cách đây 1 tuần, 2 tuần, 1 tháng. ** Gồm thỏa thuận.</span></div></div>
<h2 class="sh"><em>03</em>{upn} trong 60 mã vốn hóa lớn đang tăng, {dnn} mã giảm</h2><p class="sub">60 mã lớn nhất HOSE · diện tích theo vốn hóa, màu theo % thay đổi</p>
<div class="card">{heatmap(uni, q)}<div class="scale"><span>−4%</span><i class="h3d"></i><i class="h2d"></i><i class="h1d"></i><i class="h0"></i><i class="h1u"></i><i class="h2u"></i><i class="h3u"></i><span>+4%</span></div></div>
<h2 class="sh"><em>04</em>{lift} nâng chỉ số nhiều nhất, {drag} đè mạnh nhất</h2><p class="sub">Độ rộng tính trên 60 mã vốn hóa lớn HOSE · điểm đóng góp theo VCBS</p>
<section class="two"><div class="card"><div class="ct">Độ rộng 60 mã lớn: {lead.lower()}</div>
<div class="stack"><i style="flex:{up};background:var(--up-bar)"></i><i style="flex:{fl};background:var(--gold)"></i><i style="flex:{dn};background:var(--down-bar)"></i></div>
<div class="sl"><span class="chg up">▲ {up} tăng</span><span class="nt">{fl} đứng</span><span class="chg down">{dn} giảm ▼</span></div>
<p class="ln"><b>Tăng mạnh:</b> {best}</p><p class="ln"><b>Chịu áp lực:</b> {worst}</p>
<p class="ln"><b>Khối ngoại:</b> bán {fsell} · mua {fbuy} (tỷ đồng)</p></div>
<div class="card"><div class="ct">Kéo / đè chỉ số, điểm</div>{contrib_chart(ct)}
<p class="ln rest">Các mã còn lại cộng dồn: <b>{vn(rest,2,True)} điểm</b></p>
<p class="ln">{dv["name"]}: <b class="chg {cls(dvc)}">{vn(dv["price"],1)} ({vn(dvc,2,True)}%)</b> · basis {vn(basis,1,True)}</p></div></section>
<footer class="foot"><div><b>WeHa - Wealth and Happiness</b> · weha.com.vn<br>Kỷ luật đầu tư bằng dữ liệu</div>
<div class="r">Nguồn: {data.get("source", "VCBS")} · cập nhật {data["asof"]} {dstr}. Số liệu trong phiên là tạm tính, chỉ để tham khảo, không phải khuyến nghị đầu tư.</div></footer>
</main></body></html>'''
    out = ROOT / day / "index.html"
    out.write_text(html, "utf8")
    print(f"KL sáng {kl:.1f} | hôm qua {klp:.1f} | TB5 {kl5:.1f} | TB{n20} {kl20:.1f} | độ rộng {up}/{fl}/{dn} | còn lại {rest:.2f} | TB3 {avg3:.0f}")
    return out


async def shot(html, png):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        exe = "/opt/pw-browsers/chromium"
        b = await pw.chromium.launch(**({"executable_path": exe, "args": ["--no-sandbox"]} if pathlib.Path(exe).exists() else {}))
        ctx = await b.new_context(viewport={"width": W, "height": 1000}, device_scale_factor=SCALE)
        p = await ctx.new_page()
        await p.goto(html.resolve().as_uri())
        await p.evaluate("document.fonts.ready")
        await p.wait_for_timeout(300)
        bad = await p.evaluate("[...document.fonts].filter(f=>f.status!='loaded').map(f=>f.family)")
        h = await p.evaluate("document.documentElement.scrollHeight")
        over = await p.evaluate("[...document.querySelectorAll('.ct,.ln,.h1,.sh,.stat-sub,.sub')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.slice(0,24))")
        await p.screenshot(path=str(png), full_page=True)
        await b.close()
    print(f"OK {png.name}: {int(W*SCALE)}x{int(h*SCALE)}px, cao/rộng {h/W:.2f}", "| FONT LOI:" if bad else "", bad or "", "| TRAN:" if over else "", over or "")


if __name__ == "__main__":
    if sys.argv[1] == "--vn30f":
        print(*vn30f_code())
        sys.exit()
    if sys.argv[1] == "--symbols":
        u = json.loads((ROOT / "universe.json").read_text("utf8"))["groups"]
        a = [x for g in u.values() for x in g]
        for i in range(0, len(a), 20):
            print(",".join(a[i:i + 20]))
        sys.exit()
    day = sys.argv[1]
    d = dt.date.fromisoformat(day)
    asyncio.run(shot(render(day), ROOT / day / f"ThongKeGiuaPhien_{d:%d-%m-%Y}.png"))
