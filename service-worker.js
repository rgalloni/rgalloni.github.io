const CACHE_NAME = 'istanbul-guide-spa-v11';
const PRECACHE_URLS = [
  "app_mobile.html",
  "assets/fontawesome/css/all.min.css",
  "assets/fontawesome/webfonts/fa-brands-400.ttf",
  "assets/fontawesome/webfonts/fa-brands-400.woff2",
  "assets/fontawesome/webfonts/fa-regular-400.ttf",
  "assets/fontawesome/webfonts/fa-regular-400.woff2",
  "assets/fontawesome/webfonts/fa-solid-900.ttf",
  "assets/fontawesome/webfonts/fa-solid-900.woff2",
  "assets/fontawesome/webfonts/fa-v4compatibility.ttf",
  "assets/fontawesome/webfonts/fa-v4compatibility.woff2",
  "assets/js/marked.min.js",
  "assets/js/panzoom.min.js",
  "data/ar/activities.json",
  "data/ar/bookings.json",
  "data/ar/itineraries.json",
  "data/ar/sections.json",
  "data/en/activities.json",
  "data/en/bookings.json",
  "data/en/itineraries.json",
  "data/en/sections.json",
  "data/it/activities.json",
  "data/it/bookings.json",
  "data/it/itineraries.json",
  "data/it/sections.json",
  "data/security/auth.json",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "images/01_hippodrome_of_constantinople.jpg",
  "images/02_basilica_cistern.jpg",
  "images/03_blue_mosque.jpg",
  "images/04_hagia_sophia.jpg",
  "images/05_topkapi_palace.jpg",
  "images/06_grand_bazaar.jpg",
  "images/07_spice_bazaar.jpg",
  "images/08_rustem_pasha_mosque.jpg",
  "images/09_galata_tower.jpg",
  "images/10_galata_bridge.jpg",
  "images/11_taksim_square.jpg",
  "images/Istanbul-City-Map.jpg",
  "images/_normalized/01_hippodrome_of_constantinople.png",
  "images/_normalized/02_basilica_cistern.png",
  "images/_normalized/03_blue_mosque.png",
  "images/_normalized/04_hagia_sophia.png",
  "images/_normalized/05_topkapi_palace.png",
  "images/_normalized/06_grand_bazaar.png",
  "images/_normalized/07_spice_bazaar.png",
  "images/_normalized/08_rustem_pasha_mosque.png",
  "images/_normalized/09_galata_tower.png",
  "images/_normalized/10_galata_bridge.png",
  "images/_normalized/11_taksim_square.png",
  "manifest.webmanifest"
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
      return response;
    }).catch(() => caches.match('app_mobile.html')))
  );
});
