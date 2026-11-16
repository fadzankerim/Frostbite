// Kopiranje teksta (npr. GPS koordinata) u međuspremnik.
(function () {
  'use strict';
  document.querySelectorAll('[data-target]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var src = document.getElementById(btn.getAttribute('data-target'));
      if (!src || !navigator.clipboard) return;
      navigator.clipboard.writeText(src.textContent.trim()).then(function () {
        var label = btn.querySelector('span');
        if (!label) return;
        var old = label.textContent;
        label.textContent = 'Kopirano';
        btn.classList.add('copied');
        setTimeout(function () { label.textContent = old; btn.classList.remove('copied'); }, 1800);
      });
    });
  });
})();
