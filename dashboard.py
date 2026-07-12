import streamlit as st
import duckdb
import plotly.express as px

con = duckdb.connect("steam_analytics.duckdb")

st.set_page_config(page_title="Dashboard Phân Tích Game Steam", layout="wide")

st.title("Dashboard Phân Tích Game Steam")

st.subheader("1. Số lượng game ra mắt theo thể loại qua từng năm")

df_bq1 = con.execute("""
    SELECT
        g.genre_name,
        d.release_year,
        COUNT(DISTINCT d.game_id) AS game_count
    FROM fact_game_stats f
    JOIN dim_game d USING (game_id)
    JOIN bridge_game_genre b USING (game_id)
    JOIN dim_genre g USING (genre_id)
    GROUP BY g.genre_name, d.release_year
    ORDER BY g.genre_name, d.release_year
""").df()

fig1 = px.line(
    df_bq1,
    x="release_year",
    y="game_count",
    color="genre_name",
    title="Số lượng game ra mắt theo thể loại qua các năm",
    labels={"release_year": "Năm", "game_count": "Số lượng game", "genre_name": "Thể loại"}
)
st.plotly_chart(fig1, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ này cho thấy xu hướng số lượng game được phát hành mỗi năm theo từng thể loại. 
Những đường đi lên (ví dụ: Action, RPG) cho thấy thể loại đang tăng trưởng về mặt cung ứng, 
trong khi những đường đi ngang hoặc đi xuống (ví dụ: Casual, Indie) cho thấy thị trường đang bão hòa hoặc suy giảm. 
Đây là cơ sở để trả lời câu hỏi: "Nên phát triển thể loại game nào?"
""")

st.subheader("2. Quan hệ giữa giá bán, tỷ lệ đánh giá tích cực và số người sở hữu ước tính")

df_bq2 = con.execute("""
    SELECT
        d.price,
        AVG(f.positive / (f.positive + f.negative)) AS positive_rate,
        AVG(CASE 
                WHEN o.tier_label = 'No Data' THEN 0
                WHEN o.tier_label = 'Niche' THEN 10000
                WHEN o.tier_label = 'Small' THEN 35000
                WHEN o.tier_label = 'Medium' THEN 75000
                WHEN o.tier_label = 'Large' THEN 300000
                WHEN o.tier_label = 'Blockbuster' THEN 5000000
                ELSE 0
            END) AS avg_owners
    FROM fact_game_stats f
    JOIN dim_game d USING (game_id)
    JOIN dim_owners_tier o ON f.tier_id = o.tier_id
    GROUP BY d.price
    ORDER BY d.price
""").df()

fig2 = px.scatter(
    df_bq2,
    x="price",
    y="positive_rate",
    size="avg_owners",
    title="Giá bán và tỷ lệ review tích cực (kích thước điểm tương ứng với số người sở hữu trung bình)",
    labels={
        "price": "Giá bán (USD)",
        "positive_rate": "Tỷ lệ review tích cực (trung bình)",
        "avg_owners": "Số người sở hữu trung bình ước tính"
    },
    color_discrete_sequence=["blue"]
)
st.plotly_chart(fig2, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ phân tán này thể hiện mối quan hệ giữa giá bán (trục X) và tỷ lệ review tích cực trung bình (trục Y). 
Kích thước điểm phản ánh số lượng người sở hữu ước tính trung bình. 
Qua đó có thể nhận thấy những mức giá nào thường đi kèm với đánh giá tích cực và lượng người mua lớn, 
từ đó giúp đưa ra quyết định về chiến lược định giá sản phẩm (câu hỏi: "Nên định giá game ở mức nào?").
""")

st.subheader("3. Tổng số người sở hữu ước tính theo từng thể loại game")

df_bq3 = con.execute("""
    SELECT
        g.genre_name,
        SUM(
            CASE 
                WHEN s.estimated_owners = '0 - 0' THEN 0
                WHEN s.estimated_owners = '0 - 20000' THEN 10000
                WHEN s.estimated_owners = '20000 - 50000' THEN 35000
                WHEN s.estimated_owners = '50000 - 100000' THEN 75000
                WHEN s.estimated_owners = '100000 - 500000' THEN 300000
                WHEN s.estimated_owners = '500000 - 200000000' THEN 100250000
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
    labels={"genre_name": "Thể loại", "total_estimated_owners": "Tổng số người sở hữu ước tính", "game_count": "Số game"},
    color="game_count",
    text_auto=True
)
st.plotly_chart(fig3, use_container_width=True)

st.caption("""
**Giải thích:** Biểu đồ cột này tổng hợp số lượng người sở hữu ước tính trên toàn bộ các game thuộc từng thể loại. 
Màu sắc thể hiện số lượng game trong thể loại đó. 
Đây là thước đo nhu cầu thị trường (demand) và bổ sung cho biểu đồ số 1 (cung ứng). 
Kết hợp cả hai sẽ trả lời được câu hỏi: "Thể loại game nào có thị trường người chơi thực sự lớn?"
""")