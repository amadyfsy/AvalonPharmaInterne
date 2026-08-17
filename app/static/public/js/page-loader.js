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

  function hideLoader() {
    var elapsed = Date.now() - shownAt;
    var wait = Math.max(0, MIN_VISIBLE_MS - elapsed);
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () {
      loader.classList.add('is-hidden');
      loader.setAttribute('aria-busy', 'false');
      loader.setAttribute('aria-hidden', 'true');
    }, wait);
  }

  function shouldInterceptLink(a, event) {
    if (!a || event.defaultPrevented) return false;
    if (event.button !== 0) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (a.target && a.target !== '_self') return false;
    if (a.hasAttribute('download')) return false;
    if (a.dataset.noLoader === '1') return false;
    var skipClass = 'js-facture-download js-facture-print js-bl-download js-bl-print js-facture-print-choice';
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
    var a = event.target.closest && event.target.closest('a[href]');
    if (shouldInterceptLink(a, event)) {
      showLoader();
    }
  }, true);

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form || form.tagName !== 'FORM') return;
    if (form.dataset.noLoader === '1') return;
    if (form.target && form.target !== '_self') return;
    showLoader();
  }, true);

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
