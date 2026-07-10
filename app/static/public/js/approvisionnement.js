/**
 * Approvisionnement Page - JavaScript
 * Gestion des commandes fournisseurs en 3 etapes
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // Global State
    // ==========================================
    let currentStep = 1;
    let selectedSupplier = null;
    let products = [];
    
    // ==========================================
    // DOM Elements
    // ==========================================
    const steps = document.querySelectorAll('.step');
    const stepLines = document.querySelectorAll('.step-line');
    const stepPanels = document.querySelectorAll('.step-content-panel');
    
    // Step 1 Elements
    const searchSupplierInput = document.getElementById('searchSupplier');
    const supplierList = document.getElementById('supplierList');
    const supplierItems = document.querySelectorAll('.supplier-item');
    const btnNewSupplier = document.getElementById('btnNewSupplier');
    const selectedSupplierContainer = document.getElementById('selectedSupplierContainer');
    const btnChangeSupplier = document.getElementById('btnChangeSupplier');
    const btnSaveSupplier = document.getElementById('btnSaveSupplier');
    const btnNextStep1 = document.getElementById('btnNextStep1');
    
    // Step 2 Elements
    const btnAddProduct = document.getElementById('btnAddProduct');
    const productsList = document.getElementById('productsList');
    const emptyProductsState = document.getElementById('emptyProductsState');
    const totalCommande = document.getElementById('totalCommande');
    const btnSaveProducts = document.getElementById('btnSaveProducts');
    const btnNextStep2 = document.getElementById('btnNextStep2');
    const btnPrevStep2 = document.getElementById('btnPrevStep2');
    
    // Step 3 Elements
    const btnFinalizeOrder = document.getElementById('btnFinalizeOrder');
    const btnPrevStep3 = document.getElementById('btnPrevStep3');
    
    // Summary Elements
    const summaryProduits = document.getElementById('summaryProduits');
    const summaryDepense = document.getElementById('summaryDepense');
    const summaryTotal = document.getElementById('summaryTotal');
    
    // Modals
    const newSupplierModal = new bootstrap.Modal(document.getElementById('newSupplierModal'));
    const addProductModal = new bootstrap.Modal(document.getElementById('addProductModal'));

    // ==========================================
    // Dépenses : transport et douane (facultatifs, validation si saisie partielle).
    // ==========================================
    function parseMoney(raw) {
        if (raw === undefined || raw === null) {
            return 0;
        }
        const n = parseFloat(String(raw).replace(',', '.').trim());
        return isNaN(n) ? 0 : n;
    }

    function getTransportFraisValues() {
        return {
            depart: (document.getElementById('fraisTransportDepart') || {}).value || '',
            arrivee: (document.getElementById('fraisTransportArrivee') || {}).value || '',
            transporteur: (document.getElementById('fraisTransportTransporteur') || {}).value || '',
            numeroTransporteur: (document.getElementById('fraisTransportNumero') || {}).value || '',
            montantRaw: (document.getElementById('fraisTransportMontant') || {}).value || '',
            modePaiement: (document.getElementById('fraisTransportMode') || {}).value || '',
            reference: (document.getElementById('fraisTransportReference') || {}).value || '',
            notes: (document.getElementById('fraisTransportNotes') || {}).value || ''
        };
    }

    function transportFraisStarted(t) {
        t.depart = (t.depart || '').trim();
        t.arrivee = (t.arrivee || '').trim();
        t.transporteur = (t.transporteur || '').trim();
        t.numeroTransporteur = (t.numeroTransporteur || '').trim();
        t.reference = (t.reference || '').trim();
        t.notes = (t.notes || '').trim();
        const m = parseMoney(t.montantRaw);
        return !!(t.depart || t.arrivee || t.transporteur || t.numeroTransporteur || t.montantRaw || m !== 0 ||
            t.modePaiement || t.reference || t.notes);
    }

    function transportFraisComplete(t) {
        const m = parseMoney(t.montantRaw);
        return !!(t.depart && t.arrivee && t.transporteur && t.numeroTransporteur && t.montantRaw && m > 0 && t.modePaiement);
    }

    function getDouaneFraisValues() {
        return {
            bureau: (document.getElementById('fraisDouaneBureau') || {}).value || '',
            montantRaw: (document.getElementById('fraisDouaneMontant') || {}).value || '',
            modePaiement: (document.getElementById('fraisDouaneMode') || {}).value || '',
            reference: (document.getElementById('fraisDouaneReference') || {}).value || ''
        };
    }

    function douaneFraisStarted(d) {
        d.bureau = (d.bureau || '').trim();
        d.reference = (d.reference || '').trim();
        const m = parseMoney(d.montantRaw);
        return !!(d.bureau || d.montantRaw || m !== 0 || d.modePaiement || d.reference);
    }

    function douaneFraisComplete(d) {
        const m = parseMoney(d.montantRaw);
        return !!(d.bureau && d.montantRaw && m > 0 && d.modePaiement);
    }

    function getAutreFraisValues() {
        return {
            categorieId: (document.getElementById('fraisAutreCategorie') || {}).value || '',
            libelle: (document.getElementById('fraisAutreLibelle') || {}).value || '',
            montantRaw: (document.getElementById('fraisAutreMontant') || {}).value || '',
            modePaiement: (document.getElementById('fraisAutreMode') || {}).value || ''
        };
    }

    function autreFraisStarted(a) {
        a.libelle = (a.libelle || '').trim();
        const m = parseMoney(a.montantRaw);
        return !!(a.categorieId || a.libelle || a.montantRaw || m !== 0 || a.modePaiement);
    }

    function autreFraisComplete(a) {
        const m = parseMoney(a.montantRaw);
        return !!(a.categorieId && a.libelle && a.montantRaw && m > 0 && a.modePaiement);
    }

    function hasJustificatifFile(inputId) {
        const el = document.getElementById(inputId);
        return !!(el && el.files && el.files.length > 0 && el.files[0].name);
    }

    function validateAllExpenseSections() {
        const tr = getTransportFraisValues();
        if (transportFraisStarted(tr) && !transportFraisComplete(tr)) {
            return {
                ok: false,
                msg: 'Transport : renseignez départ, arrivée, transporteur, n° transporteur, montant > 0 et mode de paiement (ou videz tous les champs).'
            };
        }
        const dq = getDouaneFraisValues();
        if (douaneFraisStarted(dq) && !douaneFraisComplete(dq)) {
            return {
                ok: false,
                msg: 'Douane : renseignez le bureau, un montant > 0 et le mode de paiement (ou videz les champs).'
            };
        }
        const aut = getAutreFraisValues();
        if (autreFraisStarted(aut) && !autreFraisComplete(aut)) {
            return {
                ok: false,
                msg: 'Autre dépense : renseignez le type, la description, un montant > 0 et le mode de paiement (ou videz les champs).'
            };
        }
        return { ok: true };
    }

    // ==========================================
    // Step Navigation
    // ==========================================
    function goToStep(stepNumber) {
        if (stepNumber < 1 || stepNumber > 3) return;
        
        // Update current step
        currentStep = stepNumber;
        
        // Update step indicators
        steps.forEach(function(step, index) {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNum < currentStep) {
                step.classList.add('completed');
            } else if (stepNum === currentStep) {
                step.classList.add('active');
            }
        });
        
        // Update step lines
        stepLines.forEach(function(line, index) {
            if (index < currentStep - 1) {
                line.classList.add('completed');
            } else {
                line.classList.remove('completed');
            }
        });
        
        // Show/hide panels
        stepPanels.forEach(function(panel, index) {
            if (index + 1 === currentStep) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        });
        
        // Update summary if on step 3
        if (currentStep === 3) {
            updateSummary();
        }
    }
    
    // Click on step indicator
    steps.forEach(function(step) {
        step.addEventListener('click', function() {
            const stepNum = parseInt(this.getAttribute('data-step'));
            
            // Can only go back or to completed steps
            if (stepNum < currentStep || this.classList.contains('completed')) {
                goToStep(stepNum);
            }
        });
    });
    
    // ==========================================
    // Step 1: Supplier Management
    // ==========================================
    
    // Search supplier
    if (searchSupplierInput) {
        searchSupplierInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            
            supplierItems.forEach(function(item) {
                const name = item.querySelector('.supplier-name').textContent.toLowerCase();
                const details = item.querySelector('.supplier-details').textContent.toLowerCase();
                
                if (name.includes(query) || details.includes(query)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Select supplier
    supplierItems.forEach(function(item) {
        const selectBtn = item.querySelector('.btn-select-supplier');
        
        selectBtn.addEventListener('click', function() {
            const supplierId = item.getAttribute('data-id');
            const supplierName = item.querySelector('.supplier-name').textContent;
            const supplierDetails = item.querySelector('.supplier-details').textContent;
            
            selectedSupplier = {
                id: supplierId,
                name: supplierName,
                details: supplierDetails,
                isNew: false
            };
            
            // Update UI
            document.getElementById('selectedSupplierName').textContent = supplierName;
            document.getElementById('selectedSupplierDetails').textContent = supplierDetails;
            
            // Show selected card, hide list
            supplierList.style.display = 'none';
            document.querySelector('.search-supplier-box').style.display = 'none';
            selectedSupplierContainer.style.display = 'block';
            
            // Enable buttons
            btnSaveSupplier.disabled = false;
            btnNextStep1.disabled = false;
        });
    });
    
    // Change supplier
    if (btnChangeSupplier) {
        btnChangeSupplier.addEventListener('click', function() {
            selectedSupplier = null;
            
            // Show list, hide selected card
            supplierList.style.display = 'flex';
            document.querySelector('.search-supplier-box').style.display = 'block';
            selectedSupplierContainer.style.display = 'none';
            
            // Disable buttons
            btnSaveSupplier.disabled = true;
            btnNextStep1.disabled = true;
        });
    }
    
    // Nouveau fournisseur : lien vers le formulaire ERP (pas de modal)
    if (btnNewSupplier && btnNewSupplier.tagName === 'BUTTON') {
        btnNewSupplier.addEventListener('click', function() {
            newSupplierModal.show();
        });
    }
    
    // Save new supplier
    const btnSaveNewSupplier = document.getElementById('btnSaveNewSupplier');
    if (btnSaveNewSupplier) {
        btnSaveNewSupplier.addEventListener('click', function() {
            const name = document.getElementById('newSupplierName').value.trim();
            const phone = document.getElementById('newSupplierPhone').value.trim();
            const email = document.getElementById('newSupplierEmail').value.trim();
            const city = document.getElementById('newSupplierCity').value.trim();
            const address = document.getElementById('newSupplierAddress').value.trim();
            
            if (!name || !phone || !city) {
                alert('Veuillez remplir tous les champs obligatoires');
                return;
            }
            
            selectedSupplier = {
                id: 'new-' + Date.now(),
                name: name,
                details: 'Tel: ' + phone + ' | ' + city + (address ? ', ' + address : ''),
                phone: phone,
                email: email,
                city: city,
                address: address,
                isNew: true
            };
            
            // Update UI
            document.getElementById('selectedSupplierName').textContent = name;
            document.getElementById('selectedSupplierDetails').textContent = selectedSupplier.details;
            
            // Show selected card, hide list
            supplierList.style.display = 'none';
            document.querySelector('.search-supplier-box').style.display = 'none';
            selectedSupplierContainer.style.display = 'block';
            
            // Enable buttons
            btnSaveSupplier.disabled = false;
            btnNextStep1.disabled = false;
            
            // Close modal and reset form
            newSupplierModal.hide();
            document.getElementById('newSupplierForm').reset();
        });
    }
    
    // Save supplier button
    if (btnSaveSupplier) {
        btnSaveSupplier.addEventListener('click', function() {
            if (selectedSupplier) {
                alert('Fournisseur enregistre: ' + selectedSupplier.name + (selectedSupplier.isNew ? ' (Nouveau)' : ''));
            }
        });
    }
    
    // Next step 1
    if (btnNextStep1) {
        btnNextStep1.addEventListener('click', function() {
            if (selectedSupplier) {
                goToStep(2);
            }
        });
    }
    
    // ==========================================
    // Step 2: Products Management
    // ==========================================
    
    // Add product button
    if (btnAddProduct) {
        btnAddProduct.addEventListener('click', function() {
            // Reset form + sélection catalogue
            const hid = document.getElementById('selectedCatalogProductId');
            if (hid) {
                hid.value = '';
            }
            document.getElementById('newProductName').value = '';
            document.getElementById('newProductPrixAchat').value = '0';
            document.getElementById('newProductPrixVente').value = '0';
            document.getElementById('newProductQuantity').value = '1';

            addProductModal.show();
        });
    }
    
    // Search product in modal
    const searchProductInput = document.getElementById('searchProduct');
    const productSearchItems = document.querySelectorAll('.product-search-item');
    
    if (searchProductInput) {
        searchProductInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            
            productSearchItems.forEach(function(item) {
                const name = item.querySelector('.product-search-name').textContent.toLowerCase();
                const code = item.querySelector('.product-search-code').textContent.toLowerCase();
                
                if (name.includes(query) || code.includes(query)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Select product from list (produit réel en base)
    productSearchItems.forEach(function(item) {
        const selectBtn = item.querySelector('.btn-select-catalog-product') || item.querySelector('button');
        if (!selectBtn) {
            return;
        }

        selectBtn.addEventListener('click', function() {
            const productId = item.getAttribute('data-id');
            const productName = item.getAttribute('data-name') || '';
            const productPrice = parseFloat(item.getAttribute('data-price')) || 0;
            const prixVenteAttr = item.getAttribute('data-prix-vente');
            const prixVente = prixVenteAttr ? parseFloat(prixVenteAttr) : Math.round(productPrice * 1.3);

            const hid = document.getElementById('selectedCatalogProductId');
            if (hid) {
                hid.value = productId || '';
            }

            document.getElementById('newProductName').value = productName;
            document.getElementById('newProductPrixAchat').value = String(productPrice);
            document.getElementById('newProductPrixVente').value = String(prixVente);
            document.getElementById('newProductQuantity').value = '1';
        });
    });
    
    // Confirm add product
    const btnConfirmAddProduct = document.getElementById('btnConfirmAddProduct');
    if (btnConfirmAddProduct) {
        btnConfirmAddProduct.addEventListener('click', function() {
            const hid = document.getElementById('selectedCatalogProductId');
            const produitIdRaw = hid ? hid.value.trim() : '';
            const produitId = parseInt(produitIdRaw, 10);

            const name = document.getElementById('newProductName').value.trim();
            const prixAchat = parseFloat(document.getElementById('newProductPrixAchat').value) || 0;
            const prixVente = parseFloat(document.getElementById('newProductPrixVente').value) || 0;
            const quantity = parseInt(document.getElementById('newProductQuantity').value, 10) || 1;

            if (!produitIdRaw || isNaN(produitId)) {
                alert('Sélectionnez un produit dans la liste (recherche). Pour un nouveau médicament, créez d’abord le produit depuis le stock puis rechargez cette page.');
                return;
            }

            if (!name || prixAchat <= 0 || quantity <= 0) {
                alert('Veuillez remplir tous les champs obligatoires');
                return;
            }

            const product = {
                rowId: Date.now(),
                produitId: produitId,
                name: name,
                prixAchat: prixAchat,
                prixVente: prixVente,
                quantity: quantity,
                total: prixAchat * quantity
            };

            products.push(product);
            renderProducts();
            addProductModal.hide();
            if (hid) {
                hid.value = '';
            }
        });
    }
    
    // Render products table
    function renderProducts() {
        if (products.length === 0) {
            productsList.innerHTML = '';
            emptyProductsState.style.display = 'block';
            btnSaveProducts.disabled = true;
            btnNextStep2.disabled = true;
            totalCommande.textContent = '0 FCFA';
            return;
        }
        
        emptyProductsState.style.display = 'none';
        btnSaveProducts.disabled = false;
        btnNextStep2.disabled = false;
        
        let html = '';
        let total = 0;
        
        products.forEach(function(product, index) {
            total += product.total;

            html += '<tr data-index="' + index + '">';
            html += '<td><strong>' + product.name + '</strong>';
            html += ' <span class="text-muted small">(#' + product.produitId + ')</span></td>';
            html += '<td>';
            html += '<input type="number" step="0.01" class="form-control form-control-sm input-prix-achat" value="' + product.prixAchat + '" min="0">';
            html += '</td>';
            html += '<td>';
            html += '<input type="number" step="0.01" class="form-control form-control-sm input-prix-vente" value="' + product.prixVente + '" min="0">';
            html += '</td>';
            html += '<td>';
            html += '<input type="number" class="form-control form-control-sm input-quantity" value="' + product.quantity + '" min="1">';
            html += '</td>';
            html += '<td><strong>' + product.total.toLocaleString('fr-FR') + ' FCFA</strong></td>';
            html += '<td>';
            html += '<button class="btn btn-sm btn-outline-danger btn-remove-product" title="Supprimer">';
            html += '<i class="bi bi-trash"></i>';
            html += '</button>';
            html += '</td>';
            html += '</tr>';
        });
        
        productsList.innerHTML = html;
        totalCommande.textContent = total.toLocaleString('fr-FR') + ' FCFA';
        
        // Bind events
        bindProductEvents();
    }
    
    // Bind product row events
    function bindProductEvents() {
        // Update prix achat
        document.querySelectorAll('.input-prix-achat').forEach(function(input) {
            input.addEventListener('change', function() {
                const index = parseInt(this.closest('tr').getAttribute('data-index'), 10);
                products[index].prixAchat = parseFloat(this.value) || 0;
                products[index].total = products[index].prixAchat * products[index].quantity;
                renderProducts();
            });
        });
        
        // Update prix vente
        document.querySelectorAll('.input-prix-vente').forEach(function(input) {
            input.addEventListener('change', function() {
                const index = parseInt(this.closest('tr').getAttribute('data-index'), 10);
                products[index].prixVente = parseFloat(this.value) || 0;
            });
        });
        
        // Update quantity
        document.querySelectorAll('.input-quantity').forEach(function(input) {
            input.addEventListener('change', function() {
                const index = parseInt(this.closest('tr').getAttribute('data-index'), 10);
                products[index].quantity = parseInt(this.value, 10) || 1;
                products[index].total = products[index].prixAchat * products[index].quantity;
                renderProducts();
            });
        });
        
        // Remove product
        document.querySelectorAll('.btn-remove-product').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const index = parseInt(this.closest('tr').getAttribute('data-index'), 10);
                products.splice(index, 1);
                renderProducts();
            });
        });
    }
    
    // Save products
    if (btnSaveProducts) {
        btnSaveProducts.addEventListener('click', function() {
            if (products.length > 0) {
                alert('Produits enregistres: ' + products.length + ' produit(s)');
            }
        });
    }
    
    // Navigation step 2
    if (btnPrevStep2) {
        btnPrevStep2.addEventListener('click', function() {
            goToStep(1);
        });
    }
    
    if (btnNextStep2) {
        btnNextStep2.addEventListener('click', function() {
            if (products.length > 0) {
                goToStep(3);
            }
        });
    }
    
    // ==========================================
    // Step 3: Frais transport + douane
    // ==========================================

    function updateSummary() {
        const totalProduits = products.reduce(function(sum, p) {
            return sum + p.total;
        }, 0);

        summaryProduits.textContent = totalProduits.toLocaleString('fr-FR') + ' FCFA';

        const tTr = getTransportFraisValues();
        const mt = Math.round(parseMoney(tTr.montantRaw));
        const dD = getDouaneFraisValues();
        const md = Math.round(parseMoney(dD.montantRaw));
        const aA = getAutreFraisValues();
        const ma = Math.round(parseMoney(aA.montantRaw));
        const depenseMontant = mt + md + ma;
        if (summaryDepense) {
            summaryDepense.textContent = depenseMontant.toLocaleString('fr-FR') + ' FCFA';
        }

        const total = totalProduits + depenseMontant;
        summaryTotal.textContent = total.toLocaleString('fr-FR') + ' FCFA';
    }

    [
        'fraisTransportDepart', 'fraisTransportArrivee', 'fraisTransportTransporteur', 'fraisTransportNumero',
        'fraisTransportMontant', 'fraisTransportMode', 'fraisTransportReference', 'fraisTransportNotes',
        'fraisDouaneBureau', 'fraisDouaneMontant', 'fraisDouaneMode', 'fraisDouaneReference',
        'fraisAutreCategorie', 'fraisAutreLibelle', 'fraisAutreMontant', 'fraisAutreMode'
    ].forEach(function(id) {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateSummary);
            el.addEventListener('change', updateSummary);
        }
    });

    // Navigation step 3
    if (btnPrevStep3) {
        btnPrevStep3.addEventListener('click', function() {
            goToStep(2);
        });
    }
    
    function appendHidden(form, name, value) {
        const inp = document.createElement('input');
        inp.type = 'hidden';
        inp.name = name;
        inp.value = value;
        form.appendChild(inp);
    }

    /** JSON : transport, douane (création Depense côté serveur). */
    function buildFraisApprovisionnementJson() {
        const out = {};
        try {
            const tr = getTransportFraisValues();
            if (transportFraisComplete(tr)) {
                out.transport = {
                    depart: tr.depart.trim(),
                    arrivee: tr.arrivee.trim(),
                    transporteur: tr.transporteur.trim(),
                    numero_transporteur: tr.numeroTransporteur.trim(),
                    montant: Math.round(parseMoney(tr.montantRaw)),
                    mode_paiement: tr.modePaiement,
                    reference: tr.reference.trim(),
                    notes: tr.notes.trim()
                };
            }
            const dq = getDouaneFraisValues();
            if (douaneFraisComplete(dq)) {
                out.douane = {
                    bureau: dq.bureau.trim(),
                    montant: Math.round(parseMoney(dq.montantRaw)),
                    mode_paiement: dq.modePaiement,
                    reference: dq.reference.trim()
                };
            }
            const aut = getAutreFraisValues();
            if (autreFraisComplete(aut)) {
                out.depense_autre = {
                    categorie_id: parseInt(aut.categorieId, 10),
                    libelle: aut.libelle.trim(),
                    montant: Math.round(parseMoney(aut.montantRaw)),
                    mode_paiement: aut.modePaiement
                };
            }
        } catch (e) {
            out._error = String(e);
        }
        return JSON.stringify(out);
    }

    // Finalize order — POST vers le backend (création CommandeFournisseur)
    if (btnFinalizeOrder) {
        btnFinalizeOrder.addEventListener('click', function() {
            if (!selectedSupplier) {
                alert('Veuillez selectionner un fournisseur');
                goToStep(1);
                return;
            }

            const fid = parseInt(String(selectedSupplier.id), 10);
            if (isNaN(fid) || selectedSupplier.isNew) {
                alert('Choisissez un fournisseur existant dans la liste. Utilisez « Nouveau fournisseur » pour l’enregistrer, puis rechargez cette page.');
                goToStep(1);
                return;
            }

            if (products.length === 0) {
                alert('Veuillez ajouter au moins un produit');
                goToStep(2);
                return;
            }

            for (let i = 0; i < products.length; i++) {
                if (!products[i].produitId) {
                    alert('Une ligne produit est invalide. Ré-ajoutez les produits depuis le catalogue.');
                    goToStep(2);
                    return;
                }
            }

            const expenseCheck = validateAllExpenseSections();
            if (!expenseCheck.ok) {
                alert(expenseCheck.msg);
                goToStep(3);
                return;
            }

            const dateCmdEl = document.getElementById('dateCommande');
            const dateCmd = dateCmdEl && dateCmdEl.value ? dateCmdEl.value : '';
            if (!dateCmd) {
                alert('Indiquez la date de commande (étape 1).');
                goToStep(1);
                return;
            }

            const cfg = window.APPROVISIONNEMENT || {};
            const submitUrl = cfg.submitUrl || '';
            if (!submitUrl) {
                alert('URL de soumission manquante. Rechargez la page.');
                return;
            }

            const form = document.createElement('form');
            form.method = 'POST';
            form.action = submitUrl;
            form.enctype = 'multipart/form-data';

            appendHidden(form, 'fournisseur_id', String(fid));
            appendHidden(form, 'date_commande', dateCmd);
            const dateLiv = document.getElementById('dateLivraisonPrevue');
            if (dateLiv && dateLiv.value) {
                appendHidden(form, 'date_livraison_prevue', dateLiv.value);
            }
            const fraisJson = buildFraisApprovisionnementJson();
            if (fraisJson && fraisJson !== '{}') {
                appendHidden(form, 'frais_approvisionnement', fraisJson);
            }

            products.forEach(function(p) {
                appendHidden(form, 'produit_id[]', String(p.produitId));
                appendHidden(form, 'quantite[]', String(p.quantity));
                appendHidden(form, 'prix_achat_ht[]', String(p.prixAchat));
            });

            ['justificatifTransport', 'justificatifDouane', 'justificatifAutre'].forEach(function(inputId) {
                const src = document.getElementById(inputId);
                if (src && src.files && src.files.length > 0) {
                    form.appendChild(src);
                }
            });

            btnFinalizeOrder.disabled = true;
            document.body.appendChild(form);
            form.submit();
        });
    }
    
    // ==========================================
    // Initialize
    // ==========================================
    renderProducts();
    
});
