/** @typedef {Object} Session
 * @property {string} name
 * @property {string} address
 * @property {[number, number]} latlong
 * @property {string} age
 * @property {string} time
 */

/** @param {HTMLElement} mapEl */
function showMapError(mapEl) {
	mapEl.innerHTML =
		'<div class="flex h-full items-center justify-center px-6 text-center text-sm text-red-700">Map failed to load. Please refresh the page, or open the session address directly in Google Maps.</div>';
}

/** @param {HTMLElement} mapEl
 * @returns {Session[]}
 */
function parseSessions(mapEl) {
	try {
		const raw = mapEl.getAttribute('data-sessions') || '[]';
		const parsed = JSON.parse(raw);
		return Array.isArray(parsed) ? parsed : [];
	} catch {
		return [];
	}
}

/** @param {HTMLElement} mapEl */
async function initMap(mapEl) {
	if (mapEl.dataset.mapInitialized === 'true') return;
	mapEl.dataset.mapInitialized = 'true';

	try {
		const sessions = parseSessions(mapEl);
		if (!sessions.length) return;

		const mapId = mapEl.id;
		if (!mapId) return;

		const L = await import('leaflet');
		const { Map: LeafletMap, TileLayer, Marker, Popup, FeatureGroup, Icon } = L;

		const icon = new Icon({
			iconUrl: '/marker-icon.png',
			shadowUrl: '/marker-shadow.png',
			iconSize: [25, 41],
			iconAnchor: [12, 39],
		});

		const mapRef = new LeafletMap(mapId, {
			attributionControl: true,
		});

		// Always start with a sane default view so the map renders even before
		// markers are added or when marker data is incomplete.
		mapRef.setView([-41.2865, 174.7762], 11, { animate: false });

		// Add tile layer first
		new TileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 19,
			attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
		}).addTo(mapRef);

		const markerLayerRef = new FeatureGroup();
		mapRef.addLayer(markerLayerRef);
		let markerCount = 0;

		for (const session of sessions) {
			if (!session?.latlong || session.latlong.length !== 2) continue;
			const marker = new Marker(session.latlong, { icon }).addTo(markerLayerRef);
			markerCount += 1;
			const q = encodeURIComponent(`${session.name}, ${session.address}`);
			const popupContent = `
				<div>
					<strong>${session.name}</strong><br />
					${session.time}<br />
					${session.age}<br />
					${session.address}<br />
					<a href="https://www.google.com/maps/search/?api=1&query=${q}" target="_blank" rel="noopener noreferrer">Open in Maps</a>
				</div>
			`;
			marker.bindPopup(new Popup({ maxWidth: 300 }).setContent(popupContent));
		}

		try {
			if (markerCount === 1 && sessions[0]?.latlong) {
				mapRef.setView(sessions[0].latlong, 17, { animate: false });
			} else if (markerCount > 1) {
				mapRef.fitBounds(markerLayerRef.getBounds().pad(0.1));
			}
		} catch {
			// ignore
		}
	} catch {
		showMapError(mapEl);
	}
}

function observeAndInit(mapEl) {
	if ('IntersectionObserver' in window) {
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((e) => e.isIntersecting)) {
					observer.disconnect();
					initMap(mapEl);
				}
			},
			{ rootMargin: '200px' },
		);
		observer.observe(mapEl);
	} else {
		initMap(mapEl);
	}
}

function initAll() {
	const maps = Array.from(document.querySelectorAll('[data-sessions-map="true"]'));
	for (const mapEl of maps) {
		// Mark as needing initialization
		mapEl.dataset.mapNeedsInit = 'true';
		observeAndInit(mapEl);
	}
}

// Watch for when map containers become visible and retry initialization
function watchMapVisibility() {
	const observer = new MutationObserver(() => {
		const maps = Array.from(
			document.querySelectorAll('[data-sessions-map="true"][data-map-needs-init="true"]'),
		);
		for (const mapEl of maps) {
			const parent = mapEl.closest('.map-container');
			if (parent && !parent.classList.contains('hidden')) {
				delete mapEl.dataset.mapNeedsInit;
				observeAndInit(mapEl);
			}
		}
	});

	observer.observe(document.body, {
		attributes: true,
		attributeFilter: ['class'],
		subtree: true,
	});
}

if (document.readyState === 'loading') {
	document.addEventListener(
		'DOMContentLoaded',
		() => {
			initAll();
			watchMapVisibility();
		},
		{ once: true },
	);
} else {
	initAll();
	watchMapVisibility();
}
