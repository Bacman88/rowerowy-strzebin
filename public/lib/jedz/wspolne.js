// „Jedź” – wspólne: dane z innych skryptów, geometria, formatowanie liczb i czasu, ustawienia w telefonie (localStorage).
// Moduły ładowane po kolei (jedz.html): wspolne → graf → profil → manewry → jedz.js (interfejs); wspólna przestrzeń window.JZ.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const H = window.HUB, ODC = window.ODC || [], J = window.JEDZ || {trasy: [], rower: []}, TB = window.TABLICZKA, WYS = window.WYS || null;
  const $ = id => document.getElementById(id);
  const rad = Math.PI / 180, RZ = 6371000;
  const dist = (a, b) => { const x = (b[1] - a[1]) * rad * Math.cos((a[0] + b[0]) / 2 * rad), y = (b[0] - a[0]) * rad; return Math.hypot(x, y) * RZ; };
  const brg = (a, b) => (Math.atan2((b[1] - a[1]) * Math.cos(a[0] * rad), b[0] - a[0]) / rad + 360) % 360;
  const kat = (a, b) => ((a - b + 540) % 360) - 180;       // a względem b, -180..180 (+ = w prawo)
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const kmTxt = m => m < 950 ? (Math.round(m / 10) * 10) + ' m' : (m / 1000).toFixed(m < 9950 ? 1 : 0).replace('.', ',') + ' km';
  const czasTxt = sek => { const t = Math.max(1, Math.round(sek / 60)); return t < 60 ? '~' + t + ' min' : '~' + Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0') + ' h'; };
  const godz = sek => { const d = new Date(Date.now() + sek * 1000); return d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0'); };
  const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
  const LS = {get(k, d) { try { const v = localStorage.getItem('jedz.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
              set(k, v) { try { localStorage.setItem('jedz.' + k, JSON.stringify(v)); } catch (e) {} }};
  Object.assign(JZ, {H, ODC, J, TB, WYS, $, rad, RZ, dist, brg, kat, esc, kmTxt, czasTxt, godz, norm, LS});
})();
