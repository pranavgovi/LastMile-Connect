/**
 * Hardcoded bus stops around FSU campus (Tallahassee, FL). MVP / demo data.
 * Coordinates approximate (FSU area ~ 30.44, -84.30).
 */
(function (global) {
  var BUS_STOPS = [
    { id: "tennessee-dewey", name: "Tennessee St & Dewey St", lat: 30.4425, lng: -84.2950 },
    { id: "jefferson-dorman", name: "Jefferson St at Dorman Hall", lat: 30.4410, lng: -84.2985 },
    { id: "call-st", name: "Call St at Woodward Ave", lat: 30.4398, lng: -84.3010 },
    { id: "gaines-st", name: "Gaines St at Railroad Ave", lat: 30.4375, lng: -84.2960 },
    { id: "tennessee-macomb", name: "Tennessee St & Macomb St", lat: 30.4430, lng: -84.2880 },
    { id: "jefferson-gray", name: "Jefferson St at Gray St", lat: 30.4405, lng: -84.2995 },
    { id: "copeland", name: "Copeland St (Strozier)", lat: 30.4435, lng: -84.3020 },
    { id: "w-jefferson", name: "W Jefferson St (Lorene)", lat: 30.4418, lng: -84.3050 },
  ];

  global.BUS_STOPS = BUS_STOPS;
})(typeof window !== "undefined" ? window : this);
