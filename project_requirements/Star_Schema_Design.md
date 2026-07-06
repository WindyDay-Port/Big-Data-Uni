# Star Schema Design

## Overview

- **Grain:** 1 row trong `fact_game_stats` = 1 game
- **Loại Fact Table:** Snapshot fact (dữ liệu tĩnh tại thời điểm thu thập)
- **Tổng số bảng:** 5 (1 fact + 3 dimension + 1 bridge)

---

## Schema Diagram

```
                    dim_genre
                   ┌──────────────┐
                   │ genre_id (PK)│
                   │ genre_name   │
                   └──────┬───────┘
                          │
                   bridge_game_genre
                   ┌──────────────┐
                   │ game_id (FK) │
                   │ genre_id (FK)│
                   └──────┬───────┘
                          │
dim_owners_tier    dim_game        fact_game_stats
┌─────────────┐   ┌──────────────┐   ┌─────────────────┐
│ tier_id(PK) │   │ game_id (PK) │──▶│ fact_id (PK)    │
│ tier_label  │   │ name         │   │ game_id (FK)    │
│ range_min   │   │ price        │   │ tier_id (FK)    │
│ range_max   │◀──│ release_year │   │ positive        │
└─────────────┘   └──────────────┘   │ negative        │
                                     └─────────────────┘
```

---

## Chi tiết các bảng

### 1. `fact_game_stats` — Fact Table

| Column | Type | Mô tả |
|--------|------|-------|
| `fact_id` | INT (PK) | Surrogate key |
| `game_id` | INT (FK) | Trỏ về `dim_game` |
| `tier_id` | INT (FK) | Trỏ về `dim_owners_tier` |
| `positive` | INT | Số review tích cực |
| `negative` | INT | Số review tiêu cực |

---

### 2. `dim_game` — Dimension

| Column | Type | Mô tả |
|--------|------|-------|
| `game_id` | INT (PK) | Surrogate key |
| `name` | VARCHAR | Tên game |
| `price` | FLOAT | Giá bán (USD) |
| `release_year` | INT | Năm ra mắt (extract từ `release_date`) |

---

### 3. `dim_genre` — Dimension

| Column | Type | Mô tả |
|--------|------|-------|
| `genre_id` | INT (PK) | Surrogate key |
| `genre_name` | VARCHAR | Tên thể loại (ví dụ: Action, RPG, Indie) |

---

### 4. `dim_owners_tier` — Dimension

| Column | Type | Mô tả |
|--------|------|-------|
| `tier_id` | INT (PK) | Surrogate key |
| `tier_label` | VARCHAR | Nhãn tier (ví dụ: Niche, Small, Medium, Large, Blockbuster) |
| `range_min` | INT | Giá trị nhỏ nhất của range |
| `range_max` | INT | Giá trị lớn nhất của range |

**Mapping mẫu:**

| tier_id | tier_label | range_min | range_max |
|---------|-----------|-----------|-----------|
| 1 | No Data | 0 | 0 |
| 2 | Niche | 0 | 20,000 |
| 3 | Small | 20,000 | 50,000 |
| 4 | Medium | 50,000 | 100,000 |
| 5 | Large | 100,000 | 500,000 |
| 6 | Blockbuster | 500,000 | 200,000,000+ |

---

### 5. `bridge_game_genre` — Bridge Table

| Column | Type | Mô tả |
|--------|------|-------|
| `game_id` | INT (FK) | Trỏ về `dim_game` |
| `genre_id` | INT (FK) | Trỏ về `dim_genre` |

> Xử lý quan hệ many-to-many: 1 game có thể thuộc nhiều genre.

---

## Join Path cho từng Business Question

### BQ1: Genre nào tăng trưởng theo năm?

```sql
fact_game_stats
  JOIN dim_game ON fact_game_stats.game_id = dim_game.game_id
  JOIN bridge_game_genre ON dim_game.game_id = bridge_game_genre.game_id
  JOIN dim_genre ON bridge_game_genre.genre_id = dim_genre.genre_id
GROUP BY dim_genre.genre_name, dim_game.release_year
```

---

### BQ2: Mức giá nào có review tốt và lượng người mua lớn?

```sql
fact_game_stats
  JOIN dim_game ON fact_game_stats.game_id = dim_game.game_id
  JOIN dim_owners_tier ON fact_game_stats.tier_id = dim_owners_tier.tier_id
GROUP BY dim_game.price, dim_owners_tier.tier_label
```

---

### BQ3: Genre nào có thị trường người chơi lớn?

```sql
fact_game_stats
  JOIN dim_owners_tier ON fact_game_stats.tier_id = dim_owners_tier.tier_id
  JOIN bridge_game_genre ON fact_game_stats.game_id = bridge_game_genre.game_id
  JOIN dim_genre ON bridge_game_genre.genre_id = dim_genre.genre_id
GROUP BY dim_genre.genre_name, dim_owners_tier.tier_label
```

---

## Lưu ý

- **Grain rõ ràng:** 1 row trong `fact_game_stats` = 1 game, không phải 1 game-genre pair. Quan hệ với genre được handle qua `bridge_game_genre`.
- **`release_year`** được extract từ field `release_date` gốc trong quá trình ETL — chỉ lấy năm, bỏ tháng và ngày vì BQ1 chỉ cần granularity theo năm.
- **`estimated_owners`** được convert từ string range sang `tier_id` trong ETL trước khi load vào fact table.
- Các record rác cần lọc trong ETL: game bị xóa khỏi Steam, `estimated_owners = "0 - 0"`.
