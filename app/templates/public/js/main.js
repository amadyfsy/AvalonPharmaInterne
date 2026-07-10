/**
 * ERP Medical Dashboard - Main JavaScript
 * Vanilla JS - No Framework
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // Sidebar Toggle (Mobile)
    // ==========================================
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const openSidebarBtn = document.getElementById('openSidebar');
    const closeSidebarBtn = document.getElementById('closeSidebar');

    function openSidebar() {
        sidebar.classList.add('active');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (openSidebarBtn) {
        openSidebarBtn.addEventListener('click', openSidebar);
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener('click', closeSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    // Close sidebar on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('active')) {
            closeSidebar();
        }
    });

    // ==========================================
    // Active Nav Link
    // ==========================================
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            // Remove active class from all links
            navLinks.forEach(function(l) {
                l.classList.remove('active');
            });
            // Add active class to clicked link
            this.classList.add('active');

            // Close sidebar on mobile after click
            if (window.innerWidth < 992) {
                closeSidebar();
            }
        });
    });

    // ==========================================
    // Animate KPI Values on Load
    // ==========================================
    function animateValue(element, start, end, duration) {
        let startTimestamp = null;
        const step = function(timestamp) {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = value.toLocaleString('fr-FR') + ' FCFA';
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    // Animate KPI values
    const kpiValues = document.querySelectorAll('.kpi-value');
    kpiValues.forEach(function(kpi) {
        const text = kpi.textContent;
        const match = text.match(/[\d\s]+/);
        if (match) {
            const value = parseInt(match[0].replace(/\s/g, ''));
            if (!isNaN(value)) {
                kpi.textContent = '0 FCFA';
                setTimeout(function() {
                    animateValue(kpi, 0, value, 1500);
                }, 300);
            }
        }
    });

    // ==========================================
    // Chart Bars Animation on Scroll
    // ==========================================
    const chartBars = document.querySelectorAll('.chart-bar');
    
    function animateOnScroll() {
        chartBars.forEach(function(bar, index) {
            const rect = bar.getBoundingClientRect();
            if (rect.top < window.innerHeight - 50) {
                setTimeout(function() {
                    bar.style.animation = 'growUp 0.8s ease-out forwards';
                }, index * 50);
            }
        });
    }

    // Initial check
    animateOnScroll();
    
    // Listen for scroll
    window.addEventListener('scroll', animateOnScroll);

    // ==========================================
    // Tooltips (Simple)
    // ==========================================
    const tooltipElements = document.querySelectorAll('[title]');
    
    tooltipElements.forEach(function(el) {
        const title = el.getAttribute('title');
        if (title) {
            el.setAttribute('data-tooltip', title);
            el.removeAttribute('title');
            
            el.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'custom-tooltip';
                tooltip.textContent = this.getAttribute('data-tooltip');
                tooltip.style.cssText = `
                    position: fixed;
                    background: #333;
                    color: #fff;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    z-index: 9999;
                    pointer-events: none;
                `;
                document.body.appendChild(tooltip);
                
                const rect = this.getBoundingClientRect();
                tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
            });
            
            el.addEventListener('mouseleave', function() {
                const tooltips = document.querySelectorAll('.custom-tooltip');
                tooltips.forEach(function(t) {
                    t.remove();
                });
            });
        }
    });

    // Barre de recherche : GET /recherche (voir _medigest_header.html)

    // ==========================================
    // User Menu Dropdown (Simple)
    // ==========================================
    const userMenu = document.querySelector('.user-menu');
    // Ne pas interférer avec le menu Bootstrap (header MediGest)
    if (userMenu && userMenu.getAttribute('data-bs-toggle') !== 'dropdown') {
        userMenu.addEventListener('click', function() {
            alert('Menu utilisateur - Fonctionnalite a implementer');
        });
    }

    // ==========================================
    // Notification Buttons
    // ==========================================
    const notificationBtns = document.querySelectorAll('.header-btn');
    
    notificationBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const badge = this.querySelector('.badge-notification');
            if (badge) {
                const type = this.querySelector('.bi-bell') ? 'notifications' : 'messages';
                alert('Vous avez ' + badge.textContent + ' ' + type + ' non lus');
            }
        });
    });

    // ==========================================
    // Table Row Actions
    // ==========================================
    const tableActionBtns = document.querySelectorAll('.table .btn-icon');
    
    tableActionBtns.forEach(function(btn) {
        if (btn.tagName === 'A' || btn.closest('a')) {
            return;
        }
        btn.addEventListener('click', function() {
            const row = this.closest('tr');
            const invoiceId = row.querySelector('td:first-child strong').textContent;
            const action = this.querySelector('.bi-eye') ? 'voir' : 'imprimer';
            alert('Action: ' + action + ' la facture ' + invoiceId);
        });
    });

    // ==========================================
    // Quick Action Buttons
    // ==========================================
    const quickActionBtns = document.querySelectorAll('.quick-action-btn');
    
    quickActionBtns.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.querySelector('span').textContent;
            alert('Action rapide: ' + action);
        });
    });

    // ==========================================
    // Page Action Buttons
    // ==========================================
    const pageActionBtns = document.querySelectorAll('.page-actions .btn');
    
    pageActionBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const action = this.textContent.trim();
            alert('Action: ' + action);
        });
    });

    // ==========================================
    // Alert Items Click
    // ==========================================
    const alertItems = document.querySelectorAll('.alert-item');
    
    alertItems.forEach(function(item) {
        item.style.cursor = 'pointer';
        item.addEventListener('click', function() {
            const title = this.querySelector('.alert-title').textContent;
            const text = this.querySelector('.alert-text').textContent;
            alert(title + '\n\n' + text);
        });
    });

    // ==========================================
    // Responsive Check
    // ==========================================
    function handleResize() {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    }

    window.addEventListener('resize', handleResize);

    // ==========================================
    // Console Welcome Message
    // ==========================================
    console.log('%c Avalon Pharma Dashboard ', 'background: #1e3a5f; color: #fff; padding: 10px 20px; font-size: 16px; font-weight: bold;');
    console.log('%c Version 1.0.0 ', 'background: #0d6efd; color: #fff; padding: 5px 10px;');

});
