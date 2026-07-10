/**
 * Graphiques Chart.js — page Statistiques
 */
(function () {
  'use strict';

  const data = window.STATISTIQUES_DATA || {};
  const periodeLabel = window.STATISTIQUES_PERIODE || '';

  const palette = [
    '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1',
    '#0dcaf0', '#fd7e14', '#20c997', '#6610f2', '#6c757d',
  ];

  const fmtFcfa = function (v) {
    if (v >= 1e9) return (v / 1e9).toFixed(1) + ' Md';
    if (v >= 1e6) return (v / 1e6).toFixed(1) + ' M';
    if (v >= 1e3) return (v / 1e3).toFixed(0) + ' k';
    return String(Math.round(v));
  };

  const commonOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14, font: { size: 11 } } },
      tooltip: {
        callbacks: {
          label: function (ctx) {
            const raw = ctx.raw;
            const val = typeof raw === 'object' && raw !== null ? raw.y ?? raw : raw;
            if (ctx.dataset && ctx.dataset._fcfa) {
              return ctx.dataset.label + ' : ' + Number(val).toLocaleString('fr-FR') + ' FCFA';
            }
            return ctx.dataset.label + ' : ' + val;
          },
        },
      },
    },
  };

  /* Évolution mensuelle */
  const evo = data.evolution || {};
  const elEvo = document.getElementById('chartEvolution');
  if (elEvo && evo.labels) {
    new Chart(elEvo, {
      type: 'bar',
      data: {
        labels: evo.labels,
        datasets: [
          { label: 'CA TTC', data: evo.ca || [], backgroundColor: 'rgba(13,110,253,0.75)', _fcfa: true },
          { label: 'Achats', data: evo.achats || [], backgroundColor: 'rgba(255,193,7,0.75)', _fcfa: true },
          { label: 'Dépenses', data: evo.depenses || [], backgroundColor: 'rgba(220,53,69,0.65)', _fcfa: true },
          {
            label: 'Marge brute',
            data: evo.marge || [],
            type: 'line',
            borderColor: '#198754',
            backgroundColor: 'rgba(25,135,84,0.1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            _fcfa: true,
          },
        ],
      },
      options: {
        ...commonOpts,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: fmtFcfa },
          },
        },
        plugins: {
          ...commonOpts.plugins,
          title: { display: false },
        },
      },
    });
  }

  /* CA par type client */
  const caType = data.ca_type_client || {};
  const elCa = document.getElementById('chartCaTypeClient');
  if (elCa && caType.labels && caType.labels.length) {
    new Chart(elCa, {
      type: 'doughnut',
      data: {
        labels: caType.labels,
        datasets: [{
          data: caType.data,
          backgroundColor: palette.slice(0, caType.labels.length),
          borderWidth: 2,
          _fcfa: true,
        }],
      },
      options: {
        ...commonOpts,
        cutout: '58%',
        plugins: {
          ...commonOpts.plugins,
          tooltip: {
            callbacks: {
              label: function (ctx) {
                const total = (caType.data || []).reduce(function (a, b) { return a + b; }, 0);
                const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                return ctx.label + ' : ' + Number(ctx.raw).toLocaleString('fr-FR') + ' FCFA (' + pct + ' %)';
              },
            },
          },
        },
      },
    });
  } else if (elCa) {
    elCa.parentElement.innerHTML = '<p class="text-muted small text-center mb-0">Pas de ventes par type client sur ' + periodeLabel + '.</p>';
  }

  /* Top produits */
  const topP = data.top_produits || {};
  const elTop = document.getElementById('chartTopProduits');
  if (elTop && topP.labels && topP.labels.length) {
    new Chart(elTop, {
      type: 'bar',
      data: {
        labels: topP.labels,
        datasets: [{
          label: 'Quantité vendue',
          data: topP.qty || [],
          backgroundColor: 'rgba(13,110,253,0.7)',
        }],
      },
      options: {
        indexAxis: 'y',
        ...commonOpts,
        scales: { x: { beginAtZero: true } },
      },
    });
  } else if (elTop) {
    elTop.parentElement.innerHTML = '<p class="text-muted small text-center mb-0">Aucun produit vendu sur ' + periodeLabel + '.</p>';
  }

  /* Dépenses par catégorie */
  const depCat = data.depenses_categorie || {};
  const elDep = document.getElementById('chartDepenses');
  if (elDep && depCat.labels && depCat.labels.length) {
    new Chart(elDep, {
      type: 'pie',
      data: {
        labels: depCat.labels,
        datasets: [{
          data: depCat.data,
          backgroundColor: palette.slice(0, depCat.labels.length),
          _fcfa: true,
        }],
      },
      options: { ...commonOpts, cutout: 0 },
    });
  } else if (elDep) {
    elDep.parentElement.innerHTML = '<p class="text-muted small text-center mb-0">Aucune dépense validée sur ' + periodeLabel + '.</p>';
  }

  /* Créances */
  const cre = data.creances || {};
  const elCre = document.getElementById('chartCreances');
  if (elCre && cre.labels) {
    new Chart(elCre, {
      type: 'bar',
      data: {
        labels: cre.labels,
        datasets: [{
          label: 'Montant impayé',
          data: cre.data || [],
          backgroundColor: ['#198754', '#ffc107', '#fd7e14', '#dc3545'],
          _fcfa: true,
        }],
      },
      options: {
        ...commonOpts,
        plugins: {
          ...commonOpts.plugins,
          tooltip: {
            callbacks: {
              afterLabel: function (ctx) {
                const counts = cre.counts || [];
                const n = counts[ctx.dataIndex];
                return n != null ? n + ' facture(s)' : '';
              },
              label: function (ctx) {
                return Number(ctx.raw).toLocaleString('fr-FR') + ' FCFA';
              },
            },
          },
        },
        scales: { y: { beginAtZero: true, ticks: { callback: fmtFcfa } } },
      },
    });
  }

  /* Commandes fournisseur */
  const cmd = data.commandes_statut || {};
  const elCmd = document.getElementById('chartCommandes');
  if (elCmd && cmd.labels && cmd.labels.length) {
    new Chart(elCmd, {
      type: 'doughnut',
      data: {
        labels: cmd.labels,
        datasets: [{
          data: cmd.data,
          backgroundColor: ['#0d6efd', '#ffc107', '#198754', '#6c757d'].slice(0, cmd.labels.length),
        }],
      },
      options: { ...commonOpts, cutout: '55%' },
    });
  } else if (elCmd) {
    elCmd.parentElement.innerHTML = '<p class="text-muted small text-center mb-0">Aucune commande fournisseur sur ' + periodeLabel + '.</p>';
  }
})();
