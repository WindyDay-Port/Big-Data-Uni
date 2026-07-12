import streamlit as st
import duckdb
import plotly.express as px

con = duckdb.connect("steam_analytics.duckdb")

st.set_page_config(page_title="Dashboard Phân Tích Game Steam", layout="wide")

st.title("Dashboard Phân Tích Game Steam")

# ─────────────────────────────────────────────
# BQ1: Số lượng game ra mắt theo thể loại qua từng năm
# ─────────────────────────────────────────────
st.subheader("1. Số lượng game ra mắt theo thể loại qua từng năm")

df_bq1 = con.execute("""
    SELECT
        CAST(g.genre_name AS VARCHAR) AS genre_name,
        d.release_year,
        COUNT(DISTINCT d.game_id) AS game_count
    FROM fact_game_stats f
    JOIN dim_game d USING (game_id)
    JOIN bridge_game_genre b USING (game_id)
    JOIN dim_genre g USING (genre_id)
    WHERE d.release_year IS NOT NULL
      AND d.release_year BETWEEN 1997 AND 2024
    GROUP BY g.genre_name, d.release_year
    ORDER BY g.genre_name, d.release_year
""").df()

fig1 = px.line(
    df_bq1,
    x="release_year",
    y="game_count",
    color="genre_name",
    title="Số lượng game ra mắt theo thể loại qua các năm",
    labels={
        "release_year": "Năm",
        "game_count": "Số lượng game",
        "genre_name": "Thể loại"
    }
)
fig1.update_layout(legend_title_text="Thể loại")
st.plotly_chart(fig1, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ này cho thấy xu hướng số lượng game được phát hành mỗi năm theo từng thể loại.
Những đường đi lên cho thấy thể loại đang tăng trưởng về mặt cung ứng (supply),
trong khi những đường đi ngang hoặc đi xuống cho thấy thị trường đang bão hòa hoặc suy giảm.
Đây là cơ sở để trả lời câu hỏi: "Nên phát triển thể loại game nào?"
""")

# ─────────────────────────────────────────────
# BQ2: Quan hệ giữa giá bán, tỷ lệ review tích cực và số người sở hữu
# ─────────────────────────────────────────────
st.subheader("2. Quan hệ giữa giá bán, tỷ lệ đánh giá tích cực và số người sở hữu ước tính")

df_bq2 = con.execute("""
    SELECT
        d.price,
        -- Fix chia cho 0: chỉ tính khi có ít nhất 1 review
        AVG(
            CASE
                WHEN (f.positive + f.negative) > 0
                THEN CAST(f.positive AS DOUBLE) / (f.positive + f.negative)
                ELSE NULL
            END
        ) AS positive_rate,
        AVG(
            CASE
                WHEN o.tier_label = 'No Data'     THEN 0
                WHEN o.tier_label = 'Niche'        THEN 10000
                WHEN o.tier_label = 'Small'        THEN 35000
                WHEN o.tier_label = 'Medium'       THEN 75000
                WHEN o.tier_label = 'Large'        THEN 300000
                WHEN o.tier_label = 'Blockbuster'  THEN 5000000
                ELSE 0
            END
        ) AS avg_owners,
        COUNT(*) AS game_count
    FROM fact_game_stats f
    JOIN dim_game d USING (game_id)
    JOIN dim_owners_tier o ON f.tier_id = o.tier_id
    WHERE d.price IS NOT NULL
      AND (f.positive + f.negative) > 0
    GROUP BY d.price
    HAVING AVG(
        CASE
            WHEN (f.positive + f.negative) > 0
            THEN CAST(f.positive AS DOUBLE) / (f.positive + f.negative)
            ELSE NULL
        END
    ) IS NOT NULL
    ORDER BY d.price
""").df()

fig2 = px.scatter(
    df_bq2,
    x="price",
    y="positive_rate",
    size="avg_owners",
    size_max=60,
    hover_data={
        "price": True,
        "positive_rate": ":.1%",
        "avg_owners": ":,.0f",
        "game_count": True
    },
    title="Giá bán và tỷ lệ review tích cực\n(kích thước điểm tương ứng với số người sở hữu trung bình)",
    labels={
        "price": "Giá bán (USD)",
        "positive_rate": "Tỷ lệ review tích cực (trung bình)",
        "avg_owners": "Số người sở hữu TB ước tính",
        "game_count": "Số game"
    },
    color_discrete_sequence=["#1f77b4"]
)
fig2.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig2, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ phân tán thể hiện mối quan hệ giữa giá bán (trục X) và tỷ lệ review tích cực trung bình (trục Y).
Kích thước điểm phản ánh số người sở hữu ước tính trung bình — bubble càng lớn thì lượng người mua càng cao.
Hover vào từng điểm để xem giá bán cụ thể, tỷ lệ review tích cực, số người sở hữu TB và số game tại mức giá đó.
Đây là cơ sở để trả lời câu hỏi: "Nên định giá game ở mức nào?"
""")

