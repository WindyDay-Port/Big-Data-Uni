import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Steam Game Analytics",
    page_icon="🎮",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return duckdb.connect("steam_analytics.duckdb", read_only=True)

con = get_connection()

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: map estimated_owners string → midpoint number
# Dùng đúng string values từ dataset thực tế (kiểm tra từ data_sample.json)
# ─────────────────────────────────────────────────────────────────────────────
OWNERS_MIDPOINT_EXPR = """
    CASE estimated_owners
        WHEN '0 - 20000'             THEN 10000
        WHEN '20000 - 50000'         THEN 35000
        WHEN '50000 - 100000'        THEN 75000
        WHEN '100000 - 200000'       THEN 150000
        WHEN '200000 - 500000'       THEN 350000
        WHEN '500000 - 1000000'      THEN 750000
        WHEN '1000000 - 2000000'     THEN 1500000
        WHEN '2000000 - 5000000'     THEN 3500000
        WHEN '5000000 - 10000000'    THEN 7500000
        WHEN '10000000 - 20000000'   THEN 15000000
        WHEN '20000000 - 50000000'   THEN 35000000
        WHEN '50000000 - 100000000'  THEN 75000000
        WHEN '100000000 - 200000000' THEN 150000000
        ELSE 0
    END
"""

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎮 Steam Game Analytics Dashboard")
st.markdown("""
Dashboard phân tích xu hướng game trên Steam dành cho **indie developer** và **small publisher**.  
Dữ liệu từ Steam Games Dataset (Kaggle) — ~125,000 games.
""")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_kpis():
    return con.execute("""
        SELECT
            COUNT(DISTINCT game_id)                          AS total_games,
            COUNT(DISTINCT genre_id)                         AS total_genres,
            SUM(positive + negative)                         AS total_reviews,
            ROUND(AVG(CASE WHEN price > 0 THEN price END), 2) AS avg_price
        FROM fact_game_stats f
        JOIN bridge_game_genre b USING (game_id)
    """).df()

kpi = load_kpis().iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tổng số game", f"{int(kpi['total_games']):,}")
c2.metric("Số thể loại", f"{int(kpi['total_genres'])}")
c3.metric("Tổng lượt review", f"{int(kpi['total_reviews']):,}")
c4.metric("Giá trung bình", f"${kpi['avg_price']:.2f}")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# BQ1: Genre nào tăng trưởng theo năm?
# Metric: số lượng game được publish mỗi năm theo genre
# ─────────────────────────────────────────────────────────────────────────────
st.header("📈 BQ1 — Genre nào đang tăng trưởng?")
st.markdown("""
**Phương pháp:** Đếm số game được publish mỗi năm theo từng genre.  
Genre có số lượng game tăng dần = thị trường đang mở rộng về phía supply.  
> ⚠️ *Lưu ý: đây là chỉ số supply (số game được phát hành), không phải doanh thu hay revenue.*
""")

@st.cache_data
def load_bq1():
    return con.execute("""
        SELECT
            g.genre_name,
            d.release_year,
            COUNT(DISTINCT f.game_id) AS game_count
        FROM fact_game_stats f
        JOIN dim_game d        USING (game_id)
        JOIN bridge_game_genre b USING (game_id)
        JOIN dim_genre g        USING (genre_id)
        WHERE d.release_year IS NOT NULL
          AND d.release_year BETWEEN 2000 AND 2024
        GROUP BY g.genre_name, d.release_year
        ORDER BY g.genre_name, d.release_year
    """).df()

df_bq1 = load_bq1()

# Sidebar filter: chọn genre muốn xem
all_genres = sorted(df_bq1["genre_name"].unique().tolist())

# Mặc định chọn top 8 genre có tổng game nhiều nhất
top8 = (
    df_bq1.groupby("genre_name")["game_count"]
    .sum()
    .nlargest(8)
    .index.tolist()
)

selected_genres_bq1 = st.multiselect(
    "Chọn thể loại để hiển thị (BQ1):",
    options=all_genres,
    default=top8,
    key="bq1_genres"
)

