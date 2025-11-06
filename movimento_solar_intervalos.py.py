import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tempfile, os
from PIL import Image

st.set_page_config(page_title="Irradiância por Horário", layout="wide")
st.title("☀️ Irradiância Solar por Horário")

st.markdown("""
Selecione uma **região** para visualizar a irradiância por intervalo de horário.
O app usa o arquivo incluído `medicoes_unificadas_corrigido.csv`.
""")

# CSV bundled with the app (must be in same folder)
CSV_PATH = os.path.join(os.path.dirname(__file__), "medicoes_unificadas_corrigido.csv")

# Fixed intervals
intervalos = ["06:00-08:00","08:00-10:00","10:00-12:00","12:00-14:00","14:00-16:00","16:00-18:00"]

@st.cache_data
def load_dataframe(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df

# Load
try:
    df = load_dataframe(CSV_PATH)
except FileNotFoundError:
    st.error(f"Arquivo não encontrado: {CSV_PATH}")
    st.stop()
except Exception as e:
    st.error(f"Erro ao ler CSV: {e}")
    st.stop()

# get available regions
if "Regiao" in df.columns:
    available = sorted(df["Regiao"].dropna().astype(str).str.strip().unique())
else:
    available = []

region = st.selectbox("Escolha a região", available)

if region:
    subset = df[df["Regiao"].str.strip().str.lower() == region.strip().lower()]
    if subset.empty:
        st.error("Nenhum dado encontrado para a região selecionada.")
    else:
        st.info(f"Região: {region} — {len(subset)} leituras")

        # ensure numeric ADC
        subset = subset.copy()
        subset["ADC"] = pd.to_numeric(subset["ADC"], errors="coerce")
        subset = subset.dropna(subset=["ADC"])
        subset = subset.reset_index(drop=True)

        total = len(subset)
        n_intervals = len(intervalos)
        base = total // n_intervals if n_intervals>0 else total
        groups = []
        for i in range(n_intervals):
            start = i * base
            end = (i+1) * base if i < n_intervals-1 else total
            groups.append(subset.iloc[start:end])

        maximos = [int(g["ADC"].max()) if not g.empty else 0 for g in groups]

        # Static bubble plot
        fig, ax = plt.subplots(figsize=(10,4))
        ax.set_xlim(-0.5, n_intervals-0.5)
        ytop = max(1000, int(max(maximos)*1.2)) if max(maximos) > 0 else 1000
        ax.set_ylim(0, ytop)
        ax.set_xticks(range(n_intervals))
        ax.set_xticklabels(intervalos)
        ax.set_ylabel("Irradiância (W/m²)")
        ax.set_title(f"Irradiância Solar {region} - por Horário")
        ax.grid(True, linestyle='--', alpha=0.4)

        cmap = plt.get_cmap("Blues")
        sizes = [400 + (v/ytop)*800 for v in maximos]
        for i, val in enumerate(maximos):
            color_val = val/ytop if ytop>0 else 0
            ax.scatter(i, val, s=sizes[i], color=cmap(color_val), edgecolors='k', zorder=3)
            ax.text(i, val+ytop*0.02, f"{val} W/m²", ha='center', va='bottom', fontsize=10, fontweight='bold')

        st.pyplot(fig)

        # Animation: show circles appearing interval-by-interval
        fig2, ax2 = plt.subplots(figsize=(10,4))
        ax2.set_xlim(-0.5, n_intervals-0.5)
        ax2.set_ylim(0, ytop)
        ax2.set_xticks(range(n_intervals))
        ax2.set_xticklabels(intervalos)
        ax2.set_ylabel("Irradiância (W/m²)")
        ax2.set_title(f"Irradiância Solar {region} - Animação")
        ax2.grid(True, linestyle='--', alpha=0.4)

        scatters = []
        texts = []
        for i in range(n_intervals):
            sc = ax2.scatter(i, 0, s=1, color=cmap(0), edgecolors='k', zorder=3)
            scatters.append(sc)
            t = ax2.text(i, 0, "", ha='center', va='bottom', fontsize=10, fontweight='bold')
            texts.append(t)

        def animate(frame):
            for idx in range(frame+1):
                val = maximos[idx]
                color_val = val/ytop if ytop>0 else 0
                scatters[idx].set_offsets([idx, val])
                scatters[idx].set_sizes([400 + (val/ytop)*800])
                scatters[idx].set_color(cmap(color_val))
                texts[idx].set_position((idx, val+ytop*0.02))
                texts[idx].set_text(f"{val} W/m²")
            return scatters + texts

        ani = animation.FuncAnimation(fig2, animate, frames=n_intervals, interval=800, blit=True)

        # Save animation to temporary file (required for Streamlit)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp:
            gif_path = tmp.name
        ani.save(gif_path, writer="pillow", fps=1)

        with open(gif_path, "rb") as f:
            gif_bytes = f.read()

        st.image(gif_bytes, caption="🎞️ Animação por Intervalo", use_container_width=True)
        st.download_button("💾 Baixar GIF", data=gif_bytes, file_name=f"{region}_intervalos.gif", mime="image/gif")
        os.remove(gif_path)
