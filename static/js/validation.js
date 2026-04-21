// Nombre del archivo: static/js/validation.js
document.addEventListener('DOMContentLoaded', function() {
    
    // --- LÓGICA DE TEMAS DINÁMICOS ---
    document.querySelectorAll('.theme-circle').forEach(btn => {
        btn.addEventListener('click', async function() {
            const temaSeleccionado = this.getAttribute('data-tema');
            
            // Borrar cualquier tema anterior del body
            document.body.className = document.body.className.replace(/\btema-\S+/g, '');
            // Añadir el nuevo tema
            document.body.classList.add(temaSeleccionado);
            
            // Cerrar el modal para que se vea el cambio
            const modalEl = document.getElementById('modalTemas');
            if (modalEl) {
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) modalInstance.hide();
            }

            // Notificar sutilmente
            showNotification("Tema actualizado con éxito.", "success");

            // Guardar en el backend de forma silenciosa
            try {
                await fetch('/api/guardar_tema', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tema: temaSeleccionado })
                });
            } catch (e) {
                console.error("Error guardando tema en BD", e);
            }
        });
    });

    window.showNotification = function(mensaje, tipo = 'info') {
        const toastEl = document.getElementById('uiToast');
        const toastHeader = document.getElementById('uiToastHeader');
        const toastMessage = document.getElementById('uiToastMessage');
        const toastTitle = document.getElementById('uiToastTitle');
        const toastIcon = document.getElementById('uiToastIcon');
        
        if (toastEl && toastMessage) {
            toastMessage.textContent = mensaje;
            
            let bgClass, textClass, iconClass, titleText;
            if (tipo === 'error') {
                bgClass = 'bg-danger'; textClass = 'text-white'; iconClass = 'bi-exclamation-triangle-fill'; titleText = 'Error';
            } else if (tipo === 'success') {
                bgClass = 'bg-success'; textClass = 'text-white'; iconClass = 'bi-check-circle-fill'; titleText = 'Éxito';
            } else {
                // Info usa los colores del tema dinámico
                bgClass = 'dynamic-nav'; textClass = 'text-white'; iconClass = 'bi-info-circle-fill'; titleText = 'Información';
            }

            toastHeader.className = `toast-header ${bgClass} border-0`;
            toastHeader.style.color = "var(--text-on-accent)";
            toastEl.className = `toast border-0 shadow-lg`;
            toastIcon.className = `bi me-2 ${iconClass}`;
            toastTitle.textContent = titleText;

            const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
            toast.show();
        }
    };

    const regexNombreApellidos = /^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?$/;
    const regexSoloUnApellido = /^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$/;
    const regexTelefono = /^[0-9]{8}$/;

    function validarInput(input, regex) {
        if (!input) return false;
        if (regex.test(input.value)) {
            input.classList.remove('is-invalid'); input.classList.add('is-valid');
            return true;
        } else {
            input.classList.remove('is-valid'); input.classList.add('is-invalid');
            return false;
        }
    }

    function formatearTextoEstricto(texto, permiteEspacios) {
        let limpio = permiteEspacios ? texto.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '') : texto.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ]/g, '');
        limpio = limpio.replace(/\s{2,}/g, ' ');
        return limpio.split(' ').map(palabra => palabra.length > 0 ? palabra.charAt(0).toUpperCase() + palabra.slice(1).toLowerCase() : palabra).join(' ');
    }

    ['#nombre', '#segundo_apellido'].forEach(selector => {
        const el = document.querySelector(selector);
        if (el) el.addEventListener('input', function() {
            const start = this.selectionStart;
            this.value = formatearTextoEstricto(this.value, true);
            validarInput(this, regexNombreApellidos);
            this.setSelectionRange(start, start);
        });
    });

    const primerApellido = document.querySelector('#primer_apellido');
    if (primerApellido) primerApellido.addEventListener('input', function() {
        const start = this.selectionStart;
        this.value = formatearTextoEstricto(this.value, false);
        validarInput(this, regexSoloUnApellido);
        this.setSelectionRange(start, start);
    });

    const telefono = document.querySelector('#telefono');
    if (telefono) telefono.addEventListener('input', () => {
        telefono.value = telefono.value.replace(/[^0-9]/g, '');
        validarInput(telefono, regexTelefono);
    });

    const email = document.querySelector('#email');
    if (email) email.addEventListener('input', () => email.value = email.value.toLowerCase());

    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text'; icon.classList.replace('bi-eye', 'bi-eye-slash');
            } else {
                input.type = 'password'; icon.classList.replace('bi-eye-slash', 'bi-eye');
            }
        });
    });

    const selectOpciones = document.getElementById('tipo_opcion_extra');
    const containerOpciones = document.getElementById('dynamic-fields-container');

    if (selectOpciones) {
        selectOpciones.addEventListener('change', function() {
            containerOpciones.innerHTML = ''; 
            const valor = this.value;
            let htmlCampos = '';

            if (valor === 'Empresa' || valor === 'Proveedor' || valor === 'Institucion') {
                htmlCampos = `
                    <div class="mb-2"><input type="text" class="form-control" placeholder="Nombre de ${valor}" name="extra_nombre" required></div>
                    <div class="mb-2"><input type="text" class="form-control" placeholder="Teléfono" name="extra_tel" required></div>
                    <div class="mb-2"><input type="email" class="form-control" placeholder="Email" name="extra_email" required></div>
                `;
            } else if (['Otro'].includes(valor)) {
                htmlCampos = `<div class="mb-2"><input type="text" class="form-control" placeholder="Detalle adicional" name="extra_detalle" required></div>`;
            }
            containerOpciones.innerHTML = htmlCampos;
        });
    }

    const formRegistro = document.getElementById('formRegistro');
    if (formRegistro) {
        formRegistro.addEventListener('submit', async function(e) {
            e.preventDefault(); 
            if (document.querySelectorAll('.is-invalid').length > 0) {
                showNotification("Por favor, corrige los errores antes de continuar.", "error"); return;
            }
            const formData = new FormData(formRegistro);
            const dataObj = Object.fromEntries(formData.entries());
            dataObj.opciones_extra = { tipo: document.getElementById('tipo_opcion_extra')?.value || "" };
            if(dataObj.extra_nombre) dataObj.opciones_extra.nombre = dataObj.extra_nombre;
            if(dataObj.extra_tel) dataObj.opciones_extra.telefono = dataObj.extra_tel;
            if(dataObj.extra_email) dataObj.opciones_extra.email = dataObj.extra_email;
            if(dataObj.extra_detalle) dataObj.opciones_extra.detalle = dataObj.extra_detalle;

            try {
                const response = await fetch('/api/registro', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dataObj) });
                const result = await response.json();
                if (result.status === 'success') {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(result.llave_json));
                    const dl = document.createElement('a'); dl.setAttribute("href", dataStr); dl.setAttribute("download", `llave_${dataObj.email}.json`);
                    document.body.appendChild(dl); dl.click(); dl.remove();
                    showNotification(result.mensaje + " Descargando llave...", "success");
                    setTimeout(() => window.location.href = '/login', 2500);
                } else showNotification("Error: " + result.mensaje, "error");
            } catch (err) { showNotification("Fallo de conexión.", "error"); }
        });
    }

    const formLogin = document.getElementById('formLogin');
    if (formLogin) {
        formLogin.addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            try {
                const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
                const result = await response.json();
                if (result.status === 'success') {
                    showNotification(result.mensaje, "success"); setTimeout(() => window.location.href = result.redirect, 1000); 
                } else showNotification(result.mensaje, "error");
            } catch (err) { showNotification("Fallo de conexión.", "error"); }
        });
    }

    const dropZone = document.getElementById('dropZoneLlave');
    const fileInputLlave = document.getElementById('fileInputLlave');

    if (dropZone && fileInputLlave) {
        dropZone.addEventListener('click', () => fileInputLlave.click());
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault(); dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) procesarLlave(e.dataTransfer.files[0]);
        });
        fileInputLlave.addEventListener('change', function() { if (this.files.length) procesarLlave(this.files[0]); });
    }

    function procesarLlave(file) {
        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const llaveData = JSON.parse(e.target.result);
                if (llaveData.llave_acceso) {
                    showNotification("Procesando llave...", "info");
                    const response = await fetch('/api/login_llave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ llave_acceso: llaveData.llave_acceso }) });
                    const result = await response.json();
                    if(result.status === 'success') {
                        showNotification(result.mensaje, "success"); setTimeout(() => window.location.href = result.redirect, 1500);
                    } else showNotification(result.mensaje, "error");
                } else showNotification("Formato incorrecto.", "error");
            } catch (error) { showNotification("Error al leer el archivo JSON.", "error"); }
        };
        reader.readAsText(file);
    }
});