import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="DeepSeek vs OpenAI", page_icon="⚖️", layout="centered")

st.markdown(
    """
    <style>
    .block-container { max-width: 880px; }
    h1, h2, h3 { text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Colores fijos por proveedor (orden categórico, nunca reasignado dinámicamente)
COLOR_DEEPSEEK = "#2a78d6"
COLOR_OPENAI = "#eb6834"

# Precios por millón de tokens (USD)
DEEPSEEK_INPUT_PRICE = 0.28
DEEPSEEK_OUTPUT_PRICE = 0.42
OPENAI_INPUT_PRICE = 0.15
OPENAI_OUTPUT_PRICE = 0.60

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


@st.cache_resource
def get_clients():
    try:
        openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"], timeout=60.0)
        deepseek_client = OpenAI(
            api_key=st.secrets["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
            timeout=60.0,
        )
        return openai_client, deepseek_client
    except KeyError as e:
        st.error(
            f"Falta configurar el secreto {e} en **Settings → Secrets** de Streamlit Cloud "
            "(o en `.streamlit/secrets.toml` en local)."
        )
        st.stop()


def call_model(client, model, prompt):
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=3000,
    )
    seconds = time.perf_counter() - start
    return response, seconds


def estimated_cost(response, input_price, output_price):
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return input_tokens, output_tokens, cost


def run_provider(nombre, client, model, prompt, input_price, output_price):
    try:
        response, seconds = call_model(client, model, prompt)
        input_tokens, output_tokens, cost = estimated_cost(response, input_price, output_price)
        return {
            "Proveedor": nombre,
            "Respuesta": response.choices[0].message.content,
            "Tiempo (s)": seconds,
            "Tokens Entrada": input_tokens,
            "Tokens Salida": output_tokens,
            "Costo (USD)": cost,
            "error": None,
        }
    except Exception as e:
        return {"Proveedor": nombre, "error": str(e)}


st.title("⚖️ Comparativa DeepSeek vs OpenAI")
st.markdown(
    "<p style='text-align:center; color:#52514e;'>"
    "Escribe un prompt y compara la respuesta, el tiempo, el costo y los tokens de ambos modelos."
    "</p>",
    unsafe_allow_html=True,
)

openai_client, deepseek_client = get_clients()

prompt = st.text_area(
    "Prompt",
    height=120,
    placeholder="Ej: Explica en 3 puntos las ventajas de la criptografía post-cuántica.",
)

run = st.button("Comparar modelos", type="primary", disabled=not prompt.strip(), use_container_width=True)

if run:
    with st.spinner("Consultando DeepSeek y OpenAI..."):
        deepseek_result = run_provider(
            "DeepSeek", deepseek_client, "deepseek-chat", prompt,
            DEEPSEEK_INPUT_PRICE, DEEPSEEK_OUTPUT_PRICE,
        )
        openai_result = run_provider(
            "OpenAI", openai_client, "gpt-4o-mini", prompt,
            OPENAI_INPUT_PRICE, OPENAI_OUTPUT_PRICE,
        )

    st.markdown("<h3>Respuestas</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    for col, result in ((col1, deepseek_result), (col2, openai_result)):
        with col, st.container(border=True):
            st.markdown(f"**{result['Proveedor']}**")
            if result["error"]:
                st.error(f"No se pudo obtener respuesta: {result['error']}")
            else:
                st.write(result["Respuesta"])

    results = [r for r in (deepseek_result, openai_result) if not r["error"]]

    if len(results) < 2:
        st.warning("No se pudo comparar métricas porque al menos un proveedor falló.")
    else:
        df = pd.DataFrame(results).drop(columns=["Respuesta", "error"])
        deepseek_row = df[df["Proveedor"] == "DeepSeek"].iloc[0]
        openai_row = df[df["Proveedor"] == "OpenAI"].iloc[0]

        st.markdown("<h3>Métricas</h3>", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tiempo DeepSeek", f"{deepseek_row['Tiempo (s)']:.2f}s")
        m2.metric("Tiempo OpenAI", f"{openai_row['Tiempo (s)']:.2f}s")
        m3.metric("Costo DeepSeek", f"${deepseek_row['Costo (USD)']:.6f}")
        m4.metric("Costo OpenAI", f"${openai_row['Costo (USD)']:.6f}")

        st.dataframe(df, hide_index=True, use_container_width=True)

        st.markdown("<h3>Tokens por proveedor</h3>", unsafe_allow_html=True)

        fig_tokens = go.Figure()
        fig_tokens.add_trace(
            go.Bar(
                name="Tokens entrada",
                x=df["Proveedor"],
                y=df["Tokens Entrada"],
                marker_color=COLOR_DEEPSEEK,
                text=df["Tokens Entrada"],
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig_tokens.add_trace(
            go.Bar(
                name="Tokens salida",
                x=df["Proveedor"],
                y=df["Tokens Salida"],
                marker_color=COLOR_OPENAI,
                text=df["Tokens Salida"],
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig_tokens.update_layout(
            barmode="group",
            bargap=0.35,
            plot_bgcolor="#fcfcfb",
            paper_bgcolor="#fcfcfb",
            font=dict(family=FONT_FAMILY, size=13, color="#0b0b0b"),
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
            margin=dict(t=60, b=20, l=10, r=10),
            yaxis=dict(title="Tokens", gridcolor="#e1e0d9"),
            xaxis=dict(title=None),
        )
        st.plotly_chart(fig_tokens, use_container_width=True)

        ratio_tiempo = openai_row["Tiempo (s)"] / deepseek_row["Tiempo (s)"]
        ratio_costo = (
            openai_row["Costo (USD)"] / deepseek_row["Costo (USD)"]
            if deepseek_row["Costo (USD)"] > 0
            else float("nan")
        )

        st.markdown("<h3>Análisis</h3>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <p style='text-align:center;'>
            DeepSeek fue <strong>{ratio_tiempo:.2f}x</strong> más rápido y costó
            <strong>{ratio_costo:.2f}x</strong> menos que OpenAI en esta consulta.
            </p>
            """,
            unsafe_allow_html=True,
        )
