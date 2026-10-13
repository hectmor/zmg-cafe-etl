"use strict";

const API_BASE = "http://localhost:8000";
const MAP_CENTER = [20.6736, -103.344];
const MAP_ZOOM = 12;

const statusElement = document.getElementById("status");
const countElement = document.getElementById("count");
const searchElement = document.getElementById("search");
const typeFilterElement = document.getElementById("type-filter");

const map = L.map("map").setView(MAP_CENTER, MAP_ZOOM);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · ' +
    "Fuente: Overpass API · ZMG Cafés ETL",
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
let allFeatures = [];

function setStatus(state, message) {
  statusElement.dataset.state = state;
  statusElement.textContent = message;
}

function matchesFilters(feature) {
  const properties = feature.properties || {};
  const query = searchElement.value.trim().toLowerCase();
  const objectType = typeFilterElement.value;
  const name = (properties.name || "").toLowerCase();
  if (objectType && properties.object_type !== objectType) {
    return false;
  }
  if (query && !name.includes(query)) {
    return false;
  }
  return true;
}

function popupHtml(properties) {
  const name = properties.name || "Sin nombre en la fuente";
  const tags = properties.tags || {};
  const tagLines = Object.keys(tags)
    .sort()
    .map((key) => `<li><code>${key}</code>: ${tags[key]}</li>`)
    .join("");
  return (
    `<strong>${name}</strong>` +
    `<p>${properties.category} · ${properties.object_type}/${properties.object_id}</p>` +
    `<p><code>${properties.source_id}</code></p>` +
    `<p>Método de geometría: ${properties.geometry_method}</p>` +
    (tagLines ? `<ul class="tags">${tagLines}</ul>` : "")
  );
}

function render() {
  markerLayer.clearLayers();
  const visible = allFeatures.filter(matchesFilters);
  for (const feature of visible) {
    const layer = L.geoJSON(feature, {
      pointToLayer: (geojson, latlng) =>
        L.circleMarker(latlng, {
          radius: 8,
          color: "#6f4e37",
          fillColor: "#c8a27a",
          fillOpacity: 0.85,
          weight: 1.5,
        }),
      onEachFeature: (geojson, marker) => marker.bindPopup(popupHtml(geojson.properties || {})),
    });
    markerLayer.addLayer(layer);
  }
  countElement.textContent = `${visible.length} de ${allFeatures.length} cafés visibles`;
}

async function loadCafes() {
  setStatus("loading", "Cargando cafés…");
  countElement.textContent = "";
  try {
    const response = await fetch(`${API_BASE}/geojson/cafes?limit=5000`);
    if (!response.ok) {
      throw new Error(`la API respondió ${response.status}`);
    }
    const collection = await response.json();
    allFeatures = collection.features || [];
    render();
    setStatus("ready", "Datos cargados desde la capa analítica.");
  } catch (error) {
    markerLayer.clearLayers();
    allFeatures = [];
    countElement.textContent = "";
    setStatus("error", `No se pudo cargar la API: ${error.message}. Revisa que esté en marcha en ${API_BASE}.`);
  }
}

searchElement.addEventListener("input", render);
typeFilterElement.addEventListener("change", render);
loadCafes();
