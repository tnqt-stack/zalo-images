# Nhiệt kế + Ngành dẫn dắt (ảnh ngang, gửi Zalo 8h15)

Ảnh khổ ngang WeHa bản sáng (rộng 2400 CSS, scale 1.75 → 4200px) gồm: Nhiệt kế thị trường, ô giai đoạn cho chiến lược, top 5 ngành kèm mã mạnh tiêu biểu, 17 ngành còn lại, tín hiệu mã trong top 100. Kèm `loi-binh.txt` do máy tự sinh (không ai viết tay).

## Chạy

```
python build.py                 # dựng phiên mới nhất vào nhiet-ke-nganh/<phien>/
python build.py --thu           # dựng thử vào thu/ (đè), bỏ qua kiểm "đã dựng" và "số quá cũ"
python build.py --force         # dựng lại dù phiên đã có PNG
python build.py --nguon <dir>   # đọc số từ thư mục khác
```

Cần Python 3.12+ và playwright (Chromium). Trên Linux tự dùng `/opt/pw-browsers/chromium` nếu có. Trên Windows Chromium ghi tạm vào `.tmp/` rồi xóa.

Đầu ra trong `<phien>/`: `index.html`, `NhietKe_NganhDanDat_<dd-mm-yyyy>.png`, `loi-binh.txt`. Thành công thì 4 dòng cuối là `PHIEN=`, `DMY=`, `PNG=`, `LOIBINH=` (đường dẫn tính từ gốc kho).

## Mã thoát

| Mã | Nghĩa |
|---|---|
| 0 | Xong |
| 3 | Phiên này đã dựng/gửi (đã có PNG trong thư mục phiên) |
| 4 | Số hai nguồn chưa cùng phiên (ngày Nhiệt kế khác ngày Ngành dẫn dắt), hoặc số quá cũ (phiên cũ hơn hôm nay quá 4 ngày, giờ Việt Nam) |
| 5 | Lỗi dữ liệu/ảnh: thiếu file nguồn, JSON hỏng, mã ngoài top 100 lọt vào ảnh, font không tải, chữ tràn |

## Nguồn số (KHÔNG nằm trong kho này)

Từ 25/11/2026 số đã khóa nên GitHub Actions chép vào `nguon-nhiet-ke/` của kho riêng tư zalo-room-assistant; chạy `build.py --nguon <đường dẫn tới thư mục đó>`. Không commit số nguồn vào kho công khai này.

- `nhiet-ke.json`: điểm, vùng, ngưỡng, so sánh tuần/tháng/quý, tỷ trọng, thống kê vùng.
- `ndd_nganh.json`, `ndd_vu_tru.json`, `ndd_lich_su_ma.json`: ngành, mã, lịch sử tín hiệu.
- `tin-hieu-weha.json` (không bắt buộc): giai đoạn cho chiến lược. Thiếu file, hoặc `ngay_so_lieu` cũ hơn phiên Nhiệt kế quá 7 ngày thì ảnh bỏ ô giai đoạn (hàng trên còn hero + 2 ô).

## Luật top 100

Mọi mã cổ phiếu nêu tên trên ảnh phải thuộc top 100 mã có giá trị giao dịch bình quân 20 phiên lớn nhất (`gtgd_tb20.json`, chỉ xét mã có trong `ndd_vu_tru.json`; hằng `TOP_N` trong `build.py`). Ô "Mã có tín hiệu Mạnh" đếm trên toàn bộ mã theo dõi; danh sách tên mã chỉ lấy trong top 100. Có mã ngoài top 100 lọt vào HTML thì dừng mã 5.

## Cập nhật `gtgd_tb20.json` (tay, mỗi tháng)

File tĩnh, khóa `gtgd_tb20_ty` = {mã: giá trị giao dịch bình quân 20 phiên, tỷ đồng/phiên}. Đầu mỗi tháng thay file bằng bản mới cùng cấu trúc rồi chạy `python build.py --thu` để kiểm.

## Giao diện

`style.css` = khung chung của `thong-ke-cuoi-phien/style.css` (chép nguyên) + phần ghi đè cho ảnh ngang (chép nguyên từ bản mẫu đã duyệt, giữ thứ tự) + phần ô giai đoạn Trung tính/Thuận lợi. CSS được nhúng thẳng vào HTML; font ở `assets/fonts/`, logo `assets/logo.png`.
