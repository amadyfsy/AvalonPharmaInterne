(function () {
  var modalEl = document.getElementById('modalImprimerFacture');
  if (!modalEl) return;

  var modal = window.bootstrap && window.bootstrap.Modal
    ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
    : null;
  var pendingBaseUrl = '';
  var pendingMode = 'print'; // print | download
  var btnAvecBl = document.getElementById('btnFactureAvecBl');
  var blNumEl = document.getElementById('modalImprimerBlNum');
  var titleEl = document.getElementById('modalImprimerFactureLabel');
  var descEl = document.getElementById('modalImprimerFactureDesc');

  function setModalCopy(mode) {
    if (titleEl) {
      titleEl.innerHTML = mode === 'download'
        ? '<i class="bi bi-download me-2 text-primary"></i>Télécharger la facture'
        : '<i class="bi bi-printer me-2 text-primary"></i>Imprimer la facture';
    }
    if (descEl) {
      descEl.textContent = mode === 'download'
        ? 'Choisissez le contenu du PDF à télécharger.'
        : 'Choisissez le contenu du document à imprimer.';
    }
  }

  function openUrl(avecBl) {
    if (!pendingBaseUrl) return;
    var sep = pendingBaseUrl.indexOf('?') >= 0 ? '&' : '?';
    var url = pendingBaseUrl + sep + 'avec_bl=' + (avecBl ? '1' : '0');
    if (pendingMode === 'download') {
      // Navigation directe = téléchargement (Content-Disposition: attachment)
      window.location.href = url;
    } else {
      window.open(url, '_blank', 'noopener');
    }
    if (modal) modal.hide();
  }

  function handleClick(el, mode) {
    var hasBl = el.getAttribute('data-has-bl') === '1';
    var baseUrl = el.getAttribute(mode === 'download' ? 'data-pdf-url' : 'data-print-url')
      || el.getAttribute('href');
    if (!baseUrl || baseUrl === '#') return;

    pendingMode = mode;
    setModalCopy(mode);

    if (!hasBl) {
      if (mode === 'download') {
        window.location.href = baseUrl.indexOf('avec_bl=') >= 0
          ? baseUrl
          : baseUrl + (baseUrl.indexOf('?') >= 0 ? '&' : '?') + 'avec_bl=0';
      } else {
        window.open(baseUrl, '_blank', 'noopener');
      }
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
      openUrl(choix);
    }
  }

  document.querySelectorAll('.js-facture-print').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      handleClick(el, 'print');
    });
  });

  document.querySelectorAll('.js-facture-download').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      handleClick(el, 'download');
    });
  });

  document.querySelectorAll('.js-facture-print-choice').forEach(function (btn) {
    btn.addEventListener('click', function () {
      openUrl(btn.getAttribute('data-avec-bl') === '1');
    });
  });
})();
