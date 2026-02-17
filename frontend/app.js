const API = "/api";
let token = localStorage.getItem("token");
let origin = null;
let destination = null;
let originStopId = null; // only set when origin chosen from a bus stop

function escapeHtml(s) {
  if (s == null) return "";
  var div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function headers() {
  const h = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = "Bearer " + token;
  return h;
}

function show(el) {
  if (el) el.classList.remove("hidden");
}
function hide(el) {
  if (el) el.classList.add("hidden");
}

function setError(panel, message) {
  var err = panel === "login" ? document.getElementById("login-error") : document.getElementById("register-error");
  if (!err) return;
  err.textContent = message || "";
  if (message) { show(err); } else { hide(err); }
}

function runWhenReady(fn) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
}

runWhenReady(function () {
  var btnLogin = document.getElementById("btn-login");
  var btnRegister = document.getElementById("btn-register");
  var panelLogin = document.getElementById("panel-login");
  var panelRegister = document.getElementById("panel-register");
  var formLogin = document.getElementById("form-login");
  var formRegister = document.getElementById("form-register");
  var submitLogin = document.getElementById("submit-login");
  var submitRegister = document.getElementById("submit-register");

  if (!btnLogin || !panelLogin || !formLogin) return;

  btnLogin.addEventListener("click", function () {
    hide(panelRegister);
    show(panelLogin);
    setError("login", "");
    setError("register", "");
  });

  btnRegister.addEventListener("click", function () {
    hide(panelLogin);
    show(panelRegister);
    setError("login", "");
    setError("register", "");
  });

  formLogin.addEventListener("submit", function (e) {
    e.preventDefault();
    setError("login", "");
    var email = document.getElementById("login-email").value.trim();
    var password = document.getElementById("login-password").value;
    if (!email || !password) {
      setError("login", "Email and password are required.");
      return;
    }
    submitLogin.disabled = true;
    submitLogin.textContent = "Signing in...";
    fetch(API + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, status: res.status, d: d }; }); })
      .then(function (r) {
        submitLogin.disabled = false;
        submitLogin.textContent = "Sign in";
        if (!r.ok) {
          setError("login", r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : "Login failed") : "Login failed");
          return;
        }
        token = r.d.access_token;
        localStorage.setItem("token", token);
        hide(document.getElementById("auth-panels"));
        setLoggedIn(true);
        refreshIntents();
        refreshSessions();
      })
      .catch(function () {
        submitLogin.disabled = false;
        submitLogin.textContent = "Sign in";
        setError("login", "Network error. Is the server running?");
      });
  });

  formRegister.addEventListener("submit", function (e) {
    e.preventDefault();
    setError("register", "");
    var name = document.getElementById("register-name").value.trim();
    var email = document.getElementById("register-email").value.trim();
    var password = document.getElementById("register-password").value;
    if (!email || !password) {
      setError("register", "Email and password are required.");
      return;
    }
    if (password.length < 6) {
      setError("register", "Password must be at least 6 characters.");
      return;
    }
    submitRegister.disabled = true;
    submitRegister.textContent = "Creating account...";
    fetch(API + "/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password, name: name || null }),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, status: res.status, d: d }; }); })
      .then(function (r) {
        submitRegister.disabled = false;
        submitRegister.textContent = "Create account";
        if (!r.ok) {
          setError("register", r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : "Registration failed") : "Registration failed");
          return;
        }
        setError("register", "");
        show(panelLogin);
        hide(panelRegister);
        setError("login", "Account created. Please sign in.");
      })
      .catch(function () {
        submitRegister.disabled = false;
        submitRegister.textContent = "Create account";
        setError("register", "Network error. Is the server running?");
      });
  });

  document.getElementById("btn-logout").addEventListener("click", function () {
    token = null;
    localStorage.removeItem("token");
    setLoggedIn(false);
  });

  function setLoggedIn(loggedIn) {
    var main = document.getElementById("main");
    var authPanels = document.getElementById("auth-panels");
    if (loggedIn) {
      show(main);
      hide(authPanels);
      setError("login", "");
      setError("register", "");
      if (window.initMapWhenVisible) window.initMapWhenVisible();
      if (window.map) setTimeout(function () { window.map.invalidateSize(); }, 200);
      setTimeout(function () {
        if (window._stopsForMap && window.showStopsOnMap) window.showStopsOnMap(window._stopsForMap);
      }, 400);
      btnLogin.classList.add("hidden");
      btnRegister.classList.add("hidden");
      show(document.getElementById("btn-logout"));
      fetch(API + "/auth/me", { headers: headers() })
        .then(function (r) {
          if (!r.ok && r.status === 401) {
            token = null;
            localStorage.removeItem("token");
            setLoggedIn(false);
            return null;
          }
          return r.ok ? r.json() : null;
        })
        .then(function (u) {
          if (!u) return;
          var userInfo = document.getElementById("user-info");
          var userAvatar = document.getElementById("user-avatar");
          var userNameEmail = document.getElementById("user-name-email");
          if (userInfo) show(userInfo);
          if (userAvatar) {
            if (u.avatar_url) { userAvatar.src = u.avatar_url; userAvatar.style.display = ""; } else { userAvatar.style.display = "none"; }
          }
          if (userNameEmail) userNameEmail.textContent = (u.name && u.name.trim()) ? u.name : u.email;
          var vehicleCb = document.getElementById("profile-has-vehicle");
          if (vehicleCb) vehicleCb.checked = !!u.has_vehicle;
          var profileNameEl = document.getElementById("profile-name");
          if (profileNameEl) profileNameEl.value = u.name || "";
          var profileAvatarImg = document.getElementById("profile-avatar");
          if (profileAvatarImg) {
            if (u.avatar_url) { profileAvatarImg.src = u.avatar_url; profileAvatarImg.style.display = ""; }
            else { profileAvatarImg.style.display = "none"; }
          }
        });
      startUpdatesWS();
    } else {
      stopUpdatesWS();
      window.mapTweaksDisabled = false;
      hide(main);
      show(authPanels);
      show(panelLogin);
      hide(panelRegister);
      btnLogin.classList.remove("hidden");
      btnRegister.classList.remove("hidden");
      hide(document.getElementById("btn-logout"));
      var userInfo = document.getElementById("user-info");
      if (userInfo) hide(userInfo);
    }
  }

  var updatesWs = null;
  var updatesWsReconnectTimer = null;
  function startUpdatesWS() {
    if (updatesWs && updatesWs.readyState === WebSocket.OPEN) return;
    var t = token || (typeof localStorage !== "undefined" ? localStorage.getItem("token") : null);
    if (!t) return;
    var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    var url = protocol + "//" + window.location.host + "/ws/updates?token=" + encodeURIComponent(t);
    try {
      updatesWs = new WebSocket(url);
      updatesWs.onmessage = function (event) {
        try {
          var msg = JSON.parse(event.data);
          if (msg.type === "sessions") refreshSessions();
          else if (msg.type === "intents") refreshIntents();
        } catch (e) {}
      };
      updatesWs.onclose = function () {
        updatesWs = null;
        if (!token) return;
        updatesWsReconnectTimer = setTimeout(startUpdatesWS, 3000);
      };
      updatesWs.onerror = function () {};
    } catch (e) {}
  }
  function stopUpdatesWS() {
    if (updatesWsReconnectTimer) {
      clearTimeout(updatesWsReconnectTimer);
      updatesWsReconnectTimer = null;
    }
    if (updatesWs) {
      updatesWs.close();
      updatesWs = null;
    }
  }

  if (token) setLoggedIn(true);
  else setLoggedIn(false);

  var profileVehicle = document.getElementById("profile-has-vehicle");
  if (profileVehicle) {
    profileVehicle.addEventListener("change", function () {
      fetch(API + "/auth/me", {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({ has_vehicle: profileVehicle.checked }),
      }).catch(function () {});
    });
  }
  var profileName = document.getElementById("profile-name");
  if (profileName) {
    profileName.addEventListener("blur", function () {
      var name = profileName.value.trim();
      fetch(API + "/auth/me", {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({ name: name || null }),
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (u) {
          var userNameEmail = document.getElementById("user-name-email");
          if (userNameEmail && u) userNameEmail.textContent = (u.name && u.name.trim()) ? u.name : u.email;
        })
        .catch(function () {});
    });
  }
  var profileAvatarInput = document.getElementById("profile-avatar-input");
  if (profileAvatarInput) {
    profileAvatarInput.addEventListener("change", function () {
      var file = profileAvatarInput.files[0];
      if (!file) return;
      var fd = new FormData();
      fd.append("file", file);
      fetch(API + "/auth/me/avatar", {
        method: "POST",
        headers: { Authorization: "Bearer " + (token || localStorage.getItem("token") || "") },
        body: fd,
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (u) {
          if (!u || !u.avatar_url) return;
          var profileAvatar = document.getElementById("profile-avatar");
          var userAvatar = document.getElementById("user-avatar");
          if (profileAvatar) { profileAvatar.src = u.avatar_url; profileAvatar.style.display = ""; }
          if (userAvatar) { userAvatar.src = u.avatar_url; userAvatar.style.display = ""; }
        })
        .catch(function () {})
        .finally(function () { profileAvatarInput.value = ""; });
    });
  }

  (function initOriginStops() {
    var originBusStop = document.getElementById("origin-bus-stop");
    if (!originBusStop) return;
    var stopsList = [];
    function populateStops(stops) {
      if (!stops || !stops.length) return;
      stopsList = stops;
      window._stopsForMap = stops;
      originBusStop.innerHTML = "<option value=\"\">— Select bus stop —</option>";
      stops.forEach(function (s) {
        var opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        originBusStop.appendChild(opt);
      });
      if (window.showStopsOnMap) window.showStopsOnMap(stops);
    }
    function onStopChange() {
      var id = originBusStop.value;
      if (!id) return;
      var stop = stopsList.find(function (s) { return s.id === id; });
      if (!stop) return;
      originStopId = stop.id;
      origin = { lat: stop.lat, lng: stop.lng };
      var statusEl = document.getElementById("origin-status");
      if (statusEl) statusEl.textContent = "Origin: " + stop.name;
      if (window.setOriginMarker) setOriginMarker(origin);
      if (window.centerMapOnUser) centerMapOnUser(stop.lat, stop.lng, 16);
      if (destination && window.setUserRoute) setUserRoute(origin, destination);
      updateSubmitIntentDisabled();
      refreshWalkGuidance();
    }
    originBusStop.addEventListener("change", onStopChange);
    window.setOriginFromStop = function (stop) {
      originStopId = stop.id || null;
      origin = { lat: stop.lat, lng: stop.lng };
      var statusEl = document.getElementById("origin-status");
      if (statusEl) statusEl.textContent = "Origin: " + stop.name;
      if (originBusStop) originBusStop.value = stop.id || "";
      if (window.setOriginMarker) setOriginMarker(origin);
      if (window.centerMapOnUser) centerMapOnUser(stop.lat, stop.lng, 16);
      if (destination && window.setUserRoute) setUserRoute(origin, destination);
      updateSubmitIntentDisabled();
      refreshWalkGuidance();
    };
    window.onClearOriginRequested = function () {
      origin = null;
      originStopId = null;
      var statusEl = document.getElementById("origin-status");
      if (statusEl) statusEl.textContent = "";
      if (originBusStop) originBusStop.value = "";
      if (window.clearOriginMarker) clearOriginMarker();
      updateSubmitIntentDisabled();
      refreshWalkGuidance();
    };
    window.onClearDestinationRequested = function () {
      destination = null;
      var destStatus = document.getElementById("destination-status");
      if (destStatus) destStatus.textContent = "";
      if (window.clearDestMarker) clearDestMarker();
      updateSubmitIntentDisabled();
      refreshWalkGuidance();
    };
    fetch(API + "/stops", { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (stops) {
        if (Array.isArray(stops) && stops.length) populateStops(stops);
        else if (typeof BUS_STOPS !== "undefined" && BUS_STOPS.length) populateStops(BUS_STOPS);
      })
      .catch(function () {
        if (typeof BUS_STOPS !== "undefined" && BUS_STOPS.length) populateStops(BUS_STOPS);
      });
  })();

  document.getElementById("use-my-location").addEventListener("click", function () {
    var originBusStop = document.getElementById("origin-bus-stop");
    if (originBusStop) originBusStop.value = "";
    originStopId = null;
    var status = document.getElementById("origin-status");
    status.textContent = "Getting location...";
    if (!navigator.geolocation) {
      status.textContent = "Geolocation not supported";
      return;
    }
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        origin = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        status.textContent = "Set: " + origin.lat.toFixed(4) + ", " + origin.lng.toFixed(4);
        if (window.setOriginMarker) setOriginMarker(origin);
        if (window.centerMapOnUser) centerMapOnUser(origin.lat, origin.lng);
        if (destination && window.setUserRoute) setUserRoute(origin, destination);
        updateSubmitIntentDisabled();
        refreshWalkGuidance();
      },
      function () { status.textContent = "Location failed"; }
    );
  });

  function showWalkGuidance(html) {
    var box = document.getElementById("walk-guidance");
    if (!box) return;
    if (!html) { box.innerHTML = ""; hide(box); return; }
    box.innerHTML = html;
    show(box);
  }

  function fmtM(m) {
    if (m == null) return "";
    if (m < 1000) return Math.round(m) + " m";
    return (m / 1000).toFixed(2) + " km";
  }
  function fmtMin(s) {
    if (s == null) return "";
    return Math.max(1, Math.round(s / 60)) + " min";
  }

  function refreshWalkGuidance() {
    if (!originStopId || !destination) {
      showWalkGuidance("");
      return;
    }
    showWalkGuidance("<h4>Walking directions</h4><div class=\"walk-meta\">Loading…</div>");
    fetch(API + "/guidance/walk-from-stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stop_id: originStopId, dest_lat: destination.lat, dest_lng: destination.lng }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok) {
          showWalkGuidance("<h4>Walking directions</h4><div class=\"walk-meta\">Could not load directions.</div>");
          return;
        }
        var g = res.d;
        var steps = (g.steps || []).slice(0, 12);
        var meta = fmtM(g.distance_m) + " · " + fmtMin(g.duration_s);
        var list = steps.map(function (s) {
          return "<li>" + escapeHtml(s.instruction || "Continue") + " <span class=\"sidebar-hint\">(" + fmtM(s.distance_m) + ")</span></li>";
        }).join("");
        showWalkGuidance(
          "<h4>Walking directions</h4>" +
          "<div class=\"walk-meta\">" + escapeHtml(meta) + "</div>" +
          "<ol>" + list + "</ol>"
        );
      })
      .catch(function () {
        showWalkGuidance("<h4>Walking directions</h4><div class=\"walk-meta\">Could not load directions.</div>");
      });
  }

  function updateSubmitIntentDisabled() {
    var btn = document.getElementById("submit-intent");
    if (btn) btn.disabled = !(origin && destination);
  }

  document.getElementById("submit-intent").addEventListener("click", function () {
    if (!origin || !destination) return;
    var body = {
      origin_lat: origin.lat,
      origin_lng: origin.lng,
      dest_lat: destination.lat,
      dest_lng: destination.lng,
      expires_in_minutes: 60,
    };
    fetch(API + "/intents", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(body),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
      .then(function (r) {
        if (!r.ok) {
          var msg = r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : r.d.detail) : "Failed to create intent";
          alert(msg);
          return;
        }
        origin = null;
        destination = null;
        originStopId = null;
        document.getElementById("origin-status").textContent = "";
        var destStatusEl = document.getElementById("destination-status");
        if (destStatusEl) destStatusEl.textContent = "";
        showWalkGuidance("");
        var ob = document.getElementById("origin-bus-stop");
        if (ob) ob.value = "";
        if (window.clearOriginMarker) clearOriginMarker();
        if (window.clearDestMarker) clearDestMarker();
        if (window.clearUserRoute) clearUserRoute();
        updateSubmitIntentDisabled();
        refreshIntents();
      });
  });

  async function refreshIntents() {
    var res = await fetch(API + "/intents", { headers: headers() });
    if (!res.ok) {
      if (res.status === 401) { token = null; localStorage.removeItem("token"); setLoggedIn(false); }
      return;
    }
    var list = await res.json();
    var sel = document.getElementById("match-intent-select");
    sel.innerHTML = "<option value=''>Select intent</option>";
    list.forEach(function (i) {
      var opt = document.createElement("option");
      opt.value = i.id;
      opt.textContent = "Intent #" + i.id;
      sel.appendChild(opt);
    });
    var div = document.getElementById("intents-list");
    div.innerHTML = list.length ? list.map(function (i) {
      return "<div class=\"intent-item\">" +
        "<span class=\"intent-item-text\">#" + i.id + " \u2192 " + i.dest_lat.toFixed(4) + ", " + i.dest_lng.toFixed(4) + "</span>" +
        " <button type=\"button\" class=\"btn btn-sm btn-danger intent-delete-btn\" data-intent-id=\"" + i.id + "\" data-action=\"delete-intent\" title=\"Delete intent (any session using it will be removed)\">Delete intent</button>" +
        "</div>";
    }).join("") : "None";
    div.querySelectorAll("[data-action=\"delete-intent\"]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        deleteIntent(parseInt(btn.dataset.intentId, 10));
      });
    });
  }

  function deleteIntent(intentId) {
    if (!confirm("Delete this intent? Any session using it will also be removed.")) return;
    fetch(API + "/intents/" + intentId, {
      method: "DELETE",
      headers: headers(),
    })
      .then(function (res) {
        if (res.status === 204) {
          refreshIntents();
          refreshSessions();
          return;
        }
        return res.json().then(function (d) { return { status: res.status, d: d }; });
      })
      .then(function (r) {
        if (r && r.status !== 204) alert(r.d && r.d.detail ? r.d.detail : "Failed to delete");
      })
      .catch(function () { alert("Failed to delete"); });
  }

  document.getElementById("refresh-intents").addEventListener("click", refreshIntents);

  document.getElementById("fetch-matches").addEventListener("click", function () {
    var id = document.getElementById("match-intent-select").value;
    if (!id) { alert("Select an intent"); return; }
    fetch(API + "/intents/matches?intent_id=" + id, { headers: headers() })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
      .then(function (r) {
        if (!r.ok) {
          alert(r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : "Failed") : "Failed");
          return;
        }
        var cards = r.d;
        var listEl = document.getElementById("matches-list");
        if (cards && cards.length) {
          listEl.innerHTML = cards.map(function (card) {
            var mode = card.has_vehicle ? "Vehicle" : "Walker";
            var rating = card.past_rating_avg != null ? card.past_rating_avg.toFixed(1) + " ★" : "No ratings";
            var displayName = (card.name && card.name.trim()) ? card.name.trim() : "Buddy";
            var sameStopBadge = card.same_bus_stop ? " <span class=\"match-badge match-badge-bus\">Same bus stop</span>" : "";
            var avatarHtml = card.avatar_url
              ? "<img class=\"match-card-avatar\" src=\"" + card.avatar_url + "\" alt=\"\" />"
              : "<span class=\"match-card-avatar match-card-avatar-placeholder\">" + (displayName.charAt(0).toUpperCase()) + "</span>";
            return "<div class=\"match-card\">" +
              "<div class=\"match-card-header\">" + avatarHtml +
              "<div class=\"match-card-title\"><span class=\"match-card-name\">" + escapeHtml(displayName) + "</span>" +
              "<span class=\"match-badge match-badge-" + (card.has_vehicle ? "vehicle" : "walker") + "\">" + mode + "</span>" +
              sameStopBadge +
              " <strong class=\"match-score\">Buddy " + card.buddy_score.toFixed(0) + "</strong></div></div>" +
              "<div class=\"match-card-meta\">Route overlap: " + card.route_overlap_score.toFixed(0) + " · " + rating + "</div>" +
              "<div class=\"match-card-route\">" + card.origin_lat.toFixed(3) + "," + card.origin_lng.toFixed(3) + " → " + card.dest_lat.toFixed(3) + "," + card.dest_lng.toFixed(3) + "</div>" +
              "<button type=\"button\" class=\"btn btn-sm btn-primary\" data-intent-a=\"" + id + "\" data-intent-b=\"" + card.intent_id + "\">Create session</button>" +
              "</div>";
          }).join("");
          listEl.querySelectorAll("[data-intent-a]").forEach(function (btn) {
            btn.addEventListener("click", function () {
              createSession(btn.dataset.intentA, btn.dataset.intentB);
            });
          });
        } else {
          listEl.innerHTML = "<p class=\"sidebar-hint\">No matches. Vehicle users see only walkers; walkers see walkers and vehicles.</p>";
        }
      });
  });

  function createSession(intentAId, intentBId) {
    fetch(API + "/sessions", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ intent_a_id: parseInt(intentAId, 10), intent_b_id: parseInt(intentBId, 10) }),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
      .then(function (r) {
        if (!r.ok) {
          var msg = r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : "Failed") : "Failed";
          alert(msg);
          return;
        }
        refreshSessions();
      });
  }

  async function refreshSessions() {
    var res = await fetch(API + "/sessions/me", { headers: headers() });
    if (!res.ok) {
      if (res.status === 401) { token = null; localStorage.removeItem("token"); setLoggedIn(false); }
      return;
    }
    var list = await res.json();
    var div = document.getElementById("sessions-list");
    var html = "";
    list.forEach(function (s) {
      var btns = "";
      if (s.state === "REQUESTED") {
        if (s.my_side === "b") btns = "<button type=\"button\" class=\"btn btn-sm\" data-id=\"" + s.id + "\" data-action=\"accept\">Accept</button> <button type=\"button\" class=\"btn btn-sm btn-danger\" data-id=\"" + s.id + "\" data-action=\"abort\">Abort</button>";
        else btns = "<span class=\"session-waiting\">Waiting for acceptance</span> <button type=\"button\" class=\"btn btn-sm btn-danger\" data-id=\"" + s.id + "\" data-action=\"abort\">Abort</button>";
      }
      if (s.state === "ACCEPTED") btns = "<button type=\"button\" class=\"btn btn-sm\" data-id=\"" + s.id + "\" data-action=\"activate\">Activate</button> <button type=\"button\" class=\"btn btn-sm btn-danger\" data-id=\"" + s.id + "\" data-action=\"abort\">Abort</button>";
      if (s.state === "ACTIVE") btns = "<button type=\"button\" class=\"btn btn-sm\" data-id=\"" + s.id + "\" data-action=\"complete\">Complete</button> <button type=\"button\" class=\"btn btn-sm btn-danger\" data-id=\"" + s.id + "\" data-action=\"abort\">Abort</button> <button type=\"button\" class=\"btn btn-sm btn-sos\" data-id=\"" + s.id + "\" data-action=\"sos\">SOS</button>";
      html += "<div class=\"session-card\"><span class=\"state state-" + s.state.toLowerCase() + "\">" + s.state + "</span> Session #" + s.id + (s.sos_at ? " <strong class=\"sos-tag\">SOS</strong>" : "") + " " + btns + "</div>";
    });
    div.innerHTML = html || "None";
    div.querySelectorAll("[data-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        sessionAction(btn.dataset.id, btn.dataset.action);
      });
    });
    document.getElementById("sos-banner").classList.toggle("hidden", !list.some(function (s) { return s.sos_at; }));
    var withRoutes = list.find(function (s) { return s.route_a && s.route_b; });
    if (withRoutes && window.showSessionRoutes) showSessionRoutes(withRoutes.route_a, withRoutes.route_b, withRoutes.my_side);
    else if (window.clearSessionRoutes) clearSessionRoutes();
    list.forEach(function (s) {
      if (s.state === "ACTIVE" && s.my_token && window.startLocationStream) startLocationStream(s.id, s.my_token, s.my_side);
    });
    var hasActive = list.some(function (s) { return s.state === "ACTIVE"; });
    window.mapTweaksDisabled = hasActive;
    var useLocBtn = document.getElementById("use-my-location");
    if (useLocBtn) {
      useLocBtn.disabled = hasActive;
      useLocBtn.title = hasActive ? "Map is locked while a session is active" : "";
    }
  }

  document.getElementById("refresh-sessions").addEventListener("click", refreshSessions);

  function sessionAction(sessionId, action) {
    fetch(API + "/sessions/" + sessionId + "/" + action, {
      method: "POST",
      headers: headers(),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
      .then(function (r) {
        if (!r.ok) {
          alert(r.d && r.d.detail ? (typeof r.d.detail === "string" ? r.d.detail : "Failed") : "Failed");
          return;
        }
        refreshSessions();
      });
  }

  function setDestination(lat, lng) {
    destination = { lat: lat, lng: lng };
    var destStatus = document.getElementById("destination-status");
    if (destStatus) destStatus.textContent = "Looking up address…";
    if (origin && window.setUserRoute) setUserRoute(origin, destination);
    updateSubmitIntentDisabled();
    refreshWalkGuidance();
    var url = "https://nominatim.openstreetmap.org/reverse?lat=" + encodeURIComponent(lat) + "&lon=" + encodeURIComponent(lng) + "&format=json";
    fetch(url, { headers: { "Accept": "application/json", "Accept-Language": "en", "User-Agent": "LastMile-Connect/1.0" } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var name = (data && data.display_name) ? data.display_name : (lat.toFixed(4) + ", " + lng.toFixed(4));
        if (destStatus) destStatus.textContent = "Destination: " + name;
        if (window.updateDestMarkerPopup) window.updateDestMarkerPopup(name);
      })
      .catch(function () {
        if (destStatus) destStatus.textContent = "Destination: " + lat.toFixed(4) + ", " + lng.toFixed(4);
      });
  }

  window.updateUserRoute = function () {
    if (origin && destination && window.setUserRoute) setUserRoute(origin, destination);
  };

  window.setDestination = setDestination;
});
