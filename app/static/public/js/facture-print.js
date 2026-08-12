(function () {
  var modalEl = document.getElementById('modalImprimerFacture');
  if (!modalEl) return;

  var modal = window.bootstrap && window.bootstrap.Modal
    ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
    : null;
  var pendingBaseUrl = '';
  var pendingMode = 'print'; // print | download
  var pendingDocType = 'facture'; // facture | bl
  var btnSeul = document.getElementById('btnFactureSeule');
  var btnAvecBl = document.getElementById('btnFactureAvecBl');
  var blNumEl = document.getElementById('modalImprimerBlNum');
  var titleEl = document.getElementById('modalImprimerFactureLabel');
  var descEl = document.getElementById('modalImprimerFactureDesc');
  var cachetWrap = document.getElementById('modalCachetWrap');
  var cachetCb = document.getElementById('modalAvecCachet');

  function setModalCopy(mode, docType) {
    var isBl = docType === 'bl';
    var isDl = mode === 'download';
    if (titleEl) {
      if (isBl) {
        titleEl.innerHTML = isDl
          ? '<i class="bi bi-download me-2 text-primary"></i>Télécharger le BL'
          : '<i class="bi bi-printer me-2 text-primary"></i>Imprimer le BL';
      } else {
        titleEl.innerHTML = isDl
          ? '<i class="bi bi-download me-2 text-primary"></i>Télécharger la facture'
          : '<i class="bi bi-printer me-2 text-primary"></i>Imprimer la facture';
      }
    }
    if (descEl) {
      if (isBl) {
        descEl.textContent = isDl
          ? 'Choisissez les options du PDF à télécharger.'
          : 'Choisissez les options du document à imprimer.';
      } else {
        descEl.textContent = isDl
          ? 'Choisissez le contenu du PDF à télécharger.'
          : 'Choisissez le contenu du document à imprimer.';
      }
    }
    if (btnSeul) {
      if (isBl) {
        btnSeul.innerHTML = '<i class="bi bi-file-earmark-text me-2"></i>'
          + (isDl ? 'Télécharger' : 'Continuer');
      } else {
        btnSeul.innerHTML = '<i class="bi bi-file-earmark-text me-2"></i>Facture seule';
      }
    }
  }

  function cachetParam() {
    if (!cachetWrap || cachetWrap.classList.contains('d-none') || !cachetCb) {
      return '0';
    }
    return cachetCb.checked ? '1' : '0';
  }

  function buildUrl(base, avecBl) {
    var sep = base.indexOf('?') >= 0 ? '&' : '?';
    var url = base + sep + 'avec_cachet=' + cachetParam();
    if (pendingDocType !== 'bl') {
      url += '&avec_bl=' + (avecBl ? '1' : '0');
    }
    return url;
  }

  function openUrl(avecBl) {
    if (!pendingBaseUrl) return;
    var url = buildUrl(pendingBaseUrl, avecBl);
    if (pendingMode === 'download') {
      window.location.href = url;
    } else {
      window.open(url, '_blank', 'noopener');
    }
    if (modal) modal.hide();
  }

  function prepareCachet(el) {
    var hasCachet = el.getAttribute('data-has-cachet') === '1';
    if (cachetWrap) {
      if (hasCachet) {
        cachetWrap.classList.remove('d-none');
        if (cachetCb) cachetCb.checked = true;
      } else {
        cachetWrap.classList.add('d-none');
      }
    }
  }

  function handleClick(el, mode) {
    var docType = el.getAttribute('data-doc-type') || 'facture';
    var hasBl = docType !== 'bl' && el.getAttribute('data-has-bl') === '1';
    var hasCachet = el.getAttribute('data-has-cachet') === '1';
    var baseUrl = el.getAttribute(mode === 'download' ? 'data-pdf-url' : 'data-print-url')
      || el.getAttribute('href');
    if (!baseUrl || baseUrl === '#') return;

    pendingMode = mode;
    pendingDocType = docType;
    setModalCopy(mode, docType);
    prepareCachet(el);

    // Toujours ouvrir la modale si BL ou cachet à choisir
    if (!hasBl && !hasCachet) {
      var url = buildUrl(baseUrl, false);
      if (mode === 'download') {
        window.location.href = url;
      } else {
        window.open(url, '_blank', 'noopener');
      }
      return;
    }

    pendingBaseUrl = baseUrl;
    var blNum = el.getAttribute('data-bl-num') || '';
    if (btnAvecBl) {
      if (hasBl) {
        btnAvecBl.classList.remove('d-none');
        if (blNumEl) blNumEl.textContent = blNum ? 'BL ' + blNum : '';
      } else {
        btnAvecBl.classList.add('d-none');
      }
    }
    if (modal) {
      modal.show();
    } else {
      var choix = hasBl
        ? window.confirm(
            'Inclure le bon de livraison dans le même document ?\n\nOK = Facture + BL\nAnnuler = Facture seule'
          )
        : false;
      openUrl(choix);
    }
  }

  document.querySelectorAll('.js-facture-print, .js-bl-print').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      handleClick(el, 'print');
    });
  });

  document.querySelectorAll('.js-facture-download, .js-bl-download').forEach(function (el) {
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
