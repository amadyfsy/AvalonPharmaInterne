/**
 * Pied de page type Word : lorsque le document tient sur une seule feuille, le tableau
 * prend la hauteur utile A4 (marges @page) et l’espaceur se dilate pour pousser le tfoot
 * tout en bas. Si le corps dépasse une page, on annule la hauteur min et l’espaceur = 0
 * pour laisser le navigateur paginer (thead/tfoot répétés).
 *
 * Constantes = @page dans erp-print-document.css (A4, 12 mm haut, 5 cm bas).
 */
(function () {
  const MM_TO_PX = 96 / 25.4;
  const PAGE_HEIGHT_MM = 297;
  const PAGE_MARGIN_TOP_MM = 12;
  const PAGE_MARGIN_BOTTOM_MM = 50; /* 5 cm */

  const CONTENT_BOX_MM =
    PAGE_HEIGHT_MM - PAGE_MARGIN_TOP_MM - PAGE_MARGIN_BOTTOM_MM;

  function contentAreaHeightPx() {
    return CONTENT_BOX_MM * MM_TO_PX;
  }

  function adjustSheet(sheet) {
    const inner = sheet.querySelector('.erp-running-body-inner');
    const spacer = sheet.querySelector('.erp-print-page-spacer');
    const body = sheet.querySelector('.erp-running-body');
    if (!inner || !spacer || !body) return;

    const thead = sheet.querySelector('thead');
    const tfoot = sheet.querySelector('tfoot');
    const headerH = thead ? thead.offsetHeight : 0;
    const footerH = tfoot ? tfoot.offsetHeight : 0;

    const boxH = contentAreaHeightPx();
    const innerH = inner.offsetHeight;
    const availableForBody = boxH - headerH - footerH;

    if (innerH <= availableForBody) {
      /* Une page suffit : tableau = hauteur feuille → pied en bas (style Word) */
      sheet.classList.add('erp-print-sheet--one-page');
      sheet.style.minHeight = CONTENT_BOX_MM + 'mm';
      body.style.minHeight = '100%';
      spacer.style.height = '';
      spacer.style.flex = '1 1 auto';
    } else {
      sheet.classList.remove('erp-print-sheet--one-page');
      sheet.style.minHeight = '';
      body.style.minHeight = '';
      spacer.style.flex = '';
      spacer.style.height = '0px';
    }
  }

  function adjustAll() {
    document.querySelectorAll('.erp-print-sheet').forEach(adjustSheet);
  }

  function resetLayout() {
    document.querySelectorAll('.erp-print-page-spacer').forEach(function (el) {
      el.style.height = '';
      el.style.flex = '';
    });
    document.querySelectorAll('.erp-running-body').forEach(function (el) {
      el.style.minHeight = '';
    });
    document.querySelectorAll('.erp-print-sheet').forEach(function (el) {
      el.style.minHeight = '';
      el.classList.remove('erp-print-sheet--one-page');
    });
  }

  window.addEventListener('beforeprint', function () {
    requestAnimationFrame(function () {
      requestAnimationFrame(adjustAll);
    });
  });
  window.addEventListener('afterprint', resetLayout);
})();
