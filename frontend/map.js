let map = null;
let originMarker = null;
let destMarker = null;
let userRoutePolyline = null;
let peerMarkers = { a: null, b: null };
let sessionRouteLayers = [];
// FSU Tallahassee campus (bus stops area) – all users land here to explore
const defaultCenter = [30.442, -84.291];
const defaultZoom = 15;
const userZoom = 15;

var startIcon = L.divIcon({
  className: "map-marker map-marker-start",
  html: "<span>Start</span>",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
var endIcon = L.divIcon({
  className: "map-marker map-marker-end",
  html: "<span>End</span>",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
var peerStartIcon = L.divIcon({
  className: "map-marker map-marker-peer-start",
  html: "<span>Peer start</span>",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
var peerEndIcon = L.divIcon({
  className: "map-marker map-marker-peer-end",
  html: "<span>Peer end</span>",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

function initMap() {
  if (map) return;
  var container = document.getElementById("map-container");
  if (!container) return;
  map = L.map("map-container").setView(defaultCenter, defaultZoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(map);
  map.on("click", (e) => {
    if (window.mapTweaksDisabled) return;
    if (typeof setDestination === "function") setDestination(e.latlng.lat, e.latlng.lng);
    if (typeof setDestMarker === "function") setDestMarker(e.latlng);
  });
  window.map = map;
}

function centerMapOnUser(lat, lng, zoom) {
  if (!map) return;
  map.setView([lat, lng], zoom != null ? zoom : userZoom);
}

function fitMapToShowBothParties() {
  if (!map) return;
  var bounds = [];
  ["a", "b"].forEach(function (side) {
    var m = peerMarkers[side];
    if (m && m.getLatLng) bounds.push(m.getLatLng());
  });
  if (bounds.length >= 2) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  } else if (bounds.length === 1) {
    map.setView(bounds[0], userZoom);
  }
}

function initMapWhenVisible() {
  if (map) {
    setTimeout(function () { if (map) map.invalidateSize(); }, 150);
    return;
  }
  initMap();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("main") && !document.getElementById("main").classList.contains("hidden")) {
      initMap();
    }
  });
} else {
  if (document.getElementById("main") && !document.getElementById("main").classList.contains("hidden")) {
    initMap();
  }
}

window.initMapWhenVisible = initMapWhenVisible;

function setOriginMarker(pt) {
  if (!map) return;
  if (originMarker) map.removeLayer(originMarker);
  originMarker = L.marker([pt.lat, pt.lng], { icon: startIcon }).addTo(map).bindPopup("Start");
  originMarker.on("popupclose", function () {
    if (typeof window.onClearOriginRequested === "function") window.onClearOriginRequested();
  });
  if (typeof window.updateUserRoute === "function") window.updateUserRoute();
}

function setDestMarker(latlng, label) {
  if (!map) return;
  if (destMarker) map.removeLayer(destMarker);
  destMarker = L.marker([latlng.lat, latlng.lng], { icon: endIcon }).addTo(map).bindPopup(label || "End");
  destMarker.on("popupclose", function () {
    if (typeof window.onClearDestinationRequested === "function") window.onClearDestinationRequested();
  });
  if (typeof window.updateUserRoute === "function") window.updateUserRoute();
}

function updateDestMarkerPopup(label) {
  if (destMarker && label) destMarker.setPopupContent(label);
}

function setUserRoute(origin, dest) {
  if (!map || !origin || !dest) return;
  if (userRoutePolyline) {
    map.removeLayer(userRoutePolyline);
    userRoutePolyline = null;
  }
  var pts = [[origin.lat, origin.lng], [dest.lat, dest.lng]];
  if (window._userRouteOutline && map) {
    map.removeLayer(window._userRouteOutline);
    window._userRouteOutline = null;
  }
  window._userRouteOutline = L.polyline(pts, { color: "#1a1a2e", weight: 12, opacity: 0.9, lineCap: "round", lineJoin: "round" }).addTo(map);
  userRoutePolyline = L.polyline(pts, {
    color: "#2563eb",
    weight: 8,
    opacity: 1,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(map);
  userRoutePolyline.bringToFront();
  userRoutePolyline.bindPopup("Your route");
}

function clearUserRoute() {
  if (userRoutePolyline && map) {
    map.removeLayer(userRoutePolyline);
    userRoutePolyline = null;
  }
  if (window._userRouteOutline && map) {
    map.removeLayer(window._userRouteOutline);
    window._userRouteOutline = null;
  }
}

function clearOriginMarker() {
  if (originMarker && map) {
    map.removeLayer(originMarker);
    originMarker = null;
  }
  clearUserRoute();
}

function clearDestMarker() {
  if (destMarker && map) {
    map.removeLayer(destMarker);
    destMarker = null;
  }
  clearUserRoute();
}

function clearSessionRoutes() {
  sessionRouteLayers.forEach(function (layer) {
    if (map && layer) map.removeLayer(layer);
  });
  sessionRouteLayers = [];
}

function showSessionRoutes(routeA, routeB, mySide) {
  clearSessionRoutes();
  if (!map) return;
  var myColor = "#2563eb";
  var peerColor = "#ea580c";
  var routeWeight = 10;
  var outlineWeight = 14;
  if (routeA) {
    var ptsA = [[routeA.origin.lat, routeA.origin.lng], [routeA.destination.lat, routeA.destination.lng]];
    var outlineA = L.polyline(ptsA, { color: "#1a1a2e", weight: outlineWeight, opacity: 0.9, lineCap: "round", lineJoin: "round" }).addTo(map);
    sessionRouteLayers.push(outlineA);
    var lineA = L.polyline(ptsA, { color: mySide === "a" ? myColor : peerColor, weight: routeWeight, opacity: 1, lineCap: "round", lineJoin: "round" }).addTo(map);
    lineA.bringToFront();
    lineA.bindPopup(mySide === "a" ? "Your route" : "Peer route");
    sessionRouteLayers.push(lineA);
    var startA = L.marker([routeA.origin.lat, routeA.origin.lng], { icon: mySide === "a" ? startIcon : peerStartIcon }).addTo(map).bindPopup(mySide === "a" ? "Start (you)" : "Peer start");
    var endA = L.marker([routeA.destination.lat, routeA.destination.lng], { icon: mySide === "a" ? endIcon : peerEndIcon }).addTo(map).bindPopup(mySide === "a" ? "End (you)" : "Peer end");
    sessionRouteLayers.push(startA, endA);
  }
  if (routeB) {
    var ptsB = [[routeB.origin.lat, routeB.origin.lng], [routeB.destination.lat, routeB.destination.lng]];
    var outlineB = L.polyline(ptsB, { color: "#1a1a2e", weight: outlineWeight, opacity: 0.9, lineCap: "round", lineJoin: "round" }).addTo(map);
    sessionRouteLayers.push(outlineB);
    var lineB = L.polyline(ptsB, { color: mySide === "b" ? myColor : peerColor, weight: routeWeight, opacity: 1, lineCap: "round", lineJoin: "round" }).addTo(map);
    lineB.bringToFront();
    lineB.bindPopup(mySide === "b" ? "Your route" : "Peer route");
    sessionRouteLayers.push(lineB);
    var startB = L.marker([routeB.origin.lat, routeB.origin.lng], { icon: mySide === "b" ? startIcon : peerStartIcon }).addTo(map).bindPopup(mySide === "b" ? "Start (you)" : "Peer start");
    var endB = L.marker([routeB.destination.lat, routeB.destination.lng], { icon: mySide === "b" ? endIcon : peerEndIcon }).addTo(map).bindPopup(mySide === "b" ? "End (you)" : "Peer end");
    sessionRouteLayers.push(startB, endB);
  }
  if (sessionRouteLayers.length) {
    var bounds = [];
    sessionRouteLayers.forEach(function (lyr) {
      if (lyr.getLatLngs) {
        var ll = lyr.getLatLngs();
        ll.forEach(function (p) { bounds.push(Array.isArray(p) ? L.latLng(p[0], p[1]) : L.latLng(p.lat, p.lng)); });
      } else if (lyr.getLatLng) bounds.push(lyr.getLatLng());
    });
    if (bounds.length >= 2) {
      try { map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 }); } catch (e) {}
    }
  }
}

window.setOriginMarker = setOriginMarker;
window.setDestMarker = setDestMarker;
window.updateDestMarkerPopup = updateDestMarkerPopup;
window.clearOriginMarker = clearOriginMarker;
window.setUserRoute = setUserRoute;
window.clearUserRoute = clearUserRoute;
window.clearDestMarker = clearDestMarker;
window.showSessionRoutes = showSessionRoutes;
window.clearSessionRoutes = clearSessionRoutes;
window.centerMapOnUser = centerMapOnUser;
window.fitMapToShowBothParties = fitMapToShowBothParties;

var stopMarkersLayer = null;
var busStopIcon = L.divIcon({
  className: "map-marker map-marker-bus-stop",
  html: "<span>🚌</span>",
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

var MIN_STOP_MARKER_DISTANCE_M = 120;

function distanceMeters(lat1, lng1, lat2, lng2) {
  var R = 6371000;
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLng = (lng2 - lng1) * Math.PI / 180;
  var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function spreadStopsForMap(stops) {
  if (!stops || stops.length === 0) return [];
  var out = [];
  var minDist = MIN_STOP_MARKER_DISTANCE_M;
  for (var i = 0; i < stops.length; i++) {
    var s = stops[i];
    var tooClose = false;
    for (var j = 0; j < out.length; j++) {
      if (distanceMeters(s.lat, s.lng, out[j].lat, out[j].lng) < minDist) {
        tooClose = true;
        break;
      }
    }
    if (!tooClose) out.push(s);
  }
  return out;
}

function showStopsOnMap(stops) {
  if (!map || !stops || !stops.length) return;
  clearStopsOnMap();
  var scattered = spreadStopsForMap(stops);
  stopMarkersLayer = L.layerGroup().addTo(map);
  var bounds = [];
  scattered.forEach(function (stop) {
    var m = L.marker([stop.lat, stop.lng], { icon: busStopIcon })
      .addTo(stopMarkersLayer)
      .bindPopup(
        "<strong>" + (stop.name || "Bus stop") + "</strong><br><button type=\"button\" class=\"btn-set-start\" data-stop-id=\"" + (stop.id || "") + "\">Set as start</button>",
        { className: "stop-popup" }
      );
    m._stopData = stop;
    m.on("click", function () {
      if (typeof window.setOriginFromStop === "function") window.setOriginFromStop(stop);
    });
    m.on("popupopen", function () {
      var markerRef = m;
      var stopRef = stop;
      setTimeout(function () {
        var popup = markerRef.getPopup();
        var el = popup && popup.getElement ? popup.getElement() : null;
        if (!el) return;
        var btn = el.querySelector(".btn-set-start");
        if (btn) {
          btn.onclick = function () {
            if (typeof window.setOriginFromStop === "function") window.setOriginFromStop(stopRef);
            markerRef.closePopup();
          };
        }
      }, 0);
    });
    bounds.push([stop.lat, stop.lng]);
  });
  if (bounds.length) {
    try {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    } catch (err) {}
  }
}

function clearStopsOnMap() {
  if (stopMarkersLayer && map) {
    map.removeLayer(stopMarkersLayer);
    stopMarkersLayer = null;
  }
}

window.showStopsOnMap = showStopsOnMap;
window.clearStopsOnMap = clearStopsOnMap;

var busModeLayers = [];
function showBusStopMode(stop, people) {
  clearBusStopMode();
  if (!map || !stop) return;
  var stopMarker = L.marker([stop.lat, stop.lng], {
    icon: L.divIcon({ className: "bus-stop-marker", html: "<span>Bus</span>", iconSize: [28, 28], iconAnchor: [14, 14] }),
  }).addTo(map).bindPopup(stop.name);
  busModeLayers.push(stopMarker);
  var bounds = [[stop.lat, stop.lng]];
  (people || []).forEach(function (p, i) {
    var color = i === 0 ? "#3b82f6" : i === 1 ? "#22c55e" : "#f59e0b";
    var line = L.polyline(
      [[stop.lat, stop.lng], [p.dest_lat, p.dest_lng]],
      { color: color, weight: 6, opacity: 0.85 }
    ).addTo(map).bindPopup(p.name + " (" + p.mode + ")");
    busModeLayers.push(line);
    bounds.push([p.dest_lat, p.dest_lng]);
  });
  if (bounds.length > 1) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
  else map.setView([stop.lat, stop.lng], 16);
}
function clearBusStopMode() {
  busModeLayers.forEach(function (lyr) {
    if (map && lyr) map.removeLayer(lyr);
  });
  busModeLayers = [];
}
window.showBusStopMode = showBusStopMode;
window.clearBusStopMode = clearBusStopMode;

let ws = null;
let locationPollTimer = null;

function startLocationStream(sessionId, token, mySide) {
  stopLocationStream();
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/sessions/${sessionId}?token=${encodeURIComponent(token)}`;
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    if (navigator.geolocation) {
      const send = () => {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude }));
            }
          },
          () => {}
        );
        send();
      };
      send();
      setInterval(send, 5000);
    }
  };
  ws.onclose = () => { stopLocationStream(); };

  var firstFit = true;
  locationPollTimer = setInterval(function () {
    fetch("/api/sessions/" + sessionId + "/locations", {
      headers: { Authorization: "Bearer " + getToken() },
    })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (locs) {
        if (!locs || !map) return;
        var boundsUpdated = false;
        ["a", "b"].forEach(function (side) {
          var d = locs[side];
          if (d && d.lat != null && d.lng != null) {
            if (peerMarkers[side]) map.removeLayer(peerMarkers[side]);
            var isMe = side === mySide;
            peerMarkers[side] = L.marker([d.lat, d.lng])
              .addTo(map)
              .bindPopup(isMe ? "You" : "Peer");
            boundsUpdated = true;
          }
        });
        if (boundsUpdated && firstFit) {
          firstFit = false;
          setTimeout(function () {
            if (window.fitMapToShowBothParties) fitMapToShowBothParties();
          }, 100);
        }
      })
      .catch(function () {});
  }, 3000);
}

function getToken() {
  return localStorage.getItem("token") || "";
}

function stopLocationStream() {
  if (ws) {
    ws.close();
    ws = null;
  }
  if (locationPollTimer) {
    clearInterval(locationPollTimer);
    locationPollTimer = null;
  }
  ["a", "b"].forEach((side) => {
    if (peerMarkers[side] && map) {
      map.removeLayer(peerMarkers[side]);
      peerMarkers[side] = null;
    }
  });
}

window.startLocationStream = startLocationStream;
window.stopLocationStream = stopLocationStream;
