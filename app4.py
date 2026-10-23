from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard Pokemon", layout="wide")

RAW_FILE = Path(__file__).parent / "pokemon_complete_stats.csv"
STATS = ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]



# DATA CLEANING
@st.cache_data
def load_and_clean(path):
    df = pd.read_csv(path)

    # 1. Hapus duplikat
    df = df.drop_duplicates()

    # 2. Rapikan teks
    df["name"] = df["name"].str.strip().str.lower()
    for col in ["type_1", "type_2", "color", "shape"]:
        df[col] = df[col].str.strip().str.title()

    # 3. Isi nilai kosong
    df["type_2"] = df["type_2"].fillna("Tidak Ada")
    df["abilities"] = df["abilities"].fillna("Tidak Diketahui")

    # 4. Kolom baru (Base / Mega / Gigantamax / dst)
    df["form_type"] = "Base"
    df.loc[df["id"] > 10000, "form_type"] = "Other Form"
    df.loc[df["name"].str.contains("-mega"), "form_type"] = "Mega"
    df.loc[df["name"].str.contains("-gmax"), "form_type"] = "Gigantamax"
    df.loc[df["name"].str.contains("-alola"), "form_type"] = "Alolan"
    df.loc[df["name"].str.contains("-galar"), "form_type"] = "Galarian"
    df.loc[df["name"].str.contains("-hisui"), "form_type"] = "Hisuian"
    df.loc[df["name"].str.contains("-paldea"), "form_type"] = "Paldean"

    # 5. Total base stat
    df["base_stat_total"] = df[STATS].sum(axis=1)

    # 6. Kategori Pokemon
    df["category"] = np.where(df["is_mythical"], "Mythical",
                              np.where(df["is_legendary"], "Legendary", "Regular"))

    # 7. Generasi pokemon
    df["generation_num"] = df["generation"].map({
        "generation-i": 1, "generation-ii": 2, "generation-iii": 3,
        "generation-iv": 4, "generation-v": 5, "generation-vi": 6,
        "generation-vii": 7, "generation-viii": 8, "generation-ix": 9})
    df["generation_label"] = "Gen " + df["generation_num"].astype(str)

    # 8. Konversi satuan tinggi dan berat
    df["height_m"] = df["height_dm"] / 10
    df["weight_kg"] = df["weight_hg"] / 10

    # 9. Nama untuk tampilan
    df["name_display"] = df["name"].str.replace("-", " ").str.title()

    # 10. Isi base_experience dengan median per form_type
    df["base_exp_imputed"] = df["base_experience"].isnull()
    df["base_experience"] = df["base_experience"].fillna(
        df.groupby("form_type")["base_experience"].transform("median")
    )
    df["base_experience"] = df["base_experience"].astype(int)

    return df


df = load_and_clean(RAW_FILE)


st.title("Dashboard Pokemon Complete Stats")
st.markdown(
    f"Dashboard interaktif untuk mengeksplorasi **{len(df):,} Pokemon** (spesies dasar + varian "
    "seperti Mega, Gigantamax, dan bentuk regional) dari dataset Kaggle . "
    "https://www.kaggle.com/datasets/shreyashautomation/pokemon-stats-dataset"
)


st.sidebar.header("Filter Data")

gen_options = sorted(df["generation_label"].unique(), key=lambda x: int(x.split()[1]))
gen_sel = st.sidebar.multiselect("Generasi", gen_options, default=gen_options)

type_options = sorted(df["type_1"].unique())
type_sel = st.sidebar.multiselect("Tipe Utama (type_1)", type_options, default=type_options)

cat_options = ["Regular", "Legendary", "Mythical"]
cat_sel = st.sidebar.multiselect("Kategori", cat_options, default=cat_options)

include_forms = st.sidebar.checkbox("Sertakan varian (Mega, Gigantamax, dll)", value=True)

bst_min, bst_max = int(df["base_stat_total"].min()), int(df["base_stat_total"].max())
bst_sel = st.sidebar.slider("Rentang Base Stat Total", bst_min, bst_max, (bst_min, bst_max))

filtered = df[
    df["generation_label"].isin(gen_sel)
    & df["type_1"].isin(type_sel)
    & df["category"].isin(cat_sel)
    & df["base_stat_total"].between(bst_sel[0], bst_sel[1])
]
if not include_forms:
    filtered = filtered[filtered["form_type"] == "Base"]

st.sidebar.caption(f"Menampilkan {len(filtered):,} dari {len(df):,} Pokemon")

if filtered.empty:
    st.warning("Tidak ada data yang sesuai dengan filter. Silakan ubah pilihan filter.")
    st.stop()


