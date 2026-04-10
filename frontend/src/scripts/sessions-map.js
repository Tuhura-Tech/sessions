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

const MAP_DEBUG =
	typeof window !== 'undefined' &&
	(new URLSearchParams(window.location.search).has('mapDebug') ||
		window.localStorage?.getItem('mapDebug') === '1');

function debugLog(...args) {
	if (MAP_DEBUG) {
		console.log('[Tuhura][MapDebug]', ...args);
	}
}

/** @returns {Promise<any>} */
async function loadLeaflet() {
	try {
		return await import('leaflet');
	} catch (importError) {
		// Fallback for environments where bare module specifiers fail in emitted script assets.
		if (window.L) return window.L;

		await new Promise((resolve, reject) => {
			const existing = document.querySelector('script[data-leaflet-cdn="true"]');
			if (existing) {
				existing.addEventListener('load', () => resolve(undefined), { once: true });
				existing.addEventListener('error', reject, { once: true });
				return;
			}

			const script = document.createElement('script');
			script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
			script.async = true;
			script.dataset.leafletCdn = 'true';
			script.addEventListener('load', () => resolve(undefined), { once: true });
			script.addEventListener('error', reject, { once: true });
			document.head.appendChild(script);
		});

		if (window.L) return window.L;
		throw importError;
	}
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

/** @param {[number, number]} latlong */
function isValidLatlong(latlong) {
	if (!Array.isArray(latlong) || latlong.length !== 2) return false;
	const [lat, lng] = latlong;
	if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
	if (lat < -90 || lat > 90) return false;
	if (lng < -180 || lng > 180) return false;
	// Common geocoding fallback for unknown addresses.
	if (Math.abs(lat) < 0.0001 && Math.abs(lng) < 0.0001) return false;
	return true;
}

/** @param {HTMLElement} mapEl */
async function initMap(mapEl) {
	if (mapEl.dataset.mapInitialized === 'true') return;
	mapEl.dataset.mapInitialized = 'true';

	try {
		const sessions = parseSessions(mapEl);
		if (!sessions.length) return;
		debugLog('map element', mapEl.id || '(no-id)', 'total sessions', sessions.length);

		const mapId = mapEl.id;
		if (!mapId) return;

		const L = await loadLeaflet();
		const { Map: LeafletMap, TileLayer, Marker, Popup, FeatureGroup, Icon } = L;

		const icon = new Icon({
			iconUrl: '/marker-icon.png',
			shadowUrl: '/marker-shadow.png',
			iconSize: [25, 41],
			iconAnchor: [12, 39],
		});

		const mapRef = new LeafletMap(mapId, {
			attributionControl: true,
			worldCopyJump: true,
			minZoom: 4,
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
		let firstMarkerLatlong = null;
		const validLatlongs = [];
		const invalidSessions = [];

		for (const session of sessions) {
			if (!session?.latlong || !isValidLatlong(session.latlong)) {
				invalidSessions.push({
					name: session?.name,
					address: session?.address,
					latlong: session?.latlong,
				});
				continue;
			}
			const marker = new Marker(session.latlong, { icon }).addTo(markerLayerRef);
			markerCount += 1;
			validLatlongs.push(session.latlong);
			if (!firstMarkerLatlong) firstMarkerLatlong = session.latlong;
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

		debugLog('valid markers', markerCount, validLatlongs);
		if (invalidSessions.length > 0) {
			debugLog('invalid sessions filtered', invalidSessions.length, invalidSessions);
		}

		try {
			if (markerCount === 1 && firstMarkerLatlong) {
				mapRef.setView(firstMarkerLatlong, 15, { animate: false });
				debugLog('single marker setView', { center: firstMarkerLatlong, zoom: 15 });
			} else if (markerCount > 1) {
				const bounds = markerLayerRef.getBounds().pad(0.1);
				mapRef.fitBounds(bounds, { maxZoom: 12 });
				debugLog('fitBounds applied', {
					northEast: bounds.getNorthEast(),
					southWest: bounds.getSouthWest(),
					center: mapRef.getCenter(),
					zoom: mapRef.getZoom(),
				});
				if (mapRef.getZoom() < 4) {
					mapRef.setZoom(4, { animate: false });
					debugLog('zoom clamped to min', 4);
				}
			} else {
				debugLog('no valid markers; keeping default view');
			}
		} catch {
			// ignore
		}
	} catch (error) {
		console.error('[Tuhura] Map initialization failed', error);
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
