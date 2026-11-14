"""Widoczność w wyszukiwarkach: lepsze tytuły i opisy, adresy kanoniczne, Open Graph na podstronach, dane strukturalne
(JSON-LD: strona, lista tras, aplikacja „Jedź”), robots.txt i sitemap.xml. Uruchamiane po strona.py (rebuild.sh).
Weryfikacja Google Search Console / Bing: kody w seo_config.json ({"google": "...", "bing": "..."}) – trafiają do <head> strony głównej
(kody weryfikacyjne są jawne z założenia, mogą być w repozytorium).
Użycie: python3 seo.py ../out/strona
"""
import datetime, html, json, os, sys
OUT = sys.argv[1]
URL = "https://rowerowy-strzebin.smart-ant.pl/"
DZIS = datetime.date.today().isoformat()
CFG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "seo_config.json"))) if os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "seo_config.json")) else {}
e = lambda s: html.escape(s, quote=True)
dj = open(f"{OUT}/data.js").read(); H = json.loads(dj[dj.index("=") + 1:].strip().rstrip(";"))
trasy = [r for r in H["routes"] if not r.get("alt")]

def wstaw(plik, glowa, tytul=None, opis=None):
    p = f"{OUT}/{plik}"; s = open(p).read()
    if 'rel="canonical"' in s: return                     # już przetworzone (ponowne uruchomienie)
    if tytul: s = s[:s.index("<title>") + 7] + e(tytul) + s[s.index("</title>"):]
    if opis and 'name="description"' in s:
        i = s.index('name="description"'); a = s.index('content="', i) + 9; b = s.index('"', a); s = s[:a] + e(opis) + s[b:]
    s = s.replace("</head>", glowa + "\n</head>", 1)
    open(p, "w").write(s)

def og(sciezka, tytul, opis):
    return (f'<link rel="canonical" href="{URL}{sciezka}">\n<meta property="og:type" content="website">\n<meta property="og:site_name" content="HUB rowerowy Strzebiń">\n'
            f'<meta property="og:locale" content="pl_PL">\n<meta property="og:url" content="{URL}{sciezka}">\n<meta property="og:title" content="{e(tytul)}">\n'
            f'<meta property="og:description" content="{e(opis)}">\n<meta property="og:image" content="{URL}og.jpg">\n<meta name="twitter:card" content="summary_large_image">')
ld = lambda d: '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "</script>"

# --- strona główna
T0 = "HUB rowerowy Strzebiń – trasy rowerowe, drogowskazy i mapa dróg w gminie Koszęcin"
D0 = (f"Trasy rowerowe wokół Strzebinia, Koszęcina, Kalet i Boronowa: {len(trasy)} tras z plikami GPX, drogowskazy rowerowe, mapa stanu dróg "
      "uzupełniana przez mieszkańców i darmowa nawigacja rowerowa „Jedź”. Dojazd do Leśnej Rajzy i Liswarciańskiego Szlaku Rowerowego.")
glowa = [f'<link rel="canonical" href="{URL}">', '<meta name="robots" content="index,follow,max-image-preview:large">']
if CFG.get("google"): glowa.append(f'<meta name="google-site-verification" content="{e(CFG["google"])}">')
if CFG.get("bing"): glowa.append(f'<meta name="msvalidate.01" content="{e(CFG["bing"])}">')
glowa.append(ld({"@context": "https://schema.org", "@graph": [
    {"@type": "WebSite", "@id": URL + "#strona", "url": URL, "name": "HUB rowerowy Strzebiń", "inLanguage": "pl",
     "description": D0, "about": {"@type": "Place", "name": "Strzebiń, gmina Koszęcin", "address": {"@type": "PostalAddress", "addressLocality": "Strzebiń",
     "addressRegion": "śląskie", "addressCountry": "PL"}, "geo": {"@type": "GeoCoordinates", "latitude": 50.616, "longitude": 18.897}}},
    {"@type": "ItemList", "name": "Trasy rowerowe HUB Strzebiń", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "item": {"@type": "TouristTrip", "name": f"Trasa {r['id']}: {r['name']}",
         "description": f"Trasa rowerowa {str(r['km']).replace('.', ',')} km" + (f" – {r['sub']}" if r.get("sub") else "") + ". Plik GPX do pobrania.",
         "url": URL + "#trasy", "touristType": "rowerzyści"}} for i, r in enumerate(trasy)]},
]}))
wstaw("index.html", "\n".join(glowa), T0, D0)
s = open(f"{OUT}/index.html").read()
s = s.replace('<meta property="og:title" content="HUB rowerowy Strzebiń – drogowskazy, trasy i wspólna mapa dróg">',
              '<meta property="og:title" content="HUB rowerowy Strzebiń – trasy rowerowe, drogowskazy i mapa dróg">', 1)
