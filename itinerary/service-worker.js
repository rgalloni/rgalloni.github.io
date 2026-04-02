const CACHE_NAME = 'istanbul-guide-spa-v16';
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
  "images/Bangkok-central-map.png",
  "images/Istanbul-City-Map.jpg",
  "images/ao_nang.jpg",
  "images/ayutthaya.jpg",
  "images/bioluminescence.jpg",
  "images/centralworld.jpg",
  "images/chengdu_pandas.jpg",
  "images/chengdu_peoples_park.jpg",
  "images/chinatown_bkk.jpg",
  "images/cnx_night_bazaar.jpg",
  "images/damnoen_saduak.jpg",
  "images/doi_inthanon.jpg",
  "images/doi_suthep.jpg",
  "images/elephant_nature_park.jpg",
  "images/emquartier.jpg",
  "images/erawan_shrine.jpg",
  "images/golden_mount.jpg",
  "images/grand_palace.jpg",
  "images/iconsiam.jpg",
  "images/jim_thompson.jpg",
  "images/lebua_tower.jpg",
  "images/loha_prasat.jpg",
  "images/lumpini_park.jpg",
  "images/maeklong.jpg",
  "images/mahanakhon.jpg",
  "images/mbk_center.jpg",
  "images/patong_beach.jpg",
  "images/phang_nga_bay.jpg",
  "images/phi_phi.jpg",
  "images/phuket_old_town.jpg",
  "images/phuket_town.jpg",
  "images/railay_beach.jpg",
  "images/rajadamnern.jpg",
  "images/siam_paragon.jpg",
  "images/terminal_21.jpg",
  "images/tiger_cave.jpg",
  "images/wat_arun.jpg",
  "images/wat_khaek.jpg",
  "images/wat_mahathat.jpg",
  "images/wat_mangkon.jpg",
  "images/wat_paknam.jpg",
  "images/wat_pho.jpg",
  "images/wat_phra_si_sanphet.jpg",
  "images/wat_traimit.jpg",
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
