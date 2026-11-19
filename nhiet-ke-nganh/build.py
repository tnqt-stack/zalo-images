#!/usr/bin/env python
"""Nhiệt kế thị trường + Ngành dẫn dắt (ảnh ngang WeHa bản sáng) gửi Zalo 8h15 mỗi sáng.
Đọc số gốc trong nguon/ -> kiểm -> HTML -> PNG -> lời bình.

Dùng:
  python build.py                 dựng phiên mới nhất vào nhiet-ke-nganh/<phien>/
  python build.py --thu           dựng thử vào nhiet-ke-nganh/thu/ (đè), bỏ qua kiểm "đã dựng" và "số quá cũ"
  python build.py --force         dựng lại dù thư mục phiên đã có PNG
  python build.py --nguon <dir>   đọc số từ thư mục khác (mặc định nguon/)

Mã thoát: 0 xong (4 dòng cuối PHIEN=, DMY=, PNG=, LOIBINH=) · 3 phiên này đã dựng/gửi ·
4 số hai nguồn chưa cùng phiên hoặc số quá cũ · 5 lỗi dữ liệu/ảnh (thiếu file, JSON hỏng, mã ngoài top 100, font, tràn chữ)."""
import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
W = 2400
SCALE = 1.75
TOP_N = 100            # mọi mã nêu tên trên ảnh phải thuộc top N theo giá trị giao dịch bình quân 20 phiên
MAX_CU_NGAY = 4        # phiên Nhiệt kế cũ hơn hôm nay quá số ngày này thì không gửi
MAX_LECH_TIN_HIEU = 7  # tin-hieu-weha cũ hơn phiên Nhiệt kế quá số ngày này thì bỏ ô giai đoạn
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
GD_TEN = {"thuan_loi": "Thuận lợi", "trung_tinh": "Trung tính", "bat_loi": "Bất lợi"}
GD_CLS = {"thuan_loi": "gd-up", "trung_tinh": "gd-mid", "bat_loi": "warn"}
GD_VCLS = {"thuan_loi": "up", "trung_tinh": "mid", "bat_loi": "down"}

# tín hiệu -> lớp màu (t-* thẻ ngành, b-* huy hiệu, v-* chữ số)
SIG = {"Tham gia": "up", "Mạnh": "up", "Nắm giữ": "mid", "Trung bình": "mid",
       "Quan sát": "obs", "Rời bỏ": "down", "Yếu": "down"}


def die(code, msg):
    print(f"DUNG ({code}): {msg}", file=sys.stderr)
    sys.exit(code)


def load(p):
    if not p.exists():
        die(5, f"thiếu file nguồn {p}")
    try:
        return json.loads(p.read_text("utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        die(5, f"JSON hỏng {p.name}: {e}")


def hom_nay_vn():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    except Exception:
        return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=7)).date()


def n(x, d=0, sign=False):
    s = f"{abs(x):,.{d}f}"  # WeHa: 12,345.6; số âm dấu "-" thường
    pre = ("+" if x > 0 else "-" if x < 0 else "") if sign else ("-" if x < 0 else "")
    return pre + s


def ud(x):
    return "up" if x > 0 else "down" if x < 0 else "flat"


def zcls(zone):
    return "down" if zone <= 2 else "mid" if zone == 3 else "up"


