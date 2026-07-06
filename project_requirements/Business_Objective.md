# Business Objectives

## Overall Objective

Hệ thống data warehouse được xây dựng nhằm hỗ trợ **indie game developer và publisher nhỏ** — những người thiếu nguồn lực nghiên cứu thị trường — đưa ra **3 quyết định cốt lõi** có căn cứ dữ liệu trước khi bắt đầu phát triển game trên nền tảng Steam.

Hệ thống phân tích **125,855 game** từ Steam Games Dataset (Kaggle) để trả lời 3 câu hỏi kinh doanh sau:

---

## Business Questions

### BQ1: Tôi nên làm thể loại game nào?

> Genre nào đang tăng trưởng về số lượng game ra mắt theo năm, và genre nào đã bão hòa?

- **Fields sử dụng:** `genres`, `release_date`
- **Góc nhìn:** Supply — phân tích theo chiều thời gian (trend theo năm)
- **Giá trị thực tế:** Giúp developer tránh đổ công sức vào genre đã quá đông (ví dụ: Casual, Indie tràn lan) và nhận ra genre nào còn dư địa để gia nhập.

---

### BQ2: Tôi nên định giá bao nhiêu khi launch?

> Mức giá nào có tỷ lệ review tích cực cao nhất và lượng người sở hữu game lớn nhất?

- **Fields sử dụng:** `price`, `positive`, `negative`, `estimated_owners`
- **Giá trị thực tế:** Người mới làm game thường định giá sai — hoặc quá rẻ (mất doanh thu) hoặc quá đắt (mất người mua). Câu hỏi này cung cấp căn cứ dữ liệu để chọn price tier tối ưu.

---

### BQ3: Genre tôi chọn có người chơi thực không?

> Genre nào có thị trường người chơi thực sự lớn (estimated owners cao)?

- **Fields sử dụng:** `genres`, `estimated_owners`
- **Góc nhìn:** Demand — phân tích snapshot thị trường hiện tại
- **Giá trị thực tế:** Bổ sung cho BQ1 — BQ1 nhìn phía supply (số game được ra), BQ3 nhìn phía demand (số người chơi thực sự). Kết hợp cả hai mới đủ căn cứ để ra quyết định chọn genre.

---

## Tổng hợp Fields sử dụng

| Field | BQ1 | BQ2 | BQ3 |
|-------|-----|-----|-----|
| `genres` | ✓ | | ✓ |
| `release_date` | ✓ | | |
| `price` | | ✓ | |
| `positive` | | ✓ | |
| `negative` | | ✓ | |
| `estimated_owners` | | ✓ | ✓ |

---

## Lưu ý về Data

- `estimated_owners` là dạng **range bucket cố định** của Steam (ví dụ: `"20000 - 50000"`), được xử lý trong ETL bằng cách map sang ordinal tier. Kết quả phân tích mang tính **so sánh tương đối**, không phải con số tuyệt đối.
- Các record rác cần lọc trong ETL: game bị xóa khỏi Steam, `estimated_owners = "0 - 0"`, `positive = 0` và `negative = 0` đồng thời.
