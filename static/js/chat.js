// Nombre del archivo: static/js/chat.js
document.addEventListener('DOMContentLoaded', async function() {
    const socket = io();
    const myId = document.getElementById('current_user_id').value;
    const myName = document.getElementById('current_user_nombre').value;
    
    let currentChatId = null; 
    let usuarios = [];

    const chatBox = document.getElementById('chat-box');
    const chatTitle = document.getElementById('chat-title');
    const chatInput = document.getElementById('chat-input');
    const form = document.getElementById('chat-form');
    
    const usersListDesktop = document.getElementById('users-list-desktop');
    const usersListMobile = document.getElementById('users-list-mobile');
    
    const searchDesktop = document.getElementById('search-contacts-desktop');
    const searchMobile = document.getElementById('search-contacts-mobile');
    
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');

    socket.on('connect', () => {
        socket.emit('conectar_usuario', { user_id: myId });
        socket.emit('pedir_estados');
    });

    async function cargarUsuarios() {
        try {
            const res = await fetch('/api/usuarios_chat');
            if(!res.ok) throw new Error("Error en la red");
            usuarios = await res.json();
            renderizarListaUsuarios();
        } catch (e) {
            console.error("Error cargando usuarios", e);
        }
    }
    cargarUsuarios();

    socket.on('estado_usuarios', (data) => {
        document.querySelectorAll(`.status-${data.user_id}`).forEach(ind => {
            ind.className = `status-${data.user_id} bi bi-circle-fill ms-2 ${data.status === 'online' ? 'text-success' : 'text-secondary'}`;
        });
    });

    socket.on('lista_estados', (conectadosIds) => {
        conectadosIds.forEach(id => {
            document.querySelectorAll(`.status-${id}`).forEach(ind => {
                ind.className = `status-${id} bi bi-circle-fill ms-2 text-success`;
            });
        });
    });

    if(searchDesktop) searchDesktop.addEventListener('input', (e) => renderizarListaUsuarios(e.target.value.toLowerCase()));
    if(searchMobile) searchMobile.addEventListener('input', (e) => renderizarListaUsuarios(e.target.value.toLowerCase()));

    function renderizarListaUsuarios(filtro = '') {
        // ==========================================
        // AQUÍ ESTÁ EL BOTÓN DE LA SALA VIRTUAL
        // ==========================================
        let html = `
            <a href="/lobby" class="list-group-item list-group-item-action d-flex align-items-center p-3 border-bottom text-decoration-none bg-transparent" style="cursor: pointer;">
                <div class="bg-danger text-white rounded-circle d-flex justify-content-center align-items-center me-3 shadow-sm" style="width: 45px; height: 45px;">
                    <i class="bi bi-camera-video-fill fs-5"></i>
                </div>
                <div>
                    <h6 class="mb-0 fw-bold text-dark">Sala Virtual (Cursos)</h6>
                    <small class="text-danger fw-bold"><i class="bi bi-record-circle me-1"></i>Ingresar al Lobby</small>
                </div>
            </a>

            <button class="list-group-item list-group-item-action d-flex align-items-center p-3 border-bottom bg-transparent" onclick="seleccionarChat('global', 'Chat Global')">
                <div class="dynamic-nav rounded-circle d-flex justify-content-center align-items-center me-3 shadow-sm" style="width: 45px; height: 45px;">
                    <i class="bi bi-globe fs-5" style="color: var(--text-on-accent)"></i>
                </div>
                <div>
                    <h6 class="mb-0 fw-bold text-dark">Chat Global</h6>
                    <small class="text-muted">Sala pública de texto</small>
                </div>
            </button>
        `;

        usuarios.forEach(u => {
            if(u.id == myId) return; 
            const nombreCompleto = `${u.nombre} ${u.apellidos}`.toLowerCase();
            if (filtro && !nombreCompleto.includes(filtro)) return;

            html += `
                <button class="list-group-item list-group-item-action d-flex align-items-center p-3 border-bottom bg-transparent" onclick="seleccionarChat(${u.id}, '${u.nombre} ${u.apellidos}')">
                    <div class="dynamic-nav rounded-circle d-flex justify-content-center align-items-center fw-bold fs-5 me-3 shadow-sm" style="width: 45px; height: 45px; color: var(--text-on-accent);">
                        ${u.nombre.charAt(0)}
                    </div>
                    <div class="flex-grow-1 overflow-hidden">
                        <h6 class="mb-0 text-truncate d-flex align-items-center text-dark">
                            ${u.nombre}
                            <i class="status-${u.id} bi bi-circle-fill ms-2 text-secondary" style="font-size: 0.5rem;"></i>
                        </h6>
                        <small class="text-muted">Chat Privado</small>
                    </div>
                </button>
            `;
        });
        
        if(usersListDesktop) usersListDesktop.innerHTML = html;
        if(usersListMobile) usersListMobile.innerHTML = html;
        socket.emit('pedir_estados'); 
    }

    window.seleccionarChat = async function(dest_id, dest_name) {
        currentChatId = dest_id;
        
        const modalEl = document.getElementById('contactosModal');
        if(modalEl) {
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
        }
        
        const welcome = document.getElementById('welcome-screen');
        if(welcome) welcome.remove();
        
        chatTitle.innerHTML = dest_id === 'global' 
            ? `<i class="bi bi-globe dynamic-text me-2"></i> Chat Global` 
            : `<i class="bi bi-person-fill text-secondary me-2"></i> ${dest_name}`;

        chatBox.innerHTML = '<div class="text-center dynamic-text mt-5"><div class="spinner-border" role="status"></div><p class="mt-2 text-muted">Cargando mensajes...</p></div>';
        
        try {
            const res = await fetch(`/api/mensajes/${dest_id}`);
            if(!res.ok) throw new Error("Fallo de backend");
            const mensajes = await res.json();
            
            chatBox.innerHTML = '';
            mensajes.forEach(m => renderMensaje(m));
            scrollToBottom();

            mensajes.forEach(m => {
                if(m.remitente_id != myId && !m.leido && dest_id !== 'global') {
                    socket.emit('marcar_leido', { mensaje_id: m.id });
                }
            });
        } catch (err) {
            chatBox.innerHTML = '<div class="text-center text-danger mt-5">Error al cargar el historial.</div>';
        }
    };

    function renderMensaje(msg) {
        if(document.getElementById(`msg-${msg.id}`)) return; 

        const isMe = msg.remitente_id == myId;
        const nameLabel = isMe ? 'Tú' : msg.remitente_nombre;
        
        const alignClass = isMe ? 'justify-content-end' : 'justify-content-start';
        const bubbleClass = isMe ? 'dynamic-bubble-mine' : 'bg-white text-dark border shadow-sm';
        const timeColor = isMe ? 'text-white-50' : 'text-muted';
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `d-flex w-100 mb-3 ${alignClass}`;
        msgDiv.id = `msg-${msg.id}`;

        let contenidoHTML = msg.borrado ? `<span class="fst-italic opacity-75"><i class="bi bi-slash-circle me-1"></i> Este mensaje fue eliminado.</span>` : msg.texto;

        if (msg.archivo_url && !msg.borrado) {
            const tipo = msg.tipo_archivo || '';
            if (tipo.startsWith('image/')) {
                contenidoHTML += `<div class="mt-2"><img src="${msg.archivo_url}" class="img-fluid rounded shadow-sm" style="max-height: 200px;"></div>`;
            } else if (tipo.startsWith('video/')) {
                contenidoHTML += `<div class="mt-2"><video src="${msg.archivo_url}" controls class="w-100 rounded shadow-sm" style="max-height: 250px;"></video></div>`;
            } else if (tipo.startsWith('audio/')) {
                contenidoHTML += `<div class="mt-2"><audio src="${msg.archivo_url}" controls class="w-100" style="height: 40px;"></audio></div>`;
            } else {
                const btnClass = isMe ? 'btn-light dynamic-text' : 'dynamic-btn';
                contenidoHTML += `
                    <div class="mt-2">
                        <a href="${msg.archivo_url}" download class="btn btn-sm ${btnClass} d-inline-flex align-items-center shadow-sm">
                            <i class="bi bi-download me-2"></i> Descargar Archivo
                        </a>
                    </div>`;
            }
        }

        let checksHTML = '';
        if (isMe && currentChatId !== 'global') {
            checksHTML = `<span class="ms-1" id="check-${msg.id}">
                ${msg.leido ? '<i class="bi bi-check-all text-white"></i>' : '<i class="bi bi-check text-white-50"></i>'}
            </span>`;
        }

        let btnBorrar = '';
        if (!msg.borrado) {
            const trashColor = isMe ? 'text-white-50' : 'text-danger opacity-75';
            btnBorrar = `<button class="btn btn-sm p-0 ms-2 border-0 bg-transparent ${trashColor}" onclick="borrarMensaje(${msg.id}, ${isMe})" title="Eliminar"><i class="bi bi-trash3-fill"></i></button>`;
        }

        msgDiv.innerHTML = `
            <div style="max-width: 75%;">
                <div class="small mb-1 px-1 ${isMe ? 'text-end text-muted' : 'text-muted'}">${nameLabel}</div>
                <div class="p-3 rounded-4 ${bubbleClass}" style="${isMe ? 'border-bottom-right-radius: 4px !important;' : 'border-bottom-left-radius: 4px !important;'}">
                    <div id="text-${msg.id}">${contenidoHTML}</div>
                    <div class="d-flex justify-content-end align-items-center mt-2 small ${timeColor}">
                        <span>${msg.fecha_envio}</span>
                        ${checksHTML}
                        ${btnBorrar}
                    </div>
                </div>
            </div>
        `;

        chatBox.appendChild(msgDiv);
        scrollToBottom();
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if(!currentChatId) {
            if(typeof window.showNotification === 'function') {
                window.showNotification("Selecciona un contacto en el panel lateral para escribir.", "info");
            }
            return;
        }

        let texto = chatInput.value.trim();
        let archivoUrl = null, tipoArchivo = null, nombreArchivo = null;
        const file = fileInput.files[0];

        if (!texto && !file) return;

        if (file) {
            uploadStatus.style.display = 'block';
            chatInput.disabled = true; document.getElementById('btn-enviar').disabled = true;
            const formData = new FormData(); formData.append('file', file);
            try {
                const res = await fetch('/api/upload_file', { method: 'POST', body: formData });
                const data = await res.json();
                archivoUrl = data.url; tipoArchivo = data.tipo; nombreArchivo = data.nombre;
            } catch (err) {
                console.error(err); 
                if(typeof window.showNotification === 'function') window.showNotification("Error al subir el archivo.", "error"); 
                uploadStatus.style.display = 'none';
                chatInput.disabled = false; document.getElementById('btn-enviar').disabled = false;
                return;
            }
        }

        socket.emit('enviar_mensaje', {
            remitente_id: myId, destinatario_id: currentChatId === 'global' ? null : currentChatId,
            texto: texto, archivo_url: archivoUrl, tipo_archivo: tipoArchivo, nombre_archivo: nombreArchivo
        });

        chatInput.value = ''; fileInput.value = ''; uploadStatus.style.display = 'none';
        chatInput.disabled = false; document.getElementById('btn-enviar').disabled = false; chatInput.focus();
    });

    socket.on('nuevo_mensaje', function(msg) {
        const isGlobalMsg = msg.destinatario_id === null;
        const imInGlobal = currentChatId === 'global';
        const isForCurrentPrivate = msg.remitente_id == currentChatId || msg.destinatario_id == currentChatId;

        if ((isGlobalMsg && imInGlobal) || (!isGlobalMsg && isForCurrentPrivate)) {
            renderMensaje(msg);
            if(msg.remitente_id != myId && !isGlobalMsg) {
                socket.emit('marcar_leido', { mensaje_id: msg.id });
            }
        }
    });

    window.borrarMensaje = function(id, isMe) {
        document.getElementById('delete-msg-id').value = id;
        const btnTodos = document.getElementById('btn-borrar-todos');
        btnTodos.style.display = isMe ? 'block' : 'none';
        new bootstrap.Modal(document.getElementById('modalBorrarMsg')).show();
    };

    window.confirmarBorrado = function(tipo) {
        const id = document.getElementById('delete-msg-id').value;
        socket.emit('borrar_mensaje', { mensaje_id: id, tipo: tipo, user_id: myId });
        bootstrap.Modal.getInstance(document.getElementById('modalBorrarMsg')).hide();
    };

    socket.on('mensaje_borrado', (data) => {
        const textSpan = document.getElementById(`text-${data.id}`);
        if(textSpan) textSpan.innerHTML = '<span class="fst-italic opacity-75"><i class="bi bi-slash-circle me-1"></i> Este mensaje fue eliminado.</span>';
    });

    socket.on('mensaje_oculto', (data) => {
        const msgDiv = document.getElementById(`msg-${data.id}`);
        if(msgDiv) msgDiv.remove(); 
    });

    socket.on('mensaje_actualizado', (data) => {
        if(data.leido) {
            const check = document.getElementById(`check-${data.id}`);
            if(check) check.innerHTML = '<i class="bi bi-check-all text-white"></i>';
        }
    });

    function scrollToBottom() { chatBox.scrollTop = chatBox.scrollHeight; }
});