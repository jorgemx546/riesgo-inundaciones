// Lógica de la página: navegación entre pantallas, búsqueda por dirección o por
// estado y condado, llamadas a la API (src/api/app.py), resultado del modelo,
// mapa del condado, gráfica e historial por año.
(() => {
  const $ = id => document.getElementById(id);
  const reducirMov = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const num = n => Number(n).toLocaleString("es-MX");
  const dinero = n => "US$ " + Math.round(n).toLocaleString("es-MX");
  const dineroCorto = n => n >= 1e6 ? `US$ ${(n / 1e6).toLocaleString("es-MX", { maximumFractionDigits: 1 })} millones`
    : n >= 1e3 ? `US$ ${(n / 1e3).toLocaleString("es-MX", { maximumFractionDigits: 1 })} mil` : dinero(n);

  const NIVEL = {
    bajo: { nombre: "Bajo", texto: "El modelo estima que el próximo año el condado no tendrá reclamaciones al seguro de inundación. Bajo no significa cero: también pueden ocurrir lluvias repentinas.",
      prot: "Tu zona tiene un riesgo estimado bajo. Aun así, vale la pena saber si tu seguro cubre inundaciones: muchas reclamaciones vienen de zonas que no se consideran de alto riesgo." },
    medio: { nombre: "Medio", texto: "El modelo estima que el próximo año el condado tendrá entre 1 y 9 reclamaciones al seguro de inundación.",
      prot: "Tu zona tiene un riesgo estimado medio. Conviene confirmar si tu póliza actual cubre inundaciones y qué tanto cubre." },
    alto: { nombre: "Alto", texto: "El modelo estima que el próximo año el condado tendrá 10 o más reclamaciones al seguro de inundación. Vale la pena revisar con cuidado tu cobertura.",
      prot: "Tu zona tiene un riesgo estimado alto. Revisa con cuidado tu cobertura contra inundaciones y considera el periodo de espera antes de la temporada de lluvias." },
  };

  const ESTADOS = {
    AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut",
    DE: "Delaware", DC: "Distrito de Columbia", FL: "Florida", GA: "Georgia", HI: "Hawái", ID: "Idaho", IL: "Illinois",
    IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Luisiana", ME: "Maine", MD: "Maryland",
    MA: "Massachusetts", MI: "Míchigan", MN: "Minnesota", MS: "Misisipi", MO: "Misuri", MT: "Montana", NE: "Nebraska",
    NV: "Nevada", NH: "Nuevo Hampshire", NJ: "Nueva Jersey", NM: "Nuevo México", NY: "Nueva York", NC: "Carolina del Norte",
    ND: "Dakota del Norte", OH: "Ohio", OK: "Oklahoma", OR: "Oregón", PA: "Pensilvania", RI: "Rhode Island",
    SC: "Carolina del Sur", SD: "Dakota del Sur", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont",
    VA: "Virginia", WA: "Washington", WV: "Virginia Occidental", WI: "Wisconsin", WY: "Wyoming",
  };
  const nombreEstado = ab => ESTADOS[ab] || ab;

  // Variables del modelo, en palabras simples. «formato» convierte el valor que manda la API.
  const VARIABLES = {
    claims_1y: { nombre: "Reclamaciones al NFIP en el último año", formato: v => num(v) },
    claims_5y: { nombre: "Reclamaciones al NFIP en 5 años", formato: v => num(v) },
    claims_10y: { nombre: "Reclamaciones al NFIP en 10 años", formato: v => num(v) },
    paid_loss_5y_log: { nombre: "Monto pagado por el NFIP en 5 años", formato: v => dinero(Math.expm1(v)) },
    severe_claims_5y: { nombre: "Reclamaciones graves al NFIP en 5 años", formato: v => num(v) },
    flood_events_1y: { nombre: "Eventos de inundación en el último año (NOAA)", formato: v => num(v) },
    flood_events_5y: { nombre: "Eventos de inundación en 5 años (NOAA)", formato: v => num(v) },
    flood_events_10y: { nombre: "Eventos de inundación en 10 años (NOAA)", formato: v => num(v) },
    storm_events_1y: { nombre: "Tormentas en el último año (NOAA)", formato: v => num(v) },
    storm_damage_10y_log: { nombre: "Daños por tormentas en 10 años (NOAA)", formato: v => dinero(Math.expm1(v)) },
    storm_deaths_10y: { nombre: "Muertes por tormentas en 10 años (NOAA)", formato: v => num(v) },
    fema_decl_5y: { nombre: "Declaratorias de desastre de FEMA en 5 años", formato: v => num(v) },
    state_fips: { nombre: "Estado", formato: (v, hist) => nombreEstado(hist.estado) || v },
  };

  // ------------------------------------------------------------ pantallas
  const pantallas = ["inicio", "estado", "resultado", "proteccion"];
  function mostrar(nombre) {
    pantallas.forEach(p => { $(p).hidden = p !== nombre; });
    window.scrollTo({ top: 0, behavior: reducirMov ? "auto" : "smooth" });
    if (nombre === "resultado" && mapa) setTimeout(() => mapa.invalidateSize(), 50);
  }
  function volverAlInicio() { mostrar("inicio"); $("direccion").select(); }
  document.querySelectorAll('a[href="#inicio"]').forEach(a => a.addEventListener("click", e => { e.preventDefault(); volverAlInicio(); }));
  $("b-otra").addEventListener("click", volverAlInicio);
  $("b-proteccion").addEventListener("click", e => { e.preventDefault(); mostrar("proteccion"); });
  $("b-volver-res").addEventListener("click", e => { e.preventDefault(); mostrar("resultado"); });

  // ------------------------------------------------------------ llamadas a la API
  async function pedir(url, opciones) {
    try {
      const r = await fetch(url, opciones);
      const datos = await r.json().catch(() => ({}));
      if (!r.ok || datos.error) return { error: datos.error || "servicio_no_disponible", mensaje: datos.mensaje };
      return datos;
    } catch (e) {
      return { error: "servicio_no_disponible" };
    }
  }

  // Mientras hay una consulta en curso, los botones que analizan se desactivan (RF-02).
  let ocupado = false;
  function bloquear(si) {
    ocupado = si;
    document.querySelectorAll("#f-buscar button, #b-analizar-condado, [data-fips], [data-buscar]").forEach(b => { b.disabled = si; });
    if (!si) actualizarBotonCondado();
  }

  // ------------------------------------------------------------ búsqueda por dirección
  async function buscar(texto) {
    if (ocupado) return;
    texto = texto.trim();
    $("direccion").value = texto;
    if (texto.length < 5) return mostrarError("entrada_invalida", texto);
    bloquear(true);
    cargando(0);
    const lugar = await pedir("/api/direccion?q=" + encodeURIComponent(texto));
    if (lugar.error) { bloquear(false); return mostrarError(lugar.error, texto); }
    await analizar(lugar.county_fips, { consulta: texto, direccion: lugar.direccion_encontrada, coordenadas: lugar.coordenadas });
  }
  $("f-buscar").addEventListener("submit", e => { e.preventDefault(); buscar($("direccion").value); });

  // ------------------------------------------------------------ análisis de un condado
  async function analizarFips(fips) {
    if (ocupado) return;
    bloquear(true);
    await analizar(fips, {});
  }
  async function analizar(fips, info) {
    cargando(2);
    const historial = pedir(`/api/historial/${encodeURIComponent(fips)}?anios=20`);
    setTimeout(() => { if (ocupado) cargando(3); }, reducirMov ? 0 : 250);
    const [pred, hist] = await Promise.all([
      pedir("/api/predecir", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ county_fips: fips }) }),
      historial,
    ]);
    bloquear(false);
    if (pred.error) return mostrarError(pred.error, info.consulta || fips, fips);
    if (hist.error) return mostrarError(hist.error, info.consulta || fips, fips);
    mostrarResultado({ fips, pred, hist, ...info });
  }

  // Ejemplos de prueba (RF-05): llenan el selector con el condado y lo analizan.
  document.addEventListener("click", e => {
    const ej = e.target.closest("[data-fips]");
    if (ej) { elegirEnSelector(ej.dataset.fips); return analizarFips(ej.dataset.fips); }
    const b = e.target.closest("[data-buscar]");
    if (b) buscar(b.dataset.buscar);
  });

  // ------------------------------------------------------------ selector de estado y condado
  let condados = [];
  async function cargarCondados() {
    const lista = await pedir("/api/condados");
    if (lista.error || !Array.isArray(lista) || !lista.length) {
      $("sel-estado").innerHTML = '<option value="">No disponible</option>';
      return;
    }
    condados = lista;
    const estados = [...new Set(lista.map(c => c.estado))].sort((a, b) => nombreEstado(a).localeCompare(nombreEstado(b), "es"));
    $("sel-estado").innerHTML = '<option value="">Elige un estado</option>' +
      estados.map(ab => `<option value="${esc(ab)}">${esc(nombreEstado(ab))}</option>`).join("");
    $("sel-estado").disabled = false;
  }
  function llenarCondados(estado) {
    const sel = $("sel-condado");
    if (!estado) {
      sel.innerHTML = '<option value="">Primero elige un estado</option>';
      sel.disabled = true;
    } else {
      const delEstado = condados.filter(c => c.estado === estado).sort((a, b) => a.condado.localeCompare(b.condado, "es"));
      sel.innerHTML = '<option value="">Elige un condado</option>' +
        delEstado.map(c => `<option value="${esc(c.county_fips)}">${esc(c.condado)}</option>`).join("");
      sel.disabled = false;
    }
    actualizarBotonCondado();
  }
  function actualizarBotonCondado() { $("b-analizar-condado").disabled = ocupado || !$("sel-condado").value; }
  function elegirEnSelector(fips) {
    const c = condados.find(x => x.county_fips === fips);
    if (!c) return;
    $("sel-estado").value = c.estado;
    llenarCondados(c.estado);
    $("sel-condado").value = fips;
    actualizarBotonCondado();
  }
  $("sel-estado").addEventListener("change", e => llenarCondados(e.target.value));
  $("sel-condado").addEventListener("change", actualizarBotonCondado);
  $("f-condado").addEventListener("submit", e => { e.preventDefault(); if ($("sel-condado").value) analizarFips($("sel-condado").value); });

  // ------------------------------------------------------------ carga
  const PASOS = ["Ubicando la dirección", "Identificando el condado", "Consultando el historial de la zona", "El modelo está estimando el riesgo"];
  function cargando(paso) {
    if ($("estado").hidden || !$("estado").querySelector(".pasos-carga")) {
      mostrar("estado");
      $("estado").innerHTML = `<div class="estado-tarjeta" role="status"><p class="eyebrow">Analizando</p>
        <ol class="pasos-carga">${PASOS.map(p => `<li><span class="punto"></span>${p}</li>`).join("")}</ol></div>`;
    }
    $("estado").querySelectorAll("li").forEach((li, k) => {
      li.classList.toggle("hecho", k < paso);
      li.classList.toggle("activo", k === paso);
      li.querySelector(".punto").textContent = k < paso ? "✓" : "";
    });
  }

  // ------------------------------------------------------------ casos sin estimación (RF-09)
  const ICO_ALERTA = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 20h20L12 3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4.5M12 17.5v.3" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
  const ERRORES = {
    entrada_invalida: t => ({ titulo: t ? "Esa dirección está incompleta" : "Escribe una dirección",
      texto: "Escribe la calle, la ciudad y el estado, por ejemplo: <i>1001 Preston St, Houston, TX</i>. También puedes elegir tu estado y condado en la lista." }),
    direccion_no_encontrada: t => ({ titulo: "No encontramos esa dirección en Estados Unidos",
      texto: `No pudimos ubicar «${esc(t)}». Revisa que tenga calle, ciudad y estado. Si la vivienda está fuera de EE. UU., no podemos analizarla: los datos que usa el modelo (NOAA, el seguro nacional de inundación NFIP y FEMA) solo existen para Estados Unidos.` }),
    condado_sin_datos: (t, fips) => ({ grave: true, fema: true, titulo: "No podemos estimar el riesgo de esta zona",
      texto: (fips || "").startsWith("09")
        ? `«${esc(t)}» cae en una región de planeación de Connecticut (código ${esc(fips)}). En 2022 el Censo cambió los condados de Connecticut por regiones, y los datos del modelo usan los condados anteriores. Elige tu condado de Connecticut en la lista de estado y condado, o revisa el mapa oficial de FEMA.`
        : `No hay datos suficientes de este condado para estimar el riesgo. Preferimos decirlo en lugar de adivinar. Puedes revisar el mapa oficial de inundación de FEMA para tu dirección.` }),
    servicio_no_disponible: () => ({ titulo: "El servicio no respondió",
      texto: "No pudimos consultar el servidor o el servicio de direcciones del Censo. Intenta de nuevo en un momento, o elige tu estado y condado en la lista: así no hace falta buscar la dirección." }),
    pendiente: () => ({ titulo: "Esta parte del sistema no está lista", texto: "El servidor todavía no tiene el historial por condado." }),
  };
  function mostrarError(tipo, texto = "", fips = "") {
    const e = (ERRORES[tipo] || ERRORES.servicio_no_disponible)(texto, fips);
    mostrar("estado");
    $("estado").innerHTML = `<div class="estado-tarjeta estado-error${e.grave ? " grave" : ""}" role="alert">
      <div class="titulo">${ICO_ALERTA}<h2>${e.titulo}</h2></div><p>${e.texto}</p>
      <div class="estado-acciones"><button class="boton boton-pri" type="button" data-volver>Escribir otra dirección</button>
      <button class="boton boton-sec" type="button" data-fips="48201">Ver un ejemplo</button>
      ${e.fema ? '<a class="boton boton-sec" href="https://msc.fema.gov/portal/home" target="_blank" rel="noopener">Mapa de FEMA</a>' : ""}</div></div>`;
    $("estado").querySelector("[data-volver]").addEventListener("click", volverAlInicio);
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  // ------------------------------------------------------------ resultado
  let zona = null, periodo = 10;
  function mostrarResultado(z) {
    zona = z;
    const { pred, hist } = z;
    mostrar("resultado");
    const nombreZona = hist.condado ? `${hist.condado}, ${nombreEstado(hist.estado)}` : `Condado ${z.fips}, ${nombreEstado(hist.estado)}`;
    $("t-zona").textContent = nombreZona;
    $("zona-detalle").textContent = [
      z.direccion ? `Dirección encontrada: ${z.direccion}` : "Elegido en la lista de condados",
      `código FIPS ${z.fips}`,
    ].join(" · ");

    // Nivel y probabilidades (RF-03)
    const n = NIVEL[pred.prediccion];
    $("tarjeta-riesgo").className = "tarjeta riesgo " + pred.prediccion;
    $("nivel").className = "nivel " + pred.prediccion;
    $("nivel").textContent = n.nombre;
    $("nivel-anio").textContent = `Para ${pred.anio_pronostico} · ${Math.round(pred.confianza_o_score * 100)} % de probabilidad`;
    $("nivel-texto").textContent = n.texto;
    $("probs").innerHTML = ["bajo", "medio", "alto"].map(k => {
      const p = Math.round(pred.probabilidades[k] * 100);
      return `<div class="prob ${k}"><span>${NIVEL[k].nombre}</span><span class="barra-p"><i style="width:${p}%"></i></span><b>${p} %</b></div>`;
    }).join("");

    // Factores que más pesaron (RF-07)
    const maxPeso = Math.max(...pred.factores.map(f => f.importancia));
    $("factores").innerHTML = pred.factores.map(f => {
      const v = VARIABLES[f.variable] || { nombre: f.variable, formato: x => x };
      const valor = f.variable === "paid_loss_5y_log" ? dinero(hist.kpis.monto_pagado_5y_usd) : v.formato(f.valor, hist);
      return `<li><span class="f-nombre">${esc(v.nombre)}</span>
        <span class="f-dato">En este condado: <b>${esc(valor)}</b></span>
        <span class="f-peso">peso ${Math.round(f.importancia * 100)} %<span><i style="width:${f.importancia / maxPeso * 100}%"></i></span></span></li>`;
    }).join("");

    // Indicadores del condado (RF-03)
    const k = hist.kpis;
    $("kpis").innerHTML = [
      [num(k.reclamaciones_5y), "reclamaciones al NFIP en 5 años"],
      [dineroCorto(k.monto_pagado_5y_usd), "pagados por el NFIP en 5 años"],
      [num(k.eventos_inundacion_10y), "eventos de inundación en 10 años (NOAA)"],
      [num(k.declaratorias_5y), "declaratorias de desastre de FEMA en 5 años"],
    ].map(([v, e]) => `<div class="kpi"><div class="v${String(v).length > 10 ? " largo" : ""}">${v}</div><div class="e">${e}</div></div>`).join("");

    // Registro de la inferencia (sección de diagnóstico)
    $("registro").innerHTML = [
      ["Tiempo de inferencia", `${pred.tiempo_ms} ms`],
      ["Año base de los datos", `${pred.anio_pronostico - 1} → pronóstico ${pred.anio_pronostico}`],
      ["Modelo", infoModelo ? infoModelo.modelo : "Random Forest"],
      ["Versiones", infoModelo ? `Python ${infoModelo.versiones.python} · scikit-learn ${infoModelo.versiones["scikit-learn"]}` : "—"],
    ].map(([t, d]) => `<div><dt>${t}</dt><dd>${esc(d)}</dd></div>`).join("");

    $("prot-intro").textContent = n.prot;
    dibujarHistorial();
    dibujarMapa(z);
  }

  // ------------------------------------------------------------ diagnóstico: matriz de confusión (Gráfica 4)
  // Fija: sale de results/metricas.json (conjunto de prueba, años base 2020 a 2024).
  const MATRIZ = [[7826, 3041, 95], [1091, 2618, 438], [78, 578, 590]];
  function dibujarMatriz() {
    const niveles = ["bajo", "medio", "alto"];
    $("matriz").innerHTML = `<thead><tr><th>Real \\ Modelo</th>${niveles.map(k => `<th>${NIVEL[k].nombre}</th>`).join("")}</tr></thead><tbody>` +
      MATRIZ.map((fila, i) => {
        const total = fila.reduce((a, b) => a + b, 0);
        return `<tr><th>${NIVEL[niveles[i]].nombre}</th>${fila.map(v => {
          const p = Math.round(v / total * 100);
          return `<td style="--p:${Math.round(p * .6)}%">${num(v)}<small>${p} %</small></td>`;
        }).join("")}</tr>`;
      }).join("") + "</tbody>";
  }
  let infoModelo = null;
  pedir("/api/salud").then(s => { if (!s.error) infoModelo = s; });
  dibujarMatriz();

  // ------------------------------------------------------------ historial: gráfica y tabla (RF-04)
  let grafica = null;
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const SERIES = [
    { id: "c-eventos", clave: "eventos_inundacion", titulo: "Eventos de inundación (NOAA)" },
    { id: "c-reclamaciones", clave: "reclamaciones", titulo: "Reclamaciones al NFIP" },
    { id: "c-declaratorias", clave: "declaratorias", titulo: "Declaratorias de FEMA" },
  ];
  function dibujarHistorial() {
    if (!zona) return;
    const h = zona.hist;
    const desde = Math.max(0, h.anios.length - periodo);
    const anios = h.anios.slice(desde);
    const serie = clave => h[clave].slice(desde);
    const ver = id => $(id).checked;

    // Tabla: del año más reciente al más antiguo; las columnas siguen a las casillas.
    $("historial-cab").innerHTML = "<th>Año</th>" + SERIES.filter(s => ver(s.id)).map(s => `<th>${s.titulo}</th>`).join("");
    $("historial-filas").innerHTML = anios.map((a, i) => `<tr><td>${a}</td>${SERIES.filter(s => ver(s.id)).map(s => `<td>${num(serie(s.clave)[i])}</td>`).join("")}</tr>`).reverse().join("");

    if (!window.Chart) return;
    const tinta = css("--tenue"), linea = css("--linea");
    const datos = {
      labels: anios,
      datasets: [
        { type: "bar", label: SERIES[0].titulo, data: serie("eventos_inundacion"), backgroundColor: css("--agua"), borderRadius: 4, yAxisID: "y", hidden: !ver("c-eventos"), order: 3 },
        { type: "bar", label: SERIES[2].titulo, data: serie("declaratorias"), backgroundColor: css("--medio"), borderRadius: 4, yAxisID: "y", hidden: !ver("c-declaratorias"), order: 2 },
        { type: "line", label: SERIES[1].titulo, data: serie("reclamaciones"), borderColor: css("--serie-2"), backgroundColor: css("--serie-2"), tension: .25, pointRadius: 3, yAxisID: "y2", hidden: !ver("c-reclamaciones"), order: 1 },
      ],
    };
    const opciones = {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: tinta, font: { family: "Public Sans" } }, onClick: () => {} }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${num(c.parsed.y)}` } } },
      scales: {
        x: { ticks: { color: tinta }, grid: { display: false } },
        y: { position: "left", beginAtZero: true, title: { display: true, text: "Eventos y declaratorias", color: tinta }, ticks: { color: tinta, precision: 0 }, grid: { color: linea } },
        y2: { position: "right", beginAtZero: true, display: ver("c-reclamaciones"), title: { display: true, text: "Reclamaciones", color: tinta }, ticks: { color: tinta, precision: 0, callback: v => num(v) }, grid: { display: false } },
      },
      animation: reducirMov ? false : { duration: 400 },
    };
    if (grafica) grafica.destroy();
    grafica = new Chart($("grafica"), { data: datos, options: opciones });
  }
  document.querySelectorAll("[data-periodo]").forEach(b => b.addEventListener("click", () => {
    periodo = +b.dataset.periodo;
    document.querySelectorAll("[data-periodo]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    dibujarHistorial();
  }));
  SERIES.forEach(s => $(s.id).addEventListener("change", dibujarHistorial));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujarHistorial);

  // ------------------------------------------------------------ mapa (RF-06)
  let mapa = null, capa = null, marcador = null;
  const contornos = {};
  // Capa actual de condados y, de respaldo, la de 2021: los condados de Connecticut
  // que el Censo cambió por regiones en 2022 solo existen en la segunda.
  const CAPAS_CONDADOS = [
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query",
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2021/MapServer/78/query",
  ];
  async function contorno(geoid) {
    if (contornos[geoid]) return contornos[geoid];
    for (const capa of CAPAS_CONDADOS) {
      const r = await fetch(`${capa}?where=GEOID%3D%27${geoid}%27&outFields=NAME&outSR=4326&f=geojson`);
      if (!r.ok) continue;
      const geo = await r.json();
      if (geo.features && geo.features.length) return (contornos[geoid] = geo);
    }
    throw new Error("sin contorno");
  }
  async function dibujarMapa(z) {
    if (!window.L) { $("mapa-nota").textContent = "No se pudo cargar el mapa."; return; }
    if (!mapa) {
      mapa = L.map("mapa", { scrollWheelZoom: false });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "&copy; colaboradores de OpenStreetMap" }).addTo(mapa);
    }
    setTimeout(() => mapa.invalidateSize(), 60);
    if (capa) { capa.remove(); capa = null; }
    if (marcador) { marcador.remove(); marcador = null; }
    const c = z.coordenadas;
    if (c) {
      mapa.setView([c.lat, c.lon], 9);
      marcador = L.circleMarker([c.lat, c.lon], { radius: 7, color: "#ffffff", weight: 2, fillColor: css("--agua"), fillOpacity: 1 }).addTo(mapa).bindTooltip(z.direccion || z.consulta);
    } else {
      mapa.setView([39.5, -98.35], 4);
    }
    const color = css("--" + z.pred.prediccion);
    const nombre = z.hist.condado || "condado";
    $("mapa-nota").textContent = "Cargando el contorno del condado…";
    try {
      const geo = await contorno(z.fips);
      if (zona !== z) return;
      capa = L.geoJSON(geo, { style: { color, weight: 2.5, fillColor: color, fillOpacity: .14 } }).addTo(mapa).bindTooltip(nombre);
      mapa.fitBounds(capa.getBounds(), { padding: [18, 18] });
      $("mapa-nota").textContent = `Contorno oficial de ${nombre} (Censo de EE. UU.). El resultado describe todo el condado, no solo tu casa.`;
    } catch (e) {
      if (zona !== z) return;
      $("mapa-nota").textContent = c
        ? "No se pudo cargar el contorno del condado; se muestra el punto consultado. El resultado describe todo el condado."
        : "No se pudo cargar el contorno del condado. El resultado describe todo el condado.";
    }
  }

  // ------------------------------------------------------------ reportar un error (RF-08)
  const abrirReporte = () => { $("rep-ok").hidden = true; $("b-enviar-rep").disabled = false; $("d-reporte").showModal(); };
  $("b-reportar").addEventListener("click", abrirReporte);
  document.querySelectorAll("[data-abrir-reporte]").forEach(b => b.addEventListener("click", abrirReporte));
  $("f-reporte").addEventListener("submit", e => { e.preventDefault(); $("rep-ok").hidden = false; $("b-enviar-rep").disabled = true; });
  document.querySelectorAll("dialog [data-cerrar]").forEach(b => b.addEventListener("click", () => b.closest("dialog").close()));

  // ------------------------------------------------------------ notas de diseño
  document.querySelectorAll("[data-nota]").forEach(el => {
    const nota = document.createElement("div");
    nota.className = "nota-diseno";
    nota.innerHTML = `<b>${el.dataset.rf || "Navegación"}</b><span>${el.dataset.nota}</span>`;
    // Dentro del elemento, salvo en controles (botón, enlace, formulario), donde va justo antes.
    if (["BUTTON", "A", "FORM", "INPUT"].includes(el.tagName)) el.insertAdjacentElement("beforebegin", nota);
    else el.insertAdjacentElement("afterbegin", nota);
  });
  function notas(activar) {
    document.body.classList.toggle("con-notas", activar);
    $("b-notas").setAttribute("aria-pressed", String(activar));
    $("panel-notas").hidden = !activar;
    try { localStorage.setItem("cauce-notas", activar ? "1" : "0"); } catch (e) {}
  }
  $("b-notas").addEventListener("click", () => notas(!document.body.classList.contains("con-notas")));
  $("b-cerrar-notas").addEventListener("click", () => notas(false));
  try { if (localStorage.getItem("cauce-notas") === "1") notas(true); } catch (e) {}

  // ------------------------------------------------------------ enlaces directos a cada estado
  // Ej.: /#resultado-alto · #error-fuera · #proteccion · ?tema=claro · ?notas
  const params = new URLSearchParams(location.search);
  if (params.get("tema") === "claro") document.documentElement.dataset.theme = "light";
  if (params.get("tema") === "oscuro") document.documentElement.dataset.theme = "dark";
  if (params.has("notas")) notas(true);
  const DIRECTOS_FIPS = { "resultado-alto": "48201", "resultado-medio": "32003", "resultado-bajo": "48371" };
  const DIRECTOS_TEXTO = { "error-sin-datos": "550 Main St, Hartford, CT 06103", "error-fuera": "Av. Tulum 100, Cancún, México", "error-no-encontrada": "zzzzzz" };
  async function irDirecto() {
    const h = location.hash.slice(1);
    if (DIRECTOS_FIPS[h]) { elegirEnSelector(DIRECTOS_FIPS[h]); await analizarFips(DIRECTOS_FIPS[h]); }
    else if (DIRECTOS_TEXTO[h]) await buscar(DIRECTOS_TEXTO[h]);
    else if (h === "proteccion") { await analizarFips("48201"); mostrar("proteccion"); }
    else if (h === "cargando") cargando(1);
  }

  cargarCondados().then(irDirecto);
})();
