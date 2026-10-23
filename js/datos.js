// Datos SIMULADOS para el prototipo (Entrega 1).
// No vienen del modelo ni de NOAA/OpenFEMA todavía: sirven para mostrar cómo se verán los resultados.
// Lo único real son los nombres, los códigos FIPS y las coordenadas de los condados de ejemplo.

const ANIOS = Array.from({ length: 20 }, (_, i) => 2004 + i);   // 2004 a 2023

window.ZONAS = {
  "48201": {
    ciudad: "Houston, TX",
    condado: "Condado de Harris",
    estado: "Texas",
    geoid: "48201",
    lat: 29.7604, lon: -95.3698,
    nivel: "alto",
    probabilidades: { bajo: 0.06, medio: 0.21, alto: 0.73 },
    factores: [
      { nombre: "Reclamaciones al seguro de inundación (NFIP), últimos 5 años", valor: "3,700", comparacion: "muy por encima de la mediana nacional de condados", peso: 0.34 },
      { nombre: "Eventos de inundación registrados, últimos 10 años", valor: "74", comparacion: "entre el 5 % de condados con más eventos", peso: 0.27 },
      { nombre: "Daños a propiedad por tormentas, últimos 10 años", valor: "US$ 1,210 M", comparacion: "muy por encima de la mediana", peso: 0.21 },
      { nombre: "Eventos de lluvia intensa y tormentas tropicales", valor: "38", comparacion: "por encima de la mediana", peso: 0.11 },
    ],
    pagoPromedio: 48300,   // los demás indicadores se calculan de las series de abajo
    eventos:      [4, 6, 3, 7, 9, 3, 2, 5, 3, 4, 6, 9, 11, 14, 5, 8, 6, 4, 5, 6],
    reclamaciones:[310, 420, 180, 520, 2900, 260, 150, 240, 190, 330, 410, 1870, 2650, 21400, 640, 1120, 980, 520, 470, 610],
    recientes: [
      { fecha: "2023-09-08", tipo: "Inundación repentina (flash flood)", danio: "US$ 3.2 M" },
      { fecha: "2023-05-12", tipo: "Lluvia intensa", danio: "US$ 0.4 M" },
      { fecha: "2022-08-22", tipo: "Inundación", danio: "US$ 6.1 M" },
      { fecha: "2022-06-03", tipo: "Inundación repentina (flash flood)", danio: "US$ 1.8 M" },
    ],
  },
  "19163": {
    ciudad: "Davenport, IA",
    condado: "Condado de Scott",
    estado: "Iowa",
    geoid: "19163",
    lat: 41.5236, lon: -90.5776,
    nivel: "medio",
    probabilidades: { bajo: 0.24, medio: 0.58, alto: 0.18 },
    factores: [
      { nombre: "Eventos de inundación de río registrados, últimos 10 años", valor: "19", comparacion: "por encima de la mediana", peso: 0.31 },
      { nombre: "Reclamaciones al seguro de inundación (NFIP), últimos 5 años", valor: "116", comparacion: "cerca de la mediana", peso: 0.26 },
      { nombre: "Daños a propiedad por tormentas, últimos 10 años", valor: "US$ 38 M", comparacion: "ligeramente por encima de la mediana", peso: 0.19 },
      { nombre: "Eventos de lluvia intensa", valor: "9", comparacion: "cerca de la mediana", peso: 0.12 },
    ],
    pagoPromedio: 27100,   // los demás indicadores se calculan de las series de abajo
    eventos:      [2, 1, 3, 2, 5, 1, 2, 1, 0, 2, 3, 1, 2, 1, 2, 4, 1, 2, 1, 2],
    reclamaciones:[12, 8, 15, 10, 96, 9, 14, 7, 3, 21, 18, 9, 11, 8, 13, 74, 10, 12, 9, 11],
    recientes: [
      { fecha: "2023-04-29", tipo: "Inundación de río", danio: "US$ 1.1 M" },
      { fecha: "2022-07-14", tipo: "Lluvia intensa", danio: "US$ 0.2 M" },
      { fecha: "2021-06-02", tipo: "Inundación repentina (flash flood)", danio: "US$ 0.6 M" },
    ],
  },
  "04013": {
    ciudad: "Phoenix, AZ",
    condado: "Condado de Maricopa",
    estado: "Arizona",
    geoid: "04013",
    lat: 33.4484, lon: -112.0740,
    nivel: "bajo",
    probabilidades: { bajo: 0.64, medio: 0.27, alto: 0.09 },
    factores: [
      { nombre: "Reclamaciones al seguro de inundación (NFIP), últimos 5 años", valor: "34", comparacion: "por debajo de la mediana", peso: 0.33 },
      { nombre: "Eventos de inundación repentina, últimos 10 años", valor: "23", comparacion: "por encima de la mediana (monzón)", peso: 0.24 },
      { nombre: "Daños a propiedad por tormentas, últimos 10 años", valor: "US$ 15 M", comparacion: "por debajo de la mediana para su población", peso: 0.18 },
      { nombre: "Eventos de lluvia intensa", valor: "6", comparacion: "por debajo de la mediana", peso: 0.10 },
    ],
    pagoPromedio: 19400,   // los demás indicadores se calculan de las series de abajo
    eventos:      [1, 2, 1, 3, 1, 2, 1, 2, 3, 1, 4, 2, 3, 2, 1, 3, 2, 3, 2, 1],
    reclamaciones:[4, 6, 3, 8, 5, 7, 3, 6, 9, 4, 19, 5, 8, 6, 3, 9, 7, 8, 6, 4],
    recientes: [
      { fecha: "2023-08-19", tipo: "Inundación repentina (flash flood)", danio: "US$ 0.3 M" },
      { fecha: "2022-07-31", tipo: "Inundación repentina (flash flood)", danio: "US$ 0.9 M" },
      { fecha: "2021-07-23", tipo: "Lluvia intensa", danio: "US$ 0.1 M" },
    ],
  },
};
window.ANIOS = ANIOS;

// Búsquedas que el prototipo reconoce para mostrar cada estado del flujo.
window.BUSQUEDAS = [
  { patron: /houston|harris|77\d{3}/i, resultado: "48201" },
  { patron: /davenport|scott county|5280\d/i, resultado: "19163" },
  { patron: /phoenix|maricopa|850\d{2}/i, resultado: "04013" },
  { patron: /canc[uú]n|m[eé]xico|cdmx|guadalajara|toronto|canad/i, resultado: "fuera" },
  { patron: /loving/i, resultado: "sin-datos" },
];