if selected_genres_bq1:
    df_bq1_filtered = df_bq1[df_bq1["genre_name"].isin(selected_genres_bq1)]
    fig1 = px.line(
        df_bq1_filtered,
        x="release_year",
        y="game_count",
        color="genre_name",
        markers=True,
        labels={
            "release_year": "Năm",
            "game_count": "Số lượng game",
            "genre_name": "Thể loại"
        },
        title="Số lượng game ra mắt theo thể loại qua các năm (2000–2024)"
    )
    fig1.update_layout(
        legend_title_text="Thể loại",
        hovermode="x unified",
        xaxis=dict(dtick=2)
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning("Vui lòng chọn ít nhất một thể loại.")

# Bảng tóm tắt top 10 genre tăng trưởng mạnh nhất (so sánh 2019 vs 2023)
st.markdown("##### Top 10 genre có tổng số game nhiều nhất (tính đến 2024)")
df_summary_bq1 = (
    df_bq1.groupby("genre_name")["game_count"]
    .sum()
    .reset_index()
    .rename(columns={"game_count": "Tổng số game (2000–2024)"})
    .sort_values("Tổng số game (2000–2024)", ascending=False)
    .head(10)
    .reset_index(drop=True)
)
df_summary_bq1.index += 1
st.dataframe(df_summary_bq1, use_container_width=True)

with st.expander("💡 Insight BQ1"):
    st.markdown("""
    - **Indie** là thể loại có số lượng game ra mắt lớn nhất và tăng trưởng mạnh nhất từ 2012 đến nay.
    - **Action**, **Adventure**, **Casual** cũng tăng đều đặn theo năm.
    - Hầu hết thể loại có peak vào khoảng **2022–2023** sau đó giảm nhẹ — có thể do hiệu ứng cắt giảm sau COVID boom.
    - **Khuyến nghị:** Các genre như Action, RPG, Simulation vẫn đang tăng trưởng ổn định và ít bão hòa hơn Indie.
    """)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# BQ2: Mức giá nào có review tốt và lượng mua cao?
# Metric: avg positive_rate và avg estimated_owners theo price bucket
# ─────────────────────────────────────────────────────────────────────────────
st.header("💰 BQ2 — Mức giá nào tối ưu?")
st.markdown("""
**Phương pháp:** Phân tích mối quan hệ giữa giá bán, tỷ lệ review tích cực và lượng người sở hữu ước tính.  
Chỉ tính các game có ít nhất 10 reviews để đảm bảo độ tin cậy thống kê.
""")

@st.cache_data
def load_bq2_scatter():
    """Raw data cho bubble chart — group theo price"""
    return con.execute(f"""
        SELECT
            d.price,
            ROUND(
                AVG(CAST(f.positive AS DOUBLE) / (f.positive + f.negative)) * 100,
                1
            ) AS positive_rate_pct,
            ROUND(AVG({OWNERS_MIDPOINT_EXPR}), 0) AS avg_owners,
            COUNT(*) AS game_count
        FROM fact_game_stats f
        JOIN dim_game d USING (game_id)
        JOIN stg_game s USING (game_id)
        WHERE d.price IS NOT NULL
          AND d.price > 0
          AND d.price <= 60
          AND (f.positive + f.negative) >= 10
        GROUP BY d.price
        HAVING COUNT(*) >= 3
        ORDER BY d.price
    """).df()

@st.cache_data
def load_bq2_bucket():
    """Group theo price bucket cho bảng tóm tắt"""
    return con.execute(f"""
        SELECT
            CASE
                WHEN d.price = 0             THEN '① Free'
                WHEN d.price <= 5            THEN '② $0–5'
                WHEN d.price <= 10           THEN '③ $5–10'
                WHEN d.price <= 20           THEN '④ $10–20'
                WHEN d.price <= 30           THEN '⑤ $20–30'
                WHEN d.price <= 60           THEN '⑥ $30–60'
                ELSE                              '⑦ >$60'
            END AS price_bucket,
            COUNT(*)                                      AS game_count,
            ROUND(
                AVG(CAST(f.positive AS DOUBLE) / (f.positive + f.negative)) * 100,
                1
            )                                             AS avg_positive_rate_pct,
            ROUND(AVG({OWNERS_MIDPOINT_EXPR}), 0)         AS avg_owners_estimate
        FROM fact_game_stats f
        JOIN dim_game d   USING (game_id)
        JOIN stg_game s   USING (game_id)
        WHERE (f.positive + f.negative) >= 10
        GROUP BY price_bucket
        ORDER BY price_bucket
    """).df()

df_bq2_scatter = load_bq2_scatter()
df_bq2_bucket  = load_bq2_bucket()

col_left, col_right = st.columns([2, 1])

with col_left:
    fig2 = px.scatter(
        df_bq2_scatter,
        x="price",
        y="positive_rate_pct",
        size="avg_owners",
        size_max=70,
        hover_name="price",
        hover_data={
            "price":            ":.2f",
            "positive_rate_pct":":.1f",
            "avg_owners":       ":,.0f",
            "game_count":       True
        },
        labels={
            "price":             "Giá bán (USD)",
            "positive_rate_pct": "Tỷ lệ review tích cực TB (%)",
            "avg_owners":        "Số người sở hữu TB ước tính",
            "game_count":        "Số game"
        },
        title="Giá bán vs Tỷ lệ review tích cực\n(bubble size = số người sở hữu TB ước tính)",
        color_discrete_sequence=["#1f77b4"]
    )
    fig2.update_layout(yaxis_title="Tỷ lệ review tích cực TB (%)")
    st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.markdown("##### Tóm tắt theo khoảng giá")
    df_display = df_bq2_bucket.rename(columns={
        "price_bucket":          "Khoảng giá",
        "game_count":            "Số game",
        "avg_positive_rate_pct": "Review tích cực TB (%)",
        "avg_owners_estimate":   "Người sở hữu TB ước tính"
    })
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with st.expander("💡 Insight BQ2"):
    st.markdown("""
    - Game trong khoảng **$5–20** thường có tỷ lệ review tích cực cao và lượng người sở hữu lớn — đây là **sweet spot** cho indie developer.
    - Game **free-to-play** có lượng người sở hữu rất lớn nhưng tỷ lệ review tích cực thấp hơn paid games.
    - Game giá **>$30** có ít người sở hữu hơn, nhưng những game lớn (AAA) có bubble rất to — không phù hợp với indie.
    - **Khuyến nghị:** Định giá trong khoảng **$9.99–$19.99** cho indie game để cân bằng giữa accessibility và perceived value.
    """)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# BQ3: Genre nào có thị trường người chơi lớn nhất?
# Metric: tổng estimated owners (dùng midpoint) theo genre
# ─────────────────────────────────────────────────────────────────────────────
st.header("🌍 BQ3 — Genre nào có thị trường người chơi lớn nhất?")
st.markdown("""
**Phương pháp:** Tính tổng số người sở hữu ước tính (dùng midpoint của mỗi range) theo từng genre.  
Màu sắc thể hiện số lượng game trong genre đó — phân biệt giữa **demand** (người chơi) và **supply** (số game).
""")

@st.cache_data
def load_bq3():
    return con.execute(f"""
        SELECT
            g.genre_name,
            SUM({OWNERS_MIDPOINT_EXPR}) AS total_estimated_owners,
            COUNT(DISTINCT s.game_id)   AS game_count,
            ROUND(
                AVG({OWNERS_MIDPOINT_EXPR}), 0
            )                           AS avg_owners_per_game
        FROM stg_game s
        JOIN bridge_game_genre b ON s.game_id = b.game_id
        JOIN dim_genre g          ON b.genre_id = g.genre_id
        GROUP BY g.genre_name
        ORDER BY total_estimated_owners DESC
    """).df()

df_bq3 = load_bq3()

# Slider: hiển thị top N genres
top_n = st.slider("Hiển thị top N thể loại:", min_value=5, max_value=30, value=15, step=1)
df_bq3_top = df_bq3.head(top_n)

fig3 = px.bar(
    df_bq3_top,
    x="genre_name",
    y="total_estimated_owners",
    color="game_count",
    color_continuous_scale="Blues",
    text_auto=".3s",
    hover_data={
        "genre_name":            True,
        "total_estimated_owners":":,.0f",
        "game_count":            True,
        "avg_owners_per_game":   ":,.0f"
    },
    labels={
        "genre_name":             "Thể loại",
        "total_estimated_owners": "Tổng số người sở hữu ước tính",
        "game_count":             "Số game",
        "avg_owners_per_game":    "Người sở hữu TB / game"
    },
    title=f"Top {top_n} thể loại theo tổng số người sở hữu ước tính"
)
fig3.update_layout(
    xaxis_tickangle=-40,
    coloraxis_colorbar_title="Số game",
)
st.plotly_chart(fig3, use_container_width=True)

# Bảng chi tiết
st.markdown("##### Bảng chi tiết tất cả thể loại")
df_bq3_display = df_bq3.rename(columns={
    "genre_name":             "Thể loại",
    "total_estimated_owners": "Tổng người sở hữu ước tính",
    "game_count":             "Số game",
    "avg_owners_per_game":    "Người sở hữu TB / game"
}).reset_index(drop=True)
df_bq3_display.index += 1
st.dataframe(df_bq3_display, use_container_width=True)

with st.expander("💡 Insight BQ3"):
    st.markdown("""
    - **Indie** dẫn đầu tổng số người sở hữu nhờ volume game lớn nhất — nhưng cũng có nghĩa là **cạnh tranh cao nhất**.
    - **Action**, **Adventure**, **Casual** có tổng người sở hữu lớn với số lượng game ít hơn Indie — **tỷ lệ người chơi / game cao hơn**.
    - Kết hợp với BQ1: genre có **supply thấp nhưng demand cao** (avg owners/game lớn) là cơ hội tốt nhất cho indie developer.
    - **Khuyến nghị:** Xem cột "Người sở hữu TB / game" — genre nào có số này lớn nhưng số game ít = blue ocean opportunity.
    """)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TỔNG HỢP: Supply vs Demand matrix
# ─────────────────────────────────────────────────────────────────────────────
st.header("🔍 Tổng hợp — Ma trận Supply vs Demand theo Genre")
st.markdown("""
Kết hợp BQ1 và BQ3: trục X là số game được publish (supply), trục Y là tổng người sở hữu ước tính (demand).  
**Góc trên bên trái** = demand cao, supply thấp → cơ hội tốt nhất.
""")

@st.cache_data
def load_matrix():
    return con.execute(f"""
        SELECT
            g.genre_name,
            COUNT(DISTINCT f.game_id)   AS total_games,
            SUM({OWNERS_MIDPOINT_EXPR}) AS total_owners
        FROM fact_game_stats f
        JOIN stg_game s          USING (game_id)
        JOIN bridge_game_genre b USING (game_id)
        JOIN dim_genre g         USING (genre_id)
        GROUP BY g.genre_name
        HAVING COUNT(DISTINCT f.game_id) >= 100
        ORDER BY total_owners DESC
    """).df()

df_matrix = load_matrix()

fig4 = px.scatter(
    df_matrix,
    x="total_games",
    y="total_owners",
    text="genre_name",
    size="total_owners",
    size_max=50,
    labels={
        "total_games":  "Số game được publish (Supply)",
        "total_owners": "Tổng người sở hữu ước tính (Demand)",
        "genre_name":   "Thể loại"
    },
    title="Supply vs Demand theo Genre",
    color_discrete_sequence=["#2196F3"]
)
fig4.update_traces(textposition="top center", textfont_size=11)
fig4.update_layout(showlegend=False)
st.plotly_chart(fig4, use_container_width=True)

st.caption("""
**Cách đọc:** Genre nằm ở góc trên bên trái (demand cao, supply thấp) là cơ hội tốt nhất cho indie developer.
Genre nằm ở góc dưới bên phải (supply cao, demand thấp) là thị trường bão hòa.
""")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption("📊 Dữ liệu: Steam Games Dataset (Kaggle) | Pipeline: MongoDB → PySpark → Parquet → dbt → DuckDB")
