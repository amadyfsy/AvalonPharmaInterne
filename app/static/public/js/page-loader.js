/**
 * Overlay de chargement avec logo Avalon (navigation + chargement initial).
 */
(function () {
  var loader = document.getElementById('pageLoader');
  if (!loader) return;

  var hideTimer = null;
  var MIN_VISIBLE_MS = 280;
  var shownAt = Date.now();

  function showLoader() {
    shownAt = Date.now();
    loader.classList.remove('is-hidden');
    loader.setAttribute('aria-busy', 'true');
    loader.setAttribute('aria-hidden', 'false');
  }

  function hideLoader(immediate) {
    clearTimeout(hideTimer);
    if (immediate) {
      loader.classList.add('is-hidden');
      loader.setAttribute('aria-busy', 'false');
      loader.setAttribute('aria-hidden', 'true');
      return;
    }
    var elapsed = Date.now() - shownAt;
    var wait = Math.max(0, MIN_VISIBLE_MS - elapsed);
    hideTimer = setTimeout(function () {
      loader.classList.add('is-hidden');
      loader.setAttribute('aria-busy', 'false');
      loader.setAttribute('aria-hidden', 'true');
    }, wait);
  }

  // Rendre accessible globalement pour les scripts AJAX si besoin
  window.showPageLoader = showLoader;
  window.hidePageLoader = hideLoader;

  function shouldInterceptLink(a, event) {
    if (!a || event.defaultPrevented) return false;
    if (event.button !== 0) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (a.target && a.target !== '_self') return false;
    if (a.hasAttribute('download')) return false;

    // Éléments explicitement marqués ou enfants d'éléments marqués sans loader
    if (a.dataset.noLoader === '1' || (a.closest && a.closest('[data-no-loader="1"]'))) return false;

    // Pagination ou recherche en direct (AJAX partiel)
    if (a.classList.contains('js-factures-page') || a.hasAttribute('data-factures-reset')) return false;
    if (a.closest && (a.closest('#facturesLiveRoot') || a.closest('[data-partial-root]') || a.closest('[data-live-search]'))) {
      return false;
    }

    // Contrôles Bootstrap (modals, dropdowns, onglets) et boutons JS
    if (a.hasAttribute('data-bs-toggle') || a.hasAttribute('data-bs-target')) return false;
    if (a.closest && a.closest('[data-bs-toggle]')) return false;
    if (a.getAttribute('role') === 'button' || a.getAttribute('role') === 'tab') return false;
    if (a.classList.contains('btn-apercu-justificatif') || (a.closest && a.closest('.btn-apercu-justificatif'))) return false;

    var skipClass = 'js-facture-download js-facture-print js-bl-download js-bl-print js-facture-print-choice js-factures-page btn-apercu-justificatif';
    if (a.className && skipClass.split(' ').some(function (c) { return a.classList.contains(c); })) {
      return false;
    }
    var href = a.getAttribute('href');
    if (!href || href === '#' || href.charAt(0) === '#') return false;
    if (href.indexOf('javascript:') === 0 || href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) {
      return false;
    }
    try {
      var url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return false;
      if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
        return false;
      }
      // PDF / impression : le fichier se télécharge sans quitter la page — ne pas bloquer l’UI.
      if (/\/pdf(\/|$)/.test(url.pathname) || /\/imprimer(\/|$)/.test(url.pathname)) {
        return false;
      }
    } catch (e) {
      return false;
    }
    return true;
  }

  document.addEventListener('click', function (event) {
    if (event.defaultPrevented) return;
    var a = event.target.closest && event.target.closest('a[href]');
    if (shouldInterceptLink(a, event)) {
      showLoader();
    }
  }, false);

  document.addEventListener('submit', function (event) {
    if (event.defaultPrevented) return;
    var form = event.target;
    if (!form || form.tagName !== 'FORM') return;
    if (form.dataset.noLoader === '1' || form.dataset.liveSearch === '1') return;
    if (form.target && form.target !== '_self') return;
    showLoader();
  }, false);

  window.addEventListener('pageshow', function (event) {
    if (event.persisted) hideLoader();
  });

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    hideLoader();
  } else {
    document.addEventListener('DOMContentLoaded', hideLoader);
    window.addEventListener('load', hideLoader);
    setTimeout(hideLoader, 4000);
  }
})();