open(f"{OUT}/index.html", "w").write(s)

# --- podstrony
TJ = "Jedź – darmowa nawigacja rowerowa po Strzebiniu, Koszęcinie i okolicy (beta)"
DJ = ("Nawigacja rowerowa w telefonie po drogach i trasach HUB rowerowego Strzebiń: tryby Bezpieczna, Najkrótsza i Szosowa, profil wysokości, "
      "czas jazdy dla Twojego roweru, mapa offline i głos. Bez konta i bez śledzenia – działa w przeglądarce i na Androidzie.")
wstaw("jedz.html", og("jedz.html", TJ, DJ) + "\n" + ld({"@context": "https://schema.org", "@type": "WebApplication", "name": "Jedź – HUB rowerowy Strzebiń",
      "url": URL + "jedz.html", "applicationCategory": "TravelApplication", "operatingSystem": "Android, przeglądarka", "inLanguage": "pl",
      "description": DJ, "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "PLN"},
      "downloadUrl": "https://github.com/Bacman88/rowerowy-strzebin/releases/latest/download/jedz-hub-strzebin.apk",
      "author": {"@type": "Organization", "name": "Bartosz Maniura Smart Ant", "url": "https://smart-ant.pl"}}), TJ, DJ)
TT = "Pobierz nawigację rowerową „Jedź” na telefon (Android) | HUB rowerowy Strzebiń"
DT = "Darmowa nawigacja rowerowa „Jedź” po Strzebiniu i okolicy na Androida: pobierz od razu albo zapisz się do testów w Google Play."
wstaw("testuj.html", og("testuj.html", TT, DT), TT, DT)
TP = "Polityka prywatności – HUB rowerowy Strzebiń i nawigacja „Jedź”"
wstaw("polityka-prywatnosci.html", og("polityka-prywatnosci.html", TP, "Jakie dane zbiera strona HUB rowerowy Strzebiń i nawigacja „Jedź”, po co i jak długo je przechowujemy."))
# narzędzia i przekierowania – poza wynikami wyszukiwania
for f in ["generator.html", "stan.html"]:
    p = f"{OUT}/{f}"
    if os.path.exists(p):
        s = open(p).read()
        if 'name="robots"' not in s: s = s.replace("</head>", '<meta name="robots" content="noindex,follow">\n</head>', 1)
        open(p, "w").write(s)

# --- robots.txt i sitemap.xml
open(f"{OUT}/robots.txt", "w").write(f"User-agent: *\nDisallow: /admin/\nDisallow: /api/\nAllow: /\n\nSitemap: {URL}sitemap.xml\n")
strony = [("", "1.0", "weekly"), ("jedz.html", "0.9", "weekly"), ("testuj.html", "0.6", "monthly"), ("polityka-prywatnosci.html", "0.2", "yearly")]
pdfy = sorted(f for f in os.listdir(f"{OUT}/pdf") if f.endswith(".pdf")) if os.path.isdir(f"{OUT}/pdf") else []
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
xml += [f"  <url><loc>{URL}{p}</loc><lastmod>{DZIS}</lastmod><changefreq>{c}</changefreq><priority>{pr}</priority></url>" for p, pr, c in strony]
xml += [f"  <url><loc>{URL}pdf/{f}</loc><lastmod>{DZIS}</lastmod><priority>0.4</priority></url>" for f in pdfy]
xml.append("</urlset>")
open(f"{OUT}/sitemap.xml", "w").write("\n".join(xml) + "\n")
print(f"seo: tytuły, opisy, JSON-LD ({len(trasy)} tras), robots.txt, sitemap.xml ({len(strony) + len(pdfy)} adresów)"
      + (", weryfikacja Google" if CFG.get("google") else ", bez kodu weryfikacji Google (seo_config.json)"))
