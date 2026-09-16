import streamlit as st

st.title("Prueba FIA")
st.write("Esta es una prueba de la aplicación FIA utilizando Streamlit.")



frecuency = st.slider("Selecciona la frecuencia", 1, 10, 5)
x = [i for i in range(1, 11)]
y = [i * frecuency for i in x]
st.plotly_chart({
    "data": [
        {
            "x": x,
            "y": y,
            "type": "bar",
            "name": f"Frecuencia {frecuency}"
        }
    ],
    "layout": {
        "title": f"Gráfico de barras con frecuencia {frecuency}"
    }
})