# ETL Pipeline Design

## Kiến trúc tổng thể

```
Kaggle JSON (125,855 game)
        ↓
MongoDB — Raw layer
        ↓
PySpark — Flatten layer
        ↓
BigQuery — Staging table
        ↓
dbt — Business transform layer
        ↓
BigQuery — Marts (Star Schema)
```

**Nguyên tắc thiết kế cốt lõi:** Mỗi layer có input/output rõ ràng và **chỉ chịu trách nhiệm 1 việc** — không layer nào trùng lặp business logic với layer khác. Đây là điểm mấu chốt giải quyết mâu thuẫn ban đầu khi xác định "nên explode `genres` array ở bước nào".

---

## Chi tiết từng layer

### 1. MongoDB — Raw layer

- **Input:** File JSON gốc từ Kaggle
- **Xử lý:** Không xử lý gì cả — giả lập tình huống "data khi crawl về sẽ lưu trực tiếp vào MongoDB" giống kiến trúc data warehouse thực tế của doanh nghiệp
- **Output:** 1 document MongoDB = 1 record JSON gốc, giữ nguyên toàn bộ field (kể cả các field không dùng như `tags`, `developers`, `categories`)
- **Lý do giữ nguyên toàn bộ field:** Đây là nguyên tắc của raw layer — raw phải là bản sao y nguyên data đầu vào. Việc chọn field nào dùng là trách nhiệm của bước sau, không phải của raw layer.

---

### 2. PySpark — Flatten layer

- **Input:** Document từ MongoDB
- **Xử lý:**
  - **Select** — chỉ lấy 6 field cần dùng: `genres`, `release_date`, `price`, `positive`, `negative`, `estimated_owners`
  - **Flatten kiểu dữ liệu** — convert types đúng (string → float cho `price`, string → date cho `release_date`)
  - **KHÔNG explode `genres` array** — giữ nguyên dạng string nối (ví dụ: `"Casual,Indie,Strategy"`)
  - **KHÔNG áp dụng business logic** — không tạo tier cho `estimated_owners`, không tính `release_year`
- **Output:** Bảng phẳng (tabular), **grain = 1 dòng / 1 game**
- **Lý do dùng PySpark dù dataset chỉ ~125K record:** Thiết kế pipeline có khả năng scale, giả lập tình huống dữ liệu sẽ tăng lên hàng triệu record trong tương lai.

---

### 3. BigQuery — Staging table

- **Input:** Bảng phẳng từ PySpark
- **Xử lý:** Không transform — chỉ là điểm chứa trung gian giữa Extract/Flatten và Transform
- **Output:** Staging table với schema gần raw nhất, đã đúng kiểu dữ liệu, grain = 1 game / dòng
- **Lý do tách staging riêng khỏi marts:** Để dễ kiểm tra/debug dữ liệu trước khi áp dụng business logic, và tách biệt rõ trách nhiệm ELT (Load trước, Transform sau) khỏi pattern ETL truyền thống.

---

### 4. dbt — Business transform layer

- **Input:** Staging table
- **Xử lý (toàn bộ business logic dồn về layer này):**
  - **Explode `genres`** từ string thành nhiều dòng → tạo `bridge_game_genre` (xử lý quan hệ many-to-many giữa game và genre)
  - **Map `estimated_owners`** (dạng range string) sang `tier_id` ordinal → tạo `dim_owners_tier`
  - **Extract `release_year`** từ `release_date` → đưa vào `dim_game`
  - **Build star schema** hoàn chỉnh: `dim_game`, `dim_genre`, `dim_owners_tier`, `bridge_game_genre`, `fact_game_stats`
  - **Lọc record rác:** loại bỏ game bị xóa khỏi Steam (`"(Removed from steam store)"`), loại `estimated_owners = "0 - 0"`
- **Output:** Star schema hoàn chỉnh, sẵn sàng cho BQ1, BQ2, BQ3

---

### 5. BigQuery — Marts

- **Input:** Output từ dbt
- **Xử lý:** Không transform thêm — chỉ chứa kết quả cuối
- **Output:** Star schema (`dim_game`, `dim_genre`, `dim_owners_tier`, `bridge_game_genre`, `fact_game_stats`), sẵn sàng cho query phục vụ 3 Business Questions

---

## Bảng phân chia trách nhiệm (Contract giữa các layer)

| Layer | Công cụ | Được làm | Không được làm |
|-------|---------|----------|-----------------|
| Raw | MongoDB | Lưu y nguyên JSON gốc | Lọc field, sửa dữ liệu |
| Flatten | PySpark | Select field, convert kiểu dữ liệu | Explode array, business logic |
| Staging | BigQuery | Chứa bảng phẳng, grain = 1 game/dòng | Transform |
| Business Transform | dbt | Explode genres, map tier, build star schema, lọc record rác | — |
| Marts | BigQuery | Chứa kết quả cuối | Transform thêm |

---

## Lưu ý quan trọng

- **Tại sao không explode `genres` ngay ở PySpark:** Nếu explode sớm, staging table sẽ mất grain rõ ràng (1 dòng = 1 game), các cột khác (`price`, `positive`, `negative`) sẽ bị lặp lại theo số lượng genre — vi phạm nguyên tắc chuẩn hóa và gây khó khăn khi validate dữ liệu ở tầng staging.
- **Tại sao 2 lần BigQuery (staging và marts) không phải là 2 hệ thống riêng biệt:** Đây là 2 dataset/schema khác nhau trong cùng 1 BigQuery project, theo pattern ELT — Load trước (staging), Transform sau (dbt → marts).
- **MongoDB trong pipeline này là raw storage giả lập**, không phải kết quả crawl thực tế — dataset gốc lấy từ Kaggle, nhưng được lưu vào MongoDB để mô phỏng kiến trúc data warehouse gần giống thực tế doanh nghiệp.