# ─────────────────────────────────────────────
# BQ3: Tổng số người sở hữu ước tính theo thể loại
# ─────────────────────────────────────────────
st.subheader("3. Tổng số người sở hữu ước tính theo từng thể loại game")

df_bq3 = con.execute("""
    SELECT
        CAST(g.genre_name AS VARCHAR) AS genre_name,
        SUM(
            CASE
                WHEN s.estimated_owners = '0 - 0'           THEN 0
                WHEN s.estimated_owners = '0 - 20000'        THEN 10000
                WHEN s.estimated_owners = '20000 - 50000'    THEN 35000
                WHEN s.estimated_owners = '50000 - 100000'   THEN 75000
                -- Fix: dùng đúng string values từ dataset
                WHEN s.estimated_owners = '100000 - 200000'  THEN 150000
                WHEN s.estimated_owners = '200000 - 500000'  THEN 350000
                WHEN s.estimated_owners = '500000 - 1000000'     THEN 750000
                WHEN s.estimated_owners = '1000000 - 2000000'    THEN 1500000
                WHEN s.estimated_owners = '2000000 - 5000000'    THEN 3500000
                WHEN s.estimated_owners = '5000000 - 10000000'   THEN 7500000
                WHEN s.estimated_owners = '10000000 - 20000000'  THEN 15000000
                WHEN s.estimated_owners = '20000000 - 50000000'  THEN 35000000
                WHEN s.estimated_owners = '50000000 - 100000000' THEN 75000000
                WHEN s.estimated_owners = '100000000 - 200000000' THEN 150000000
                ELSE 0
            END
        ) AS total_estimated_owners,
        COUNT(DISTINCT s.game_id) AS game_count
    FROM stg_game s
    JOIN bridge_game_genre b ON s.game_id = b.game_id
    JOIN dim_genre g ON b.genre_id = g.genre_id
    GROUP BY g.genre_name
    ORDER BY total_estimated_owners DESC
""").df()

fig3 = px.bar(
    df_bq3,
    x="genre_name",
    y="total_estimated_owners",
    title="Tổng số người sở hữu ước tính theo thể loại",
    labels={
        "genre_name": "Thể loại",
        "total_estimated_owners": "Tổng số người sở hữu ước tính",
        "game_count": "Số game"
    },
    color="game_count",
    color_continuous_scale="Blues",
    text_auto=True
)
fig3.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig3, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ cột tổng hợp số lượng người sở hữu ước tính trên toàn bộ các game thuộc từng thể loại.
Màu sắc thể hiện số lượng game trong thể loại đó — màu đậm hơn nghĩa là ít game hơn nhưng có thể có lượng người chơi lớn.
Đây là thước đo nhu cầu thị trường (demand) và bổ sung cho biểu đồ BQ1 (supply).
Kết hợp cả hai trả lời câu hỏi: "Thể loại game nào có thị trường người chơi thực sự lớn?"
""")
