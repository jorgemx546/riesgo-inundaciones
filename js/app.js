// Lógica del prototipo: navegación entre pantallas, estados de carga y error,
// resultado simulado, mapa del condado y gráfica del historial.
(() => {
  const $ = id => document.getElementById(id);
  const reducirMov = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const num = n => n.toLocaleString("es-MX");
  const NIVEL = {
    bajo: { nombre: "Bajo", texto: "La zona tiene pocas inundaciones y reclamaciones al seguro registradas en comparación con otros condados. Bajo no significa cero: también pueden ocurrir lluvias repentinas.",
      prot: "Tu zona tiene un riesgo estimado bajo. Aun así, vale la pena saber si tu seguro cubre inundaciones: muchas reclamaciones vienen de zonas que no se consideran de alto riesgo." },
    medio: { nombre: "Medio", texto: "Hay inundaciones registradas en la zona, sobre todo de río, aunque no tan frecuentes como en los condados de riesgo alto.",
      prot: "Tu zona tiene un riesgo estimado medio. Conviene confirmar si tu póliza actual cubre inundaciones y qué tanto cubre." },
    alto: { nombre: "Alto", texto: "La zona tiene un historial frecuente de inundaciones y de reclamaciones al seguro. Vale la pena revisar con cuidado tu cobertura.",
      prot: "Tu zona tiene un riesgo estimado alto. Revisa con cuidado tu cobertura contra inundaciones y considera el periodo de espera antes de la temporada de lluvias." },
  };

  // ------------------------------------------------------------ pantallas
  const pantallas = ["inicio", "estado", "resultado", "proteccion"];
  function mostrar(nombre) {
    pantallas.forEach(p => { $(p).hidden = p !== nombre; });
    window.scrollTo({ top: 0, behavior: reducirMov ? "auto" : "smooth" });
    if (nombre === "resultado" && mapa) setTimeout(() => mapa.invalidateSize(), 50);
  }
  document.querySelectorAll('a[href="#inicio"]').forEach(a => a.addEventListener("click", e => { e.preventDefault(); mostrar("inicio"); $("direccion").focus(); }));
  $("b-otra").addEventListener("click", () => { mostrar("inicio"); $("direccion").select(); });
  $("b-proteccion").addEventListener("click", e => { e.preventDefault(); mostrar("proteccion"); });
  $("b-volver-res").addEventListener("click", e => { e.preventDefault(); mostrar("resultado"); });

  // ------------------------------------------------------------ búsqueda
  function clasificar(texto) {
    const t = texto.trim();
    if (t.length < 3 || !/[aeiouáéíóú]/i.test(t)) return "no-encontrada";
    const hit = window.BUSQUEDAS.find(b => b.patron.test(t));
    return hit ? hit.resultado : "solo-ejemplos";
  }
  async function buscar(texto) {
    $("direccion").value = texto;
    const destino = clasificar(texto);
    await cargando();
    if (window.ZONAS[destino]) return mostrarResultado(window.ZONAS[destino]);
    mostrarError(destino, texto);
  }
  $("f-buscar").addEventListener("submit", e => { e.preventDefault(); buscar($("direccion").value); });
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-buscar]");
    if (b) buscar(b.dataset.buscar);
  });

  // ------------------------------------------------------------ estados
  const PASOS = ["Ubicando la dirección", "Identificando el condado", "Consultando el historial de la zona", "El modelo está estimando el riesgo"];
  function cargando() {
    mostrar("estado");
    $("estado").innerHTML = `<div class="estado-tarjeta" role="status"><p class="eyebrow">Analizando</p>
      <ol class="pasos-carga">${PASOS.map(p => `<li><span class="punto"></span>${p}</li>`).join("")}</ol></div>`;
    const items = [...$("estado").querySelectorAll("li")];
    const paso = reducirMov ? 60 : 420;
    return new Promise(listo => {
      items.forEach((li, i) => setTimeout(() => {
        items.forEach((x, k) => { x.classList.toggle("hecho", k < i); x.classList.toggle("activo", k === i); x.querySelector(".punto").textContent = k < i ? "✓" : ""; });
      }, i * paso));
      setTimeout(listo, items.length * paso);
    });
  }
  const ICO_ALERTA = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 20h20L12 3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4.5M12 17.5v.3" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
  const ERRORES = {
    "no-encontrada": t => ({ grave: false, titulo: "No encontramos esa dirección",
      texto: `No pudimos ubicar «${esc(t)}». Revisa que incluya la ciudad y el estado, por ejemplo: <i>1200 Main St, Houston, TX</i>.` }),
    "fuera": t => ({ grave: false, titulo: "Por ahora solo analizamos viviendas en Estados Unidos",
      texto: `«${esc(t)}» está fuera de la zona que cubre el sistema. Los datos históricos que usa el modelo (NOAA y el seguro nacional de inundación, NFIP) solo existen para Estados Unidos, así que no podemos estimar el riesgo aquí.` }),
    "sin-datos": () => ({ grave: true, titulo: "No podemos estimar el riesgo de esta zona con confianza",
      texto: "El Condado de Loving, Texas, tiene muy pocos registros de tormentas y casi ninguna póliza del seguro de inundación. Con tan poco historial, el modelo no da un nivel de riesgo: preferimos decirlo en lugar de adivinar. Puedes revisar el mapa oficial de inundación de FEMA para tu dirección." }),
    "solo-ejemplos": t => ({ grave: false, titulo: "Este prototipo solo tiene zonas de ejemplo",
      texto: `En esta versión no buscamos «${esc(t)}» porque el modelo todavía no está conectado. Prueba con una de las zonas de ejemplo para ver cómo se mostraría el resultado.` }),
    "sin-permiso": () => ({ grave: false, titulo: "No pudimos usar tu ubicación",
      texto: "El navegador no compartió tu ubicación (no diste permiso o no está disponible). Puedes escribir la dirección de tu vivienda." }),
  };
  function mostrarError(tipo, texto) {
    const e = ERRORES[tipo](texto);
    mostrar("estado");
    $("estado").innerHTML = `<div class="estado-tarjeta estado-error${e.grave ? " grave" : ""}" role="alert">
      <div class="titulo">${ICO_ALERTA}<h2>${e.titulo}</h2></div><p>${e.texto}</p>
      <div class="estado-acciones"><button class="boton boton-pri" type="button" data-volver>Escribir otra dirección</button>
      <button class="boton boton-sec" type="button" data-buscar="Houston, TX">Ver un ejemplo</button>
      ${tipo === "sin-datos" ? '<a class="boton boton-sec" href="https://msc.fema.gov/portal/home" target="_blank" rel="noopener">Mapa de FEMA</a>' : ""}</div></div>`;
    $("estado").querySelector("[data-volver]").addEventListener("click", () => { mostrar("inicio"); $("direccion").select(); });
  }
  function esc(s) { return s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  // ------------------------------------------------------------ resultado
  let zona = null, periodo = 10;
  function mostrarResultado(z) {
    zona = z;
    mostrar("resultado");
    $("t-zona").textContent = `${z.condado}, ${z.estado}`;
    $("zona-detalle").textContent = `Búsqueda: ${z.ciudad} · código FIPS ${z.geoid} · ${z.lat.toFixed(4)}°, ${z.lon.toFixed(4)}°`;
    const n = NIVEL[z.nivel];
    $("tarjeta-riesgo").className = "tarjeta riesgo " + z.nivel;
    $("nivel").className = "nivel " + z.nivel;
    $("nivel").textContent = n.nombre;
    $("nivel-texto").textContent = n.texto;
    $("probs").innerHTML = ["bajo", "medio", "alto"].map(k => {
      const p = Math.round(z.probabilidades[k] * 100);
      return `<div class="prob ${k}"><span>${NIVEL[k].nombre}</span><span class="barra-p"><i style="width:${p}%"></i></span><b>${p} %</b></div>`;
    }).join("");
    const maxPeso = Math.max(...z.factores.map(f => f.peso));
    $("factores").innerHTML = z.factores.map(f => `<li><span class="f-nombre">${f.nombre}</span>
      <span class="f-dato"><b>${f.valor}</b> · ${f.comparacion}</span>
      <span class="f-peso">peso ${Math.round(f.peso * 100)} %<span><i style="width:${f.peso / maxPeso * 100}%"></i></span></span></li>`).join("");
    // Los indicadores salen de las mismas series que la gráfica (últimos 10 años).
    const ult = arr => arr.slice(-10), suma = arr => arr.reduce((a, b) => a + b, 0);
    const recl10 = ult(z.reclamaciones), anios10 = ult(window.ANIOS);
    const peorAnio = anios10[recl10.indexOf(Math.max(...recl10))];
    $("kpis").innerHTML = [
      [num(suma(ult(z.eventos))), "eventos de inundación en 10 años"],
      [num(suma(recl10)), "reclamaciones al NFIP en 10 años"],
      ["US$ " + num(z.pagoPromedio), "pago promedio por reclamación"],
      [peorAnio, "año con más reclamaciones (10 años)"],
    ].map(([v, e]) => `<div class="kpi"><div class="v">${v}</div><div class="e">${e} <span class="simulado">Simulado</span></div></div>`).join("");
    $("recientes").innerHTML = z.recientes.map(r => `<tr><td>${r.fecha}</td><td>${r.tipo}</td><td>${r.danio}</td></tr>`).join("");
    $("prot-intro").textContent = n.prot;
    dibujarGrafica();
    dibujarMapa(z);
  }

  // ------------------------------------------------------------ gráfica
  let grafica = null;
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  function dibujarGrafica() {
    if (!zona || !window.Chart) return;
    const desde = window.ANIOS.length - periodo;
    const datos = {
      labels: window.ANIOS.slice(desde),
      datasets: [
        { type: "bar", label: "Eventos de inundación (NOAA)", data: zona.eventos.slice(desde), backgroundColor: css("--agua"), borderRadius: 4, yAxisID: "y", hidden: !$("c-eventos").checked, order: 2 },
        { type: "line", label: "Reclamaciones al NFIP", data: zona.reclamaciones.slice(desde), borderColor: css("--serie-2"), backgroundColor: css("--serie-2"), tension: .25, pointRadius: 3, yAxisID: "y2", hidden: !$("c-reclamaciones").checked, order: 1 },
      ],
    };
    const tinta = css("--tenue"), linea = css("--linea");
    const opciones = {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: tinta, font: { family: "Public Sans" } } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${num(c.parsed.y)}` } } },
      scales: {
        x: { ticks: { color: tinta }, grid: { display: false } },
        y: { position: "left", beginAtZero: true, title: { display: true, text: "Eventos", color: tinta }, ticks: { color: tinta, precision: 0 }, grid: { color: linea } },
        y2: { position: "right", beginAtZero: true, title: { display: true, text: "Reclamaciones", color: tinta }, ticks: { color: tinta, callback: v => num(v) }, grid: { display: false } },
      },
      animation: reducirMov ? false : { duration: 400 },
    };
    if (grafica) grafica.destroy();
    grafica = new Chart($("grafica"), { data: datos, options: opciones });
  }
  document.querySelectorAll("[data-periodo]").forEach(b => b.addEventListener("click", () => {
    periodo = +b.dataset.periodo;
    document.querySelectorAll("[data-periodo]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    dibujarGrafica();
  }));
  ["c-eventos", "c-reclamaciones"].forEach(id => $(id).addEventListener("change", dibujarGrafica));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujarGrafica);

  // ------------------------------------------------------------ mapa
  let mapa = null, capa = null, marcador = null;
  const contornos = {};
  async function contorno(geoid) {
    if (contornos[geoid]) return contornos[geoid];
    const url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query" +
      `?where=GEOID%3D%27${geoid}%27&outFields=NAME&outSR=4326&f=geojson`;
    const r = await fetch(url);
    if (!r.ok) throw new Error("TIGERweb " + r.status);
    return (contornos[geoid] = await r.json());
  }
  async function dibujarMapa(z) {
    if (!window.L) { $("mapa-nota").textContent = "No se pudo cargar el mapa."; return; }
    if (!mapa) {
      mapa = L.map("mapa", { scrollWheelZoom: false });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "&copy; colaboradores de OpenStreetMap" }).addTo(mapa);
    }
    setTimeout(() => mapa.invalidateSize(), 60);
    if (capa) { capa.remove(); capa = null; }
    if (marcador) marcador.remove();
    mapa.setView([z.lat, z.lon], 9);
    marcador = L.circleMarker([z.lat, z.lon], { radius: 7, color: "#ffffff", weight: 2, fillColor: css("--agua"), fillOpacity: 1 }).addTo(mapa).bindTooltip(z.ciudad);
    const color = css("--" + z.nivel);
    try {
      const geo = await contorno(z.geoid);
      if (zona !== z) return;
      capa = L.geoJSON(geo, { style: { color, weight: 2.5, fillColor: color, fillOpacity: .14 } }).addTo(mapa);
      mapa.fitBounds(capa.getBounds(), { padding: [18, 18] });
      $("mapa-nota").textContent = `Contorno oficial del ${z.condado} (Censo de EE. UU.). El resultado describe todo el condado, no solo tu casa.`;
    } catch (e) {
      $("mapa-nota").textContent = "No se pudo cargar el contorno del condado; se muestra el punto consultado. El resultado describe todo el condado.";
    }
  }

  // ------------------------------------------------------------ ubicación (con permiso)
  $("b-ubicacion").addEventListener("click", () => $("d-ubicacion").showModal());
  $("b-permitir").addEventListener("click", () => {
    $("d-ubicacion").close();
    if (!navigator.geolocation) return mostrarError("sin-permiso");
    cargando();
    navigator.geolocation.getCurrentPosition(pos => {
      const { latitude: la, longitude: lo } = pos.coords;
      const enEEUU = la > 24.4 && la < 49.5 && lo > -125 && lo < -66.9;
      if (!enEEUU) return mostrarError("fuera", `tu ubicación (${la.toFixed(2)}°, ${lo.toFixed(2)}°)`);
      // Prototipo: se muestra la zona de ejemplo más cercana.
      const cercana = Object.values(window.ZONAS).sort((a, b) => Math.hypot(a.lat - la, a.lon - lo) - Math.hypot(b.lat - la, b.lon - lo))[0];
      mostrarResultado(cercana);
    }, () => mostrarError("sin-permiso"), { timeout: 10000 });
  });

  // ------------------------------------------------------------ reportar un error
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
  // Ej.: index.html#resultado-alto · #error-fuera · #proteccion · ?tema=claro · ?notas
  const params = new URLSearchParams(location.search);
  if (params.get("tema") === "claro") document.documentElement.dataset.theme = "light";
  if (params.get("tema") === "oscuro") document.documentElement.dataset.theme = "dark";
  if (params.has("notas")) notas(true);
  const DIRECTOS = {
    "resultado-alto": "Houston, TX", "resultado-medio": "Davenport, IA", "resultado-bajo": "Phoenix, AZ",
    "error-sin-datos": "Loving, TX", "error-fuera": "Cancún, México", "error-no-encontrada": "zzzz", "error-ejemplos": "Seattle, WA",
  };
  async function irDirecto() {
    const h = location.hash.slice(1);
    if (DIRECTOS[h]) await buscar(DIRECTOS[h]);
    else if (h === "proteccion") { await buscar("Houston, TX"); mostrar("proteccion"); }
    else if (h === "cargando") cargando();
  }
  irDirecto();
})();