strongest = filtered.loc[filtered["base_stat_total"].idxmax()]
n_special = int((filtered["category"] != "Regular").sum())

k1, k2, k3, k4, k5 = st.columns([1, 1, 1, 1, 1.5])
k1.metric("Total Pokemon", f"{len(filtered):,}")
k2.metric("Rata-rata Base Stat Total", f"{filtered['base_stat_total'].mean():.0f}")
k3.metric("Legendary + Mythical", f"{n_special:,}", f"{n_special / len(filtered):.1%} dari total", delta_color="off")
k4.metric("Rata-rata Capture Rate", f"{filtered['capture_rate'].mean():.0f}")
k5.caption("Terkuat (BST)")
k5.subheader(strongest["name_display"])
k5.caption(f"BST: {int(strongest['base_stat_total'])}")

st.divider()


c1, c2 = st.columns([3, 2])

with c1:
    type_count = filtered["type_1"].value_counts().reset_index()
    type_count.columns = ["type_1", "jumlah"]
    fig = px.bar(type_count, x="type_1", y="jumlah", color="type_1", text="jumlah",
                 title="Jumlah Pokemon per Tipe Utama",
                 labels={"type_1": "Tipe", "jumlah": "Jumlah"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

with c2:
    cat_count = filtered["category"].value_counts().reset_index()
    cat_count.columns = ["category", "jumlah"]
    fig = px.pie(cat_count, names="category", values="jumlah", hole=0.45,
                 title="Proporsi Kategori Pokemon")
    st.plotly_chart(fig, width="stretch")


c3, c4 = st.columns(2)

with c3:
    gen_avg = (filtered.groupby(["generation_num", "generation_label"], as_index=False)
               ["base_stat_total"].mean().sort_values("generation_num"))
    fig = px.line(gen_avg, x="generation_label", y="base_stat_total", markers=True,
                  title="Rata-rata Base Stat Total per Generasi",
                  labels={"generation_label": "Generasi", "base_stat_total": "Rata-rata BST"})
    st.plotly_chart(fig, width="stretch")

with c4:
    fig = px.histogram(filtered, x="base_stat_total", nbins=30, color="category",
                       title="Distribusi Base Stat Total",
                       labels={"base_stat_total": "Base Stat Total", "count": "Jumlah"})
    fig.update_layout(barmode="stack", yaxis_title="Jumlah")
    st.plotly_chart(fig, width="stretch")



c5, c6 = st.columns(2)

with c5:
    fig = px.scatter(filtered, x="attack", y="defense", color="category", size="hp",
                     hover_name="name_display", opacity=0.7,
                     title="Attack vs Defense (ukuran titik = HP)",
                     labels={"attack": "Attack", "defense": "Defense"})
    st.plotly_chart(fig, width="stretch")

with c6:
    heat = filtered.groupby("type_1")[STATS].mean().round(0)
    fig = px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale="YlOrRd",
                    title="Heatmap Rata-rata Stat per Tipe",
                    labels={"x": "Stat", "y": "Tipe", "color": "Rata-rata"})
    st.plotly_chart(fig, width="stretch")



st.divider()
st.subheader("10 Pokemon dengan Base Stat Total Tertinggi")
top10 = filtered.nlargest(10, "base_stat_total")[
    ["name_display", "type_1", "type_2", "category", "generation_label"] + STATS + ["base_stat_total"]
].rename(columns={"name_display": "Nama", "type_1": "Tipe 1", "type_2": "Tipe 2",
                  "category": "Kategori", "generation_label": "Generasi",
                  "base_stat_total": "Total"})
st.dataframe(top10, width="stretch", hide_index=True)

with st.expander("Lihat seluruh data hasil filter"):
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.download_button("Unduh data hasil filter (CSV)",
                       filtered.to_csv(index=False).encode("utf-8"),
                       file_name="pokemon_filtered.csv", mime="text/csv")



st.divider()
st.subheader("Unduh Dataset Bersih")
st.markdown(
    f"Dataset hasil pembersihan (**{df.shape[0]:,} baris, {df.shape[1]} kolom**): duplikat dihapus, "
    "teks dirapikan, nilai kosong diisi, dan kolom baru ditambahkan (`form_type`, `base_stat_total`, "
    "`category`, `generation_num`, `height_m`, `weight_kg`, dll). File ini berisi **seluruh data**, "
    "tidak terpengaruh filter."
)
st.download_button("Unduh pokemon_clean.csv",
                   df.to_csv(index=False).encode("utf-8"),
                   file_name="pokemon_clean.csv", mime="text/csv", type="primary")

st.caption("Sumber data: Kaggle - Pokemon Complete Stats | Dibuat dengan Streamlit")