import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="DeepSeek vs OpenAI", page_icon="⚖️", layout="wide")

# Colores fijos por proveedor (orden categórico, nunca reasignado dinámicamente)
COLOR_DEEPSEEK = "#2a78d6"
COLOR_OPENAI = "#eb6834"

# Precios por millón de tokens (USD)
DEEPSEEK_INPUT_PRICE = 0.28
DEEPSEEK_OUTPUT_PRICE = 0.42
OPENAI_INPUT_PRICE = 0.15
OPENAI_OUTPUT_PRICE = 0.60


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
st.write("Escribe un prompt y compara la respuesta, el tiempo y el costo estimado de ambos modelos.")

openai_client, deepseek_client = get_clients()

prompt = st.text_area(
    "Prompt",
    height=120,
    placeholder="Ej: Explica en 3 puntos las ventajas de la criptografía post-cuántica.",
)

if st.button("Comparar modelos", type="primary", disabled=not prompt.strip()):
    with st.spinner("Consultando DeepSeek y OpenAI..."):
        deepseek_result = run_provider(
            "DeepSeek", deepseek_client, "deepseek-chat", prompt,
            DEEPSEEK_INPUT_PRICE, DEEPSEEK_OUTPUT_PRICE,
        )
        openai_result = run_provider(
            "OpenAI", openai_client, "gpt-4o-mini", prompt,
            OPENAI_INPUT_PRICE, OPENAI_OUTPUT_PRICE,
        )

    col1, col2 = st.columns(2)
    for col, result, color in (
        (col1, deepseek_result, COLOR_DEEPSEEK),
        (col2, openai_result, COLOR_OPENAI),
    ):
        with col:
            st.markdown(f"### :{'blue' if color == COLOR_DEEPSEEK else 'orange'}[{result['Proveedor']}]")
            if result["error"]:
                st.error(f"No se pudo obtener respuesta: {result['error']}")
            else:
                st.write(result["Respuesta"])

    results = [r for r in (deepseek_result, openai_result) if not r["error"]]

    if len(results) < 2:
        st.warning("No se pudo comparar métricas porque al menos un proveedor falló.")
    else:
        df = pd.DataFrame(results).drop(columns=["Respuesta", "error"])

        st.markdown("---")
        st.subheader("📊 Métricas comparativas")

        m1, m2, m3, m4 = st.columns(4)
        deepseek_row = df[df["Proveedor"] == "DeepSeek"].iloc[0]
        openai_row = df[df["Proveedor"] == "OpenAI"].iloc[0]
        m1.metric("Tiempo DeepSeek", f"{deepseek_row['Tiempo (s)']:.2f}s")
        m2.metric("Tiempo OpenAI", f"{openai_row['Tiempo (s)']:.2f}s")
        m3.metric("Costo DeepSeek", f"${deepseek_row['Costo (USD)']:.6f}")
        m4.metric("Costo OpenAI", f"${openai_row['Costo (USD)']:.6f}")

        st.dataframe(df, hide_index=True, use_container_width=True)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            fig_tiempo = go.Figure(
                go.Bar(
                    x=df["Proveedor"],
                    y=df["Tiempo (s)"],
                    marker_color=[COLOR_DEEPSEEK, COLOR_OPENAI],
                    text=df["Tiempo (s)"].round(2),
                    textposition="outside",
                )
            )
            fig_tiempo.update_layout(
                title="Tiempo de respuesta (s)",
                yaxis_title="Segundos",
                showlegend=False,
                bargap=0.5,
                plot_bgcolor="#fcfcfb",
                paper_bgcolor="#fcfcfb",
                margin=dict(t=50, b=30),
            )
            st.plotly_chart(fig_tiempo, use_container_width=True)

        with chart_col2:
            fig_costo = go.Figure(
                go.Bar(
                    x=df["Proveedor"],
                    y=df["Costo (USD)"],
                    marker_color=[COLOR_DEEPSEEK, COLOR_OPENAI],
                    text=df["Costo (USD)"].map(lambda v: f"${v:.6f}"),
                    textposition="outside",
                )
            )
            fig_costo.update_layout(
                title="Costo estimado (USD)",
                yaxis_title="USD",
                showlegend=False,
                bargap=0.5,
                plot_bgcolor="#fcfcfb",
                paper_bgcolor="#fcfcfb",
                margin=dict(t=50, b=30),
            )
            st.plotly_chart(fig_costo, use_container_width=True)

        fig_tokens = go.Figure()
        fig_tokens.add_trace(
            go.Bar(name="Tokens entrada", x=df["Proveedor"], y=df["Tokens Entrada"], marker_color="#2a78d6")
        )
        fig_tokens.add_trace(
            go.Bar(name="Tokens salida", x=df["Proveedor"], y=df["Tokens Salida"], marker_color="#eb6834")
        )
        fig_tokens.update_layout(
            title="Tokens consumidos por proveedor",
            yaxis_title="Tokens",
            barmode="group",
            bargap=0.4,
            plot_bgcolor="#fcfcfb",
            paper_bgcolor="#fcfcfb",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=70, b=30),
        )
        st.plotly_chart(fig_tokens, use_container_width=True)

        ratio_tiempo = openai_row["Tiempo (s)"] / deepseek_row["Tiempo (s)"]
        ratio_costo = openai_row["Costo (USD)"] / deepseek_row["Costo (USD)"] if deepseek_row["Costo (USD)"] > 0 else float("nan")

        st.markdown("---")
        st.subheader("🔎 Análisis")
        st.write(f"- DeepSeek fue **{ratio_tiempo:.2f}x** más rápido que OpenAI en esta consulta.")
        st.write(f"- DeepSeek costó **{ratio_costo:.2f}x** menos que OpenAI en esta consulta.")
