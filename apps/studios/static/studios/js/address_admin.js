(function () {
  let map = null;
  let marker = null;
  let autocompleteTimeout = null;
  let lastSearchTerm = "";

  function waitForLeaflet(callback, maxAttempts = 50) {
    let attempts = 0;
    const checkLeaflet = setInterval(() => {
      attempts++;
      if (typeof L !== "undefined" && L.map) {
        clearInterval(checkLeaflet);
        callback();
      } else if (attempts >= maxAttempts) {
        clearInterval(checkLeaflet);
        console.error("Leaflet failed to load after", maxAttempts, "attempts");
      }
    }, 100);
  }

  function initAddressAutocomplete() {
    console.log("[Address Admin] Starting initialization...");
    const addressInput = document.querySelector(".address-autocomplete");
    if (!addressInput) {
      console.warn("[Address Admin] Address input not found");
      return;
    }

    console.log("[Address Admin] Address input found, waiting for Leaflet...");
    // Wait for Leaflet to be available
    waitForLeaflet(() => {
      if (typeof L === "undefined" || !L.map) {
        console.error("[Address Admin] Leaflet is not available after waiting");
        return;
      }

      console.log("[Address Admin] Leaflet loaded! Initializing map and autocomplete...");
      initializeMapAndAutocomplete(addressInput);
    });
  }

  function initializeMapAndAutocomplete(addressInput) {

    const latInput = document.getElementById("id_latitude");
    const lngInput = document.getElementById("id_longitude");

    // Create map container if not present
    let mapContainer = document.getElementById("address-map");
    if (!mapContainer) {
      console.log("[Address Admin] Creating map container...");
      mapContainer = document.createElement("div");
      mapContainer.id = "address-map";
      mapContainer.style.width = "100%";
      mapContainer.style.height = "300px";
      mapContainer.style.marginTop = "10px";
      mapContainer.style.marginBottom = "10px";
      mapContainer.style.border = "1px solid #ddd";
      mapContainer.style.borderRadius = "4px";
      addressInput.parentElement.appendChild(mapContainer);
      console.log("[Address Admin] Map container created and added to DOM");
    } else {
      console.log("[Address Admin] Map container already exists");
    }

    // Initialize map
    const initialLat = latInput && latInput.value ? parseFloat(latInput.value) : -33.4489; // Santiago, Chile
    const initialLng = lngInput && lngInput.value ? parseFloat(lngInput.value) : -70.6693;

    console.log("[Address Admin] Initializing Leaflet map at", initialLat, initialLng);
    try {
      map = L.map(mapContainer).setView([initialLat, initialLng], 14);
      console.log("[Address Admin] Map initialized successfully");
    } catch (error) {
      console.error("[Address Admin] Error initializing map:", error);
      return;
    }

    // Add CartoDB Positron tiles (similar to Google Maps default style)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    // Add marker
    marker = L.marker([initialLat, initialLng], { draggable: false }).addTo(map);

    // Create autocomplete dropdown
    const autocompleteContainer = document.createElement("div");
    autocompleteContainer.className = "address-autocomplete-results";
    autocompleteContainer.style.display = "none";
    autocompleteContainer.style.position = "absolute";
    autocompleteContainer.style.zIndex = "10000";
    autocompleteContainer.style.backgroundColor = "#ffffff";
    autocompleteContainer.style.border = "2px solid #417690";
    autocompleteContainer.style.borderRadius = "4px";
    autocompleteContainer.style.maxHeight = "250px";
    autocompleteContainer.style.overflowY = "auto";
    autocompleteContainer.style.width = addressInput.offsetWidth + "px";
    autocompleteContainer.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
    autocompleteContainer.style.marginTop = "2px";
    addressInput.parentElement.style.position = "relative";
    addressInput.parentElement.appendChild(autocompleteContainer);

    // Search addresses using Nominatim
    function searchAddresses(query) {
      if (query.length < 3) {
        autocompleteContainer.style.display = "none";
        return;
      }

      // Clear previous timeout
      if (autocompleteTimeout) {
        clearTimeout(autocompleteTimeout);
      }

      // Debounce: wait 300ms before making request
      autocompleteTimeout = setTimeout(() => {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`;

        fetch(url, {
          headers: {
            "User-Agent": "AdminStudio Django App", // Required by Nominatim
          },
        })
          .then((response) => response.json())
          .then((data) => {
            displayAutocompleteResults(data);
          })
          .catch((error) => {
            console.error("Error searching addresses:", error);
          });
      }, 300);
    }

    function displayAutocompleteResults(results) {
      autocompleteContainer.innerHTML = "";

      if (results.length === 0) {
        autocompleteContainer.style.display = "none";
        return;
      }

      results.forEach((result) => {
        const item = document.createElement("div");
        item.style.padding = "10px 14px";
        item.style.cursor = "pointer";
        item.style.borderBottom = "1px solid #e0e0e0";
        item.style.color = "#333333";
        item.style.fontSize = "14px";
        item.style.lineHeight = "1.4";
        item.style.transition = "background-color 0.2s ease";
        item.textContent = result.display_name;

        item.addEventListener("mouseenter", () => {
          item.style.backgroundColor = "#417690";
          item.style.color = "#ffffff";
        });

        item.addEventListener("mouseleave", () => {
          item.style.backgroundColor = "#ffffff";
          item.style.color = "#333333";
        });

        item.addEventListener("click", () => {
          selectAddress(result);
        });

        autocompleteContainer.appendChild(item);
      });

      autocompleteContainer.style.display = "block";
    }

    function selectAddress(result) {
      const lat = parseFloat(result.lat);
      const lng = parseFloat(result.lon);

      // Update input fields
      addressInput.value = result.display_name;
      if (latInput) {
        latInput.value = lat.toFixed(6);
      }
      if (lngInput) {
        lngInput.value = lng.toFixed(6);
      }

      // Update map
      map.setView([lat, lng], 14);
      marker.setLatLng([lat, lng]);

      // Hide autocomplete
      autocompleteContainer.style.display = "none";
    }

    // Handle input events
    addressInput.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      if (query !== lastSearchTerm) {
        lastSearchTerm = query;
        searchAddresses(query);
      }
    });

    // Hide autocomplete when clicking outside
    document.addEventListener("click", (e) => {
      if (!addressInput.contains(e.target) && !autocompleteContainer.contains(e.target)) {
        autocompleteContainer.style.display = "none";
      }
    });

    // Update map when lat/lng are manually changed
    if (latInput && lngInput) {
      const updateMapFromInputs = () => {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        if (!isNaN(lat) && !isNaN(lng)) {
          map.setView([lat, lng], 14);
          marker.setLatLng([lat, lng]);
        }
      };

      latInput.addEventListener("change", updateMapFromInputs);
      lngInput.addEventListener("change", updateMapFromInputs);
    }
  }

  // Initialize when DOM is ready and scripts are loaded
  function tryInit() {
    if (document.readyState === "complete") {
      // DOM is ready, but wait for Leaflet to load
      initAddressAutocomplete();
    } else {
      // Wait for DOM to be ready first
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
          // Wait a bit more for external scripts (Leaflet) to load
          setTimeout(initAddressAutocomplete, 500);
        });
      } else {
        // DOM is interactive, wait for complete
        document.addEventListener("readystatechange", () => {
          if (document.readyState === "complete") {
            setTimeout(initAddressAutocomplete, 500);
          }
        });
      }
    }
  }

  // Start initialization
  tryInit();
})();
