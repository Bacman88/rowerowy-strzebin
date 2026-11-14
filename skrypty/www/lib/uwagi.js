// „Zgłoś błąd / sugestię” – wspólne okienko dla strony głównej i nawigacji „Jedź” (także w aplikacji na Androida).
// Użycie: UWAGI.otworz({gdzie: 'strona' | 'nawigacja' | 'aplikacja', trasa: {start, cel, celN, tryb, rower, km} | null})
// Wysyła do api/uwagi.php (adres: window.UWAGI_API, w aplikacji – pełny adres strony). Trasa idzie tylko po zaznaczeniu pola.
(() => {
  'use strict';
  const CSS = `.uw-tlo{position:fixed;inset:0;z-index:5000;background:rgba(20,30,25,.45);display:flex;align-items:flex-end;justify-content:center}
.uw-tlo[hidden]{display:none}
.uw{background:#fffdf8;color:#1d2a23;width:100%;max-width:520px;max-height:92vh;overflow:auto;border-radius:20px 20px 0 0;padding:18px 18px calc(18px + env(safe-area-inset-bottom));font:15px/1.45 Inter,system-ui,sans-serif;box-shadow:0 -4px 24px rgba(0,0,0,.2)}
@media (min-width:600px){.uw-tlo{align-items:center}.uw{border-radius:18px}}
.uw h2{margin:0 0 4px;font-size:20px}.uw .uw-m{color:#56665c;font-size:13px}
.uw .uw-r{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:#efe9da;border-radius:12px;padding:4px;margin:12px 0}
.uw .uw-r label{text-align:center;padding:8px;border-radius:9px;cursor:pointer;font-weight:700}
.uw .uw-r input{position:absolute;opacity:0;pointer-events:none}.uw .uw-r label:has(input:checked){background:#fff;color:#00737e;box-shadow:0 1px 3px rgba(0,0,0,.12)}
.uw textarea,.uw input[type=text]{width:100%;box-sizing:border-box;font:inherit;padding:9px 11px;border:1px solid #e3dccb;border-radius:10px;background:#fff;color:inherit}
.uw textarea{min-height:110px;resize:vertical}.uw .uw-f{display:block;font-size:13px;color:#56665c;margin:10px 0 4px}
.uw .uw-c{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;margin:8px 0}.uw .uw-c input{margin-top:3px;accent-color:#00737e}
.uw .uw-b{display:flex;gap:8px;margin-top:14px}.uw button{font:inherit;font-weight:700;border-radius:12px;padding:11px 16px;cursor:pointer;border:1px solid #e3dccb;background:#fff;color:#1d2a23}
.uw button.uw-ok{flex:1;background:#00737e;border-color:#00737e;color:#fff}.uw button:disabled{opacity:.5}
.uw .uw-msg{margin-top:10px;font-size:14px}.uw .uw-msg.ok{color:#1b5e20}.uw .uw-msg.err{color:#b00020}
.uw .uw-hp{position:absolute;left:-9999px}`;
  let el = null, ctx = {};
  const $ = s => el.querySelector(s);
  function zbuduj() {
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    el = document.createElement('div'); el.className = 'uw-tlo'; el.hidden = true;
    el.innerHTML = `<div class="uw" role="dialog" aria-modal="true" aria-labelledby="uw-t">
      <h2 id="uw-t">Zgłoś błąd albo sugestię</h2><div class="uw-m">Trafia prosto do autora projektu. Każda uwaga pomaga – szczególnie z jazdy w terenie.</div>
      <div class="uw-r" role="radiogroup"><label><input type="radio" name="uw-rodzaj" value="blad" checked>Coś nie działa</label><label><input type="radio" name="uw-rodzaj" value="sugestia">Mam pomysł</label></div>
      <label class="uw-f" for="uw-tresc">Co się stało albo co zmienić?</label>
      <textarea id="uw-tresc" maxlength="3000" placeholder="Np. przy kościele w Koszęcinie kazało skręcić w lewo, a tam nie ma przejazdu…"></textarea>
      <label class="uw-c" id="uw-tr-w" hidden><input type="checkbox" id="uw-tr"><span><b>Dołącz tę trasę</b> (start, cel, rodzaj trasy i roweru) – pomoże znaleźć błąd. Bez zaznaczenia nie wysyłamy żadnej lokalizacji.</span></label>
      <label class="uw-f" for="uw-nick">Imię lub nick (nieobowiązkowo)</label><input type="text" id="uw-nick" maxlength="60" autocomplete="nickname">
      <label class="uw-f" for="uw-kontakt">E-mail lub telefon – jeśli mamy odpisać (nieobowiązkowo)</label><input type="text" id="uw-kontakt" maxlength="120" autocomplete="email">
      <label class="uw-c" id="uw-zg-w" hidden><input type="checkbox" id="uw-zgoda"><span>Zgadzam się na kontakt w sprawie tego zgłoszenia (dane widzi tylko administrator, kasujemy je najpóźniej po roku).</span></label>
      <input type="text" class="uw-hp" id="uw-www" tabindex="-1" autocomplete="off" aria-hidden="true">
      <div class="uw-m" style="margin-top:8px">Dołączymy też typ urządzenia i przeglądarki. <a href="${(window.UWAGI_BAZA || './')}polityka-prywatnosci.html" target="_blank" rel="noopener" style="color:#00737e">Prywatność</a></div>
      <div class="uw-b"><button type="button" id="uw-anuluj">Zamknij</button><button type="button" class="uw-ok" id="uw-wyslij">Wyślij</button></div>
      <div class="uw-msg" id="uw-msg" role="status"></div></div>`;
    document.body.appendChild(el);
    el.addEventListener('click', e => { if (e.target === el) zamknij(); });
    $('#uw-anuluj').onclick = zamknij;
    $('#uw-kontakt').oninput = () => { $('#uw-zg-w').hidden = !$('#uw-kontakt').value.trim(); };
    $('#uw-wyslij').onclick = wyslij;
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !el.hidden) zamknij(); });
    try { $('#uw-nick').value = localStorage.getItem('hub_nick') || ''; } catch (e) {}
  }
  function otworz(o) {
    if (!el) zbuduj();
    ctx = o || {};
    $('#uw-tr-w').hidden = !ctx.trasa; $('#uw-tr').checked = false;
    $('#uw-msg').textContent = ''; $('#uw-msg').className = 'uw-msg'; $('#uw-wyslij').disabled = false;
    el.hidden = false; setTimeout(() => $('#uw-tresc').focus(), 50);
  }
  function zamknij() { if (el) el.hidden = true; }
  async function wyslij() {
    const m = $('#uw-msg'), tresc = $('#uw-tresc').value.trim(), kontakt = $('#uw-kontakt').value.trim();
    const blad = t => { m.textContent = t; m.className = 'uw-msg err'; };
    if (tresc.length < 5) return blad('Opisz krótko, o co chodzi.');
    if (kontakt && !$('#uw-zgoda').checked) return blad('Zaznacz zgodę na kontakt albo zostaw to pole puste.');
    const body = {rodzaj: el.querySelector('input[name=uw-rodzaj]:checked').value, gdzie: ctx.gdzie || 'strona', tresc, nick: $('#uw-nick').value.trim(), kontakt,
      zgoda: $('#uw-zgoda').checked, www: $('#uw-www').value,
      info: {urzadzenie: navigator.userAgent, ekran: `${screen.width}×${screen.height}`, adres: location.pathname + location.hash, wersja: ctx.wersja || '',
        trasa: ctx.trasa && $('#uw-tr').checked ? ctx.trasa : null}};
    $('#uw-wyslij').disabled = true; m.textContent = 'Wysyłam…'; m.className = 'uw-msg';
    try {
      const r = await fetch(window.UWAGI_API || 'api/uwagi.php', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.ok) throw new Error(j.blad || 'Nie udało się wysłać – sprawdź internet i spróbuj jeszcze raz.');
      m.textContent = 'Dziękujemy! Zgłoszenie dotarło.'; m.className = 'uw-msg ok';
      $('#uw-tresc').value = ''; try { if (body.nick) localStorage.setItem('hub_nick', body.nick); } catch (e) {}
      setTimeout(zamknij, 1800);
    } catch (e) { blad(e.message === 'Failed to fetch' ? 'Brak połączenia z internetem – spróbuj, gdy będzie zasięg.' : e.message); $('#uw-wyslij').disabled = false; }
  }
  window.UWAGI = {otworz, zamknij};
})();
