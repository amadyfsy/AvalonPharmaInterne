(function () {
  var modalEl = document.getElementById('modalImprimerFacture');
  if (!modalEl) return;

  var modal = window.bootstrap && window.bootstrap.Modal
    ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
    : null;
  var pendingBaseUrl = '';
  var btnAvecBl = document.getElementById('btnFactureAvecBl');
  var blNumEl = document.getElementById('modalImprimerBlNum');

  function openPrintUrl(avecBl) {
    if (!pendingBaseUrl) return;
    var sep = pendingBaseUrl.indexOf('?') >= 0 ? '&' : '?';
    var url = pendingBaseUrl + sep + 'avec_bl=' + (avecBl ? '1' : '0');
    window.open(url, '_blank', 'noopener');
    if (modal) modal.hide();
  }

  document.querySelectorAll('.js-facture-print').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var hasBl = el.getAttribute('data-has-bl') === '1';
      var baseUrl = el.getAttribute('data-print-url') || el.getAttribute('href');
      if (!baseUrl || baseUrl === '#') return;

      if (!hasBl) {
        window.open(baseUrl, '_blank', 'noopener');
        return;
      }

      pendingBaseUrl = baseUrl;
      var blNum = el.getAttribute('data-bl-num') || '';
      if (btnAvecBl) {
        btnAvecBl.classList.remove('d-none');
        if (blNumEl) blNumEl.textContent = blNum ? 'BL ' + blNum : '';
      }
      if (modal) {
        modal.show();
      } else {
        var choix = window.confirm(
          'Inclure le bon de livraison dans le même document ?\n\nOK = Facture + BL\nAnnuler = Facture seule'
        );
        openPrintUrl(choix);
      }
    });
  });

  document.querySelectorAll('.js-facture-print-choice').forEach(function (btn) {
    btn.addEventListener('click', function () {
      openPrintUrl(btn.getAttribute('data-avec-bl') === '1');
    });
  });
})();