def join_vi(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " và " + items[-1]


def scale(nguong, diem, zone):
    """Thang 5 vùng rộng bằng nhau; mốc đặt theo tỷ lệ bên trong đoạn đang ở."""
    bounds = [g["tu"] for g in nguong] + [100]
    segs, labs = [], []
    for i, g in enumerate(nguong):
        on = i + 1 == zone
        mk = ""
        if on:
            f = (diem - bounds[i]) / (bounds[i + 1] - bounds[i])
            mk = f'<b class="zs-mk" style="left:{f * 100:.1f}%"></b>'
        segs.append(f'<i class="z-{zcls(i + 1)}{" on" if on else ""}">{mk}</i>')
        labs.append(f'<div class="{"on" if on else ""}">{g["ten"]}<span>{bounds[i]}–{bounds[i + 1]}</span></div>')
    return f'<div class="zs"><div class="zs-bar">{"".join(segs)}</div><div class="zs-lab">{"".join(labs)}</div></div>'


def head(no, title, right=""):
    act = f'<div class="actions">{right}</div>' if right else ""
    return f'<div class="section-head"><h2 class="sh"><em>{no}</em>{title}</h2>{act}</div>'


# ---------------------------------------------------------------- đọc số
def doc_so(nguon):
    nk = load(nguon / "nhiet-ke.json")
    try:
        m = dict(
            phien=nk["date"], diem=nk["score"], vung=nk["regime"], zone=nk["zone"],
            nguong=[dict(ten=z["name"], tu=z["lo"]) for z in sorted(nk["zones"], key=lambda z: z["lo"])],
            tuan=nk["history"]["week"]["score"], thang=nk["history"]["month"]["score"], quy=nk["history"]["quarter"]["score"],
            tt=nk["alloc"], eq0=nk["backtest"]["series"]["equity"][-2],
            v3=nk["stats"]["regime_3m"], cp_lai_3m=nk["stats"]["stocks_up_3m"])
        dt.date.fromisoformat(m["phien"])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        die(5, f"nhiet-ke.json thiếu/sai trường: {e!r}")
    nganh = [r for r in load(nguon / "ndd_nganh.json") if r.get("he") == "22 nhóm"]
    vutru = load(nguon / "ndd_vu_tru.json")
    ls = load(nguon / "ndd_lich_su_ma.json")
    if len(nganh) != 22:
        die(5, f"ndd_nganh.json có {len(nganh)} ngành hệ 22 nhóm (cần 22)")
    if not ls.get("ngay") or not ls.get("ma") or not ls.get("tin_hieu_ma") or not ls.get("tin_hieu_nganh"):
        die(5, "ndd_lich_su_ma.json thiếu ngay/ma/tin_hieu_ma/tin_hieu_nganh")
    # tin-hieu-weha: không bắt buộc; thiếu hoặc cũ thì bỏ ô giai đoạn
    th = None
    p_th = nguon / "tin-hieu-weha.json"
    if p_th.exists():
        t = load(p_th).get("trang_thai") or {}
        try:
            lech = (dt.date.fromisoformat(m["phien"]) - dt.date.fromisoformat(t["ngay_so_lieu"])).days
            if lech > MAX_LECH_TIN_HIEU:
                print(f"Bỏ ô giai đoạn: tin-hieu-weha ngày {t['ngay_so_lieu']} cũ hơn phiên {m['phien']} {lech} ngày")
            elif t["giai_doan"]["giai_doan"] not in GD_TEN:
                print(f"Bỏ ô giai đoạn: mã giai đoạn lạ {t['giai_doan']['giai_doan']!r}")
            else:
                th = t
        except (KeyError, TypeError, ValueError) as e:
            print(f"Bỏ ô giai đoạn: tin-hieu-weha thiếu trường {e!r}")
    else:
        print("Bỏ ô giai đoạn: không có tin-hieu-weha.json")
    gt = load(ROOT / "gtgd_tb20.json").get("gtgd_tb20_ty") or die(5, "gtgd_tb20.json thiếu gtgd_tb20_ty")
    return m, nganh, vutru, ls, th, gt


# ---------------------------------------------------------------- dựng HTML + lời bình
def dung(m, nganh, vutru, ls, th, GT):
    THN, THM, LSMA = ls["tin_hieu_nganh"], ls["tin_hieu_ma"], ls["ma"]
    VUMA = {x["ma"] for x in vutru}
    top = sorted((k for k in GT if k in VUMA and GT[k] is not None), key=lambda k: -GT[k])[:TOP_N]
    print(f"TOP{TOP_N}: mã cuối {top[-1]} {GT[top[-1]]}")
    TOP = set(top)

    d = dt.date.fromisoformat(m["phien"])
    dstr = d.strftime("%d/%m/%Y")

    # ---- h1 + hàng Nhiệt kế
    tt, eq0 = m["tt"], m["eq0"]
    eq = tt["equity"]
    verb = "giữ" if eq == eq0 else "tăng lên" if eq > eq0 else "giảm còn"
    h1 = f'Nhiệt kế <mark>{n(m["diem"], 1)} điểm</mark>, vùng {m["vung"]}; tỷ trọng cổ phiếu gợi ý {verb} {eq}%'
    hero = (f'<div class="card-hero"><div class="eyebrow">Điểm thị trường</div>'
            f'<div class="hrow"><div class="display-score">{n(m["diem"], 1)}<small>/100</small></div>'
            f'<span class="badge b-{zcls(m["zone"])}">{m["vung"]}</span>'
            f'<div class="hist">Tuần trước <span class="hv">{n(m["tuan"], 1)}</span><br>1 tháng trước '
            f'<span class="hv">{n(m["thang"], 1)}</span><br>3 tháng trước <span class="hv">{n(m["quy"], 1)}</span></div></div>'
            f'{scale(m["nguong"], m["diem"], m["zone"])}</div>')
    chg_txt = ("Không đổi so với tuần trước" if eq == eq0
               else f'{"Tăng" if eq > eq0 else "Giảm"} {abs(eq - eq0)} điểm % so với tuần trước')
    t1 = (f'<div class="stat-tile"><div class="stat-label">Tỷ trọng cổ phiếu gợi ý</div>'
          f'<div class="stat-value">{eq}%</div>'
          f'<div class="stat-sub">{chg_txt}. <span class="nb">Trái phiếu, tiền gửi {tt["bonds"]}%</span> '
          f'<span class="nb">· Vàng {tt["gold"]}%</span> <span class="nb">· Tiền mặt {tt["cash"]}%</span></div></div>')
    v3 = m["v3"]
    t2 = (f'<div class="stat-tile"><div class="stat-label">Lịch sử khi thị trường ở vùng <strong class="nhan">{m["vung"]}</strong></div>'
          f'<div class="pair"><div><div class="stat-value {ud(v3["vni_3m"])}">{n(v3["vni_3m"], 1, True)}%</div>'
          f'<div class="pair-l">VN-Index 3 tháng sau, trung bình</div></div>'
          f'<div><div class="stat-value">{m["cp_lai_3m"]}%</div><div class="pair-l">cổ phiếu HOSE có lãi sau 3 tháng</div></div></div>'
          f'<div class="stat-sub">Tính trên các tuần cùng vùng từ {v3["since"]}; <span class="nb">VN-Index</span> chỉ tăng ở {v3["hit_3m"]}% số lần.</div></div>')

    # ---- ô giai đoạn cho chiến lược (3 trạng thái; không có số thì bỏ ô)
    t3, gd_dong = "", None
    if th:
        gd = th["giai_doan"]["giai_doan"]
        ten_gd = GD_TEN[gd]
        cl = th.get("chien_luoc") or []
        if gd == "bat_loi":
            kv = [c.get("canh_bao", {}).get("bat_loi", {}).get("ky_vong") for c in cl]
            c2 = (f' Cả {len(cl)} chiến lược đều có <span class="am">lãi kỳ vọng âm</span> trong kiểm định lịch sử.'
                  if cl and all(k is not None and k < 0 for k in kv) else "")
            cau1 = "Chưa có chiến lược nào của WeHa phù hợp giai đoạn này."
            gd_dong = f"Thị trường đang ở giai đoạn {ten_gd}, chưa có chiến lược nào của WeHa phù hợp giai đoạn này."
        else:
            hop = [c["ten"] for c in cl if c.get("giai_doan_hop") == gd]
            c2 = ""
            if hop:
                cau1 = f'Giai đoạn hợp với {join_vi([f"<span class=nb>{x}</span>" for x in hop])}.'
                gd_dong = f"Thị trường đang ở giai đoạn {ten_gd}, hợp với {join_vi(hop)}."
            else:
                cau1 = "Chưa có chiến lược nào của WeHa phù hợp giai đoạn này."
                gd_dong = f"Thị trường đang ở giai đoạn {ten_gd}, chưa có chiến lược nào của WeHa phù hợp giai đoạn này."
        t3 = (f'<div class="stat-tile {GD_CLS[gd]}"><div class="stat-label">Giai đoạn cho chiến lược</div>'
              f'<div class="stat-value {GD_VCLS[gd]}">{ten_gd}</div>'
              f'<div class="stat-sub"><span class="w1">{cau1}</span>{c2}</div></div>')
    kpi = f'<section class="kpi {"k3" if t3 else "k2"}">{hero}{t1}{t2}{t3}</section>'

    # ---- 01 top 5 ngành
    rows = sorted(nganh, key=lambda r: r["hang"])  # sort ổn định: đồng hạng giữ thứ tự file
    top5, rest = rows[:5], rows[5:]
    moi_vao = [r["nganh"] for r in top5 if r["hang_truoc"] > 5]
    t01 = (f'Top 5 ngành: {top5[0]["nganh"]} dẫn đầu; '
           + (f'{join_vi(moi_vao)} mới vào top 5' if moi_vao else 'top 5 không đổi so với phiên trước'))

    def bien_dong(r):
        if r["hang"] == r["hang_truoc"]:
            return "Giữ hạng"
        return f'{"▲" if r["hang"] < r["hang_truoc"] else "▼"} từ hạng {int(r["hang_truoc"])}'

    def tieu_bieu(ten):
        """Mã Mạnh của ngành thuộc TOP, giao dịch bình quân 20 phiên lớn nhất (bằng nhau thì điểm cao hơn), tối đa 3."""
        its = sorted((x for x in vutru if x["nganh_de_xuat"] == ten and x["th_ma"] == "Mạnh" and x["ma"] in TOP),
                     key=lambda x: (-(GT.get(x["ma"]) or 0), -x["diem"]))[:3]
        body = ("".join(f'<span><span class="tm">{x["ma"]}</span><span class="td v-up">{n(x["diem"], 1)}</span></span>' for x in its)
                if its else f'<span class="tb3-none">Chưa có mã Mạnh trong top {TOP_N}</span>')
        return f'<div class="tb3"><div class="tb3-l">Mã mạnh tiêu biểu</div><div class="tb3-r{" few" if len(its) < 3 else ""}">{body}</div></div>'
    ng_cards = "".join(
        f'<div class="ngc t-{SIG[r["de_xuat"]]}"><div class="ngc-1"><span class="ngc-h">Hạng {r["hang"]}</span>'
        f'<span class="badge bw-{SIG[r["de_xuat"]]}">{r["de_xuat"]}</span></div>'
        f'<div class="ngc-n">{r["nganh"]}</div>'
        f'<div class="ngc-3"><span class="ngc-v">{n(r["diem"], 1)}</span><span class="ngc-d">{bien_dong(r)}</span></div>'
        f'{tieu_bieu(r["nganh"])}</div>'
        for r in top5)
    s1 = head("01", t01) + f'<div class="g5">{ng_cards}</div>'

    # ---- 02 tín hiệu mã thay đổi trong phiên
    VT = {x["ma"]: x for x in vutru if x["ma"] in TOP}  # danh sách tên mã chỉ trong TOP

    def sig_at(ma, k):
        s_ = LSMA.get(ma)
        return THM[s_[k][2]] if s_ and len(s_) >= -k and s_[k][2] is not None else None
    nay = {k: sig_at(k, -1) for k in VT}
    truoc = {k: sig_at(k, -2) for k in VT}
    # ô số đếm trên toàn bộ mã theo dõi (không giới hạn top 100)
    tong = len(vutru)
    so_manh = sum(sig_at(x["ma"], -1) == "Mạnh" for x in vutru)
    so_manh_truoc = sum(sig_at(x["ma"], -2) == "Mạnh" for x in vutru)

    def xep(ms):
        return sorted((VT[k] for k in ms), key=lambda x: (-(GT.get(x["ma"]) or 0), -x["diem"]))
    len_manh = xep(k for k in VT if nay[k] == "Mạnh" and truoc[k] != "Mạnh")
    mat_manh = xep(k for k in VT if truoc[k] == "Mạnh" and nay[k] != "Mạnh")

    def ds(label, cls, its):
        if not its:
            body = '<div class="ds-none">Không có mã nào</div>'
        else:
            shown = its if len(its) <= 8 else its[:7]
            nl = len(shown) + (1 if len(its) > 8 else 0)
            last0 = max(0, nl - 2)  # ô không còn ô nào bên dưới thì không kẻ dưới
            cells = [f'<div class="dr{" last" if i >= last0 else ""}"><span class="dr-m">{x["ma"]}</span><span class="dr-d">{n(x["diem"], 1)}</span>'
                     f'<span class="dr-n">{x["nganh_de_xuat"]}</span></div>' for i, x in enumerate(shown)]
            if len(its) > 8:
                cells.append(f'<div class="dr dr-more last">+{len(its) - 7} mã khác</div>')
            body = f'<div class="ds-g">{"".join(cells)}</div>'
        return f'<div class="card dsc"><div class="ds-h"><span class="badge {cls}">{label} · {len(its)}</span></div>{body}</div>'
    tile_m = (f'<div class="stat-tile st-m"><div class="stat-label">Mã có tín hiệu Mạnh</div>'
              f'<div class="stat-value">{so_manh}<span class="unit">/{tong} mã</span></div>'
              f'<div class="stat-sub">Phiên trước {so_manh_truoc} mã</div></div>')
    s2 = (head("02", f"Tín hiệu mã trong top {TOP_N}: {len(len_manh)} mã mới lên Mạnh, {len(mat_manh)} mã mất Mạnh",
               f"<span>Top {TOP_N} mã giao dịch nhiều nhất · so với phiên trước</span>")
          + f'<div class="g02">{tile_m}{ds("Mới lên Mạnh", "b-up", len_manh)}{ds("Mất tín hiệu Mạnh", "b-down", mat_manh)}</div>')

    # ---- dải các ngành còn lại
    grp = []
    for sig in THN:
        its = [r for r in rest if r["de_xuat"] == sig]
        if its:
            grp.append(f'<div class="rg"><span class="badge b-{SIG[sig]}">{sig} · {len(its)}</span><div class="rg-l">'
                       + "".join(f'<span class="ri">{r["nganh"]} <span class="rv v-{SIG[sig]}">{n(r["diem"], 1)}</span></span>' for r in its)
                       + '</div></div>')
    s3 = f'<div class="tag tag-rest">{len(rest)} ngành còn lại</div><div class="card restc">{"".join(grp)}</div>'

    css = (ROOT / "style.css").read_text("utf8")
    thu = THU[d.weekday()]
    foot_r = (f'<span>Nguồn: Nhiệt kế thị trường, Ngành dẫn dắt và Tín hiệu WeHa, số sau phiên {dstr}.</span>'
              '<span>Mô hình định lượng, không phải khuyến nghị đầu tư. Backtest là mô phỏng quá khứ.</span>')
    html = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Nhiệt kế và Ngành dẫn dắt {dstr}</title><style>{css}</style></head><body><main class="canvas">
<header class="top"><div class="brand"><b>WeHa - Wealth and Happiness</b><span>Sau phiên · {thu}, {dstr}</span></div><img src="../assets/logo.png" alt="WeHa"></header>
<div class="tag tag-top">Nhiệt kế thị trường · Ngành dẫn dắt</div>
<h1 class="h1">{h1}</h1>
{kpi}
<section class="sec">{s1}</section>
<section class="sec sec-rest">{s3}</section>
<section class="sec sec2">{s2}</section>
<p class="xem-them">Chi tiết tham khảo tại <span>weha.com.vn</span></p>
<footer class="foot"><div><b>WeHa - Wealth and Happiness</b> · weha.com.vn<br>Kỷ luật đầu tư bằng dữ liệu</div>
<div class="r">{foot_r}</div></footer>
</main></body></html>'''

    # luật top 100: mọi mã nêu tên trên ảnh
    ma_tren_anh = sorted(set(re.findall(r'class="(?:tm|dr-m)">([A-Z0-9]{3})<', html)))
    ngoai = [x for x in ma_tren_anh if x not in TOP]
    print("Mã trên ảnh:", ", ".join(ma_tren_anh) or "(không)")
    if ngoai:
        die(5, f"mã ngoài top {TOP_N} lọt vào ảnh: {ngoai}")

    # ---- lời bình (mẫu tin bot: câu mở đầu, dòng trống, mỗi câu một dòng "- ")
    lb = [f'Em gửi mọi người Nhiệt kế thị trường và Ngành dẫn dắt sau phiên {d.strftime("%d/%m")} ạ.', ""]
    lb.append(f'- Nhiệt kế {n(m["diem"], 1)} điểm, vùng {m["vung"]}; tỷ trọng cổ phiếu gợi ý '
              f'{"giữ ở" if eq == eq0 else verb} {eq}%.')
    if gd_dong:
        lb.append(f"- {gd_dong}")
    lb.append(f'- Top 5 ngành: {", ".join(r["nganh"] for r in top5)}.')
    if moi_vao:
        lb.append(f"- {join_vi(moi_vao)} mới vào top 5.")
    lb.append(f"- Còn {so_manh} trong {tong} mã có tín hiệu Mạnh, phiên trước là {so_manh_truoc}.")
    lb.append("- Chi tiết tham khảo tại weha.com.vn.")
    return html, "\n".join(lb) + "\n"


# ---------------------------------------------------------------- chụp ảnh
JS_OVER = """[...document.querySelectorAll('body *')].filter(e=>e.scrollWidth>e.clientWidth+1 && e.clientWidth>0)
 .map(e=>(e.className||e.tagName)+' | '+e.textContent.trim().slice(0,40))"""


async def _shot(html_path, png):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        exe = "/opt/pw-browsers/chromium"
        b = await pw.chromium.launch(**({"executable_path": exe, "args": ["--no-sandbox"]} if pathlib.Path(exe).exists() else {}))
        ctx = await b.new_context(viewport={"width": W, "height": 1350}, device_scale_factor=SCALE)
        p = await ctx.new_page()
        await p.goto(html_path.resolve().as_uri())
        await p.evaluate("document.fonts.ready")
        await p.wait_for_timeout(400)
        bad = await p.evaluate("[...document.fonts].filter(f=>f.status!='loaded').map(f=>f.family)")
        h = await p.evaluate("document.documentElement.scrollHeight")
        sw = await p.evaluate("document.documentElement.scrollWidth")
        over = await p.evaluate(JS_OVER)
        await p.screenshot(path=str(png), full_page=True)
        await b.close()
    return bad, h, sw, over


def shot(html_path, png):
    tmp = ROOT / ".tmp" / "chromium"
    if os.name == "nt":  # Windows: không để Chromium ghi tạm lên ổ C
        tmp.mkdir(parents=True, exist_ok=True)
        for k in ("TEMP", "TMP", "TMPDIR"):
            os.environ[k] = str(tmp)
    try:
        bad, h, sw, over = asyncio.run(_shot(html_path, png))
    finally:
        if os.name == "nt":
            shutil.rmtree(tmp, ignore_errors=True)
            try:
                tmp.parent.rmdir()  # chỉ xóa .tmp khi trống
            except OSError:
                pass
    print(f"Ảnh {png.name}: {round(W * SCALE)}x{round(h * SCALE)}px, CSS {W}x{h}")
    loi = []
    if bad:
        loi.append(f"font chưa tải: {bad}")
    if sw > W:
        loi.append(f"tràn ngang: rộng {sw}")
    if over:
        loi.append(f"chữ tràn: {over}")
    if loi:
        png.unlink(missing_ok=True)
        die(5, "; ".join(loi))


# ---------------------------------------------------------------- main
def main():
    for st in (sys.stdout, sys.stderr):  # in tiếng Việt được cả trên console Windows
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Ảnh Nhiệt kế + Ngành dẫn dắt (khổ ngang) cho Zalo")
    ap.add_argument("--thu", action="store_true", help="dựng thử vào thu/, bỏ qua kiểm đã dựng và số quá cũ")
    ap.add_argument("--force", action="store_true", help="dựng lại dù phiên đã có PNG")
    ap.add_argument("--nguon", default=str(ROOT / "nguon"), help="thư mục số nguồn")
    a = ap.parse_args()

    m, nganh, vutru, ls, th, gt = doc_so(pathlib.Path(a.nguon))
    phien = m["phien"]
    if ls["ngay"][-1] != phien:
        die(4, f"số hai nguồn chưa cùng phiên: Nhiệt kế {phien}, Ngành dẫn dắt {ls['ngay'][-1]}")
    cu = (hom_nay_vn() - dt.date.fromisoformat(phien)).days
    if not a.thu and cu > MAX_CU_NGAY:
        die(4, f"số quá cũ: phiên {phien} cách hôm nay {cu} ngày")

    d = dt.date.fromisoformat(phien)
    dmy = d.strftime("%d-%m-%Y")
    out = ROOT / ("thu" if a.thu else phien)
    png = out / f"NhietKe_NganhDanDat_{dmy}.png"
    if not a.thu and not a.force and png.exists():
        die(3, f"phiên này đã dựng/gửi: {png.relative_to(REPO).as_posix()}")

    html, loibinh = dung(m, nganh, vutru, ls, th, gt)
    out.mkdir(exist_ok=True)
    if a.thu:
        for f in out.glob("NhietKe_NganhDanDat_*.png"):
            f.unlink()
    hp = out / "index.html"
    hp.write_text(html, "utf8")
    shot(hp, png)
    lbp = out / "loi-binh.txt"
    lbp.write_text(loibinh, "utf8")
    print(f"PHIEN={phien}")
    print(f"DMY={dmy}")
    print(f"PNG={png.relative_to(REPO).as_posix()}")
    print(f"LOIBINH={lbp.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
