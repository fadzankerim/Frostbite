// Početna stranica: brojači koji "odbrojavaju" kad dođu u vidno polje.
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var nums = document.querySelectorAll('.num[data-count]');
  if (reduce || !nums.length || !('IntersectionObserver' in window)) return;

  var fmt = function (n) { return n.toLocaleString('bs-BA'); };
  nums.forEach(function (el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (!isFinite(target) || target <= 0) return;
    var io = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      el.textContent = '0';                 // tek kad animacija krene; inače ostaje stvarni broj
      var start = null, dur = 1400;
      var step = function (ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt(Math.round(target * eased));
        if (p < 1) window.requestAnimationFrame(step);
      };
      window.requestAnimationFrame(step);
    }, { threshold: 0.4 });
    io.observe(el);
  });
})();
