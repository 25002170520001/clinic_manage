from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def manifest_view(request):
    return JsonResponse(
        {
            "name": "Family Health Care",
            "short_name": "FHC",
            "description": "Family Health Care clinic management system",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f4f7f5",
            "theme_color": "#2f8f67",
            "icons": [
                {
                    "src": "/static/images/clinic-logo.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
                {
                    "src": "/static/images/clinic-logo.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
            ],
        }
    )


@require_GET
def service_worker_view(request):
    js = """
const CACHE_NAME = "fhc-cache-v2";
const OFFLINE_URL = "/offline/";
const ASSETS = [
  "/",
  "/offline/",
  "/static/css/site.css",
  "/static/css/mobile-app.css",
  "/static/images/clinic-logo.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((key) => (key !== CACHE_NAME ? caches.delete(key) : Promise.resolve())))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isStaticAsset = isSameOrigin && url.pathname.startsWith("/static/");
  const isAuthOrDynamicPage =
    isSameOrigin && (
      url.pathname.startsWith("/login") ||
      url.pathname.startsWith("/signup") ||
      url.pathname.startsWith("/dashboard") ||
      url.pathname.startsWith("/doctor") ||
      url.pathname.startsWith("/reception") ||
      url.pathname.startsWith("/billing") ||
      url.pathname.startsWith("/patient")
    );

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  if (isAuthOrDynamicPage) {
    event.respondWith(fetch(req));
    return;
  }

  if (!isStaticAsset) {
    event.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }

  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((networkRes) => {
          const copy = networkRes.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return networkRes;
        })
        .catch(() => caches.match("/static/images/clinic-logo.png"));
    })
  );
});
""".strip()
    return HttpResponse(js, content_type="application/javascript")
