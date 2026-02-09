type Session = {
	name: string;
	address: string;
	latlong: [number, number];
	age: string;
	time: string;
};

function parseSessions(mapEl: HTMLElement): Session[] {
	try {
		const raw = mapEl.getAttribute('data-sessions') || '[]';
		const parsed = JSON.parse(raw);
		return Array.isArray(parsed) ? (parsed as Session[]) : [];
	} catch {
		return [];
	}
}

async function initMap(mapEl: HTMLElement): Promise<void> {
	if (mapEl.dataset.mapInitialized === 'true') return;
	mapEl.dataset.mapInitialized = 'true';

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

	// Add tile layer first
	new TileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
		maxZoom: 19,
		attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
	}).addTo(mapRef);

	const markerLayerRef = new FeatureGroup();
	mapRef.addLayer(markerLayerRef);

	for (const session of sessions) {
		if (!session?.latlong || session.latlong.length !== 2) continue;
		const marker = new Marker(session.latlong, { icon }).addTo(markerLayerRef);
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
		if (sessions.length === 1 && sessions[0]?.latlong) {
			mapRef.setView(sessions[0].latlong, 17, { animate: false });
		} else if (sessions.length > 1) {
			mapRef.fitBounds(markerLayerRef.getBounds().pad(0.1));
		}
	} catch {
		// ignore
	}
}

function observeAndInit(mapEl: HTMLElement): void {
	if ('IntersectionObserver' in window) {
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((e) => e.isIntersecting)) {
					observer.disconnect();
					void initMap(mapEl);
				}
			},
			{ rootMargin: '200px' },
		);
		observer.observe(mapEl);
	} else {
		void initMap(mapEl);
	}
}

function initAll(): void {
	const maps = Array.from(document.querySelectorAll<HTMLElement>('[data-sessions-map="true"]'));
	for (const mapEl of maps) {
		// Mark as needing initialization
		mapEl.dataset.mapNeedsInit = 'true';
		observeAndInit(mapEl);
	}
}

// Watch for when map containers become visible and retry initialization
function watchMapVisibility(): void {
	const observer = new MutationObserver(() => {
		const maps = Array.from(
			document.querySelectorAll<HTMLElement>(
				'[data-sessions-map="true"][data-map-needs-init="true"]',
			),
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
