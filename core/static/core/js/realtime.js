// Script para conexão WebSocket e Notificações em Tempo Real

class RealTimeNotifications {
    constructor() {
        this.socket = null;
        this.reconnectInterval = 5000; // 5 segundos para reconectar
        this.pollingInterval = 10000; // 10 segundos para polling (fallback)
        this.usePolling = false;
        this.pollingTimer = null;
        this.container = null;
        
        this.init();
    }

    init() {
        // Cria container de toasts se não existir
        this.createToastContainer();
        // Inicia conexão
        this.connect();
    }

    createToastContainer() {
        if (!document.getElementById('toast-container')) {
            const div = document.createElement('div');
            div.id = 'toast-container';
            div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            div.style.zIndex = '1090';
            document.body.appendChild(div);
            this.container = div;
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    connect() {
        // Determina o protocolo (ws ou wss)
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const path = protocol + window.location.host + '/ws/notifications/';

        console.log('Conectando ao WebSocket em: ' + path);

        this.socket = new WebSocket(path);

        this.socket.onopen = () => {
            console.log('WebSocket conectado!');
            this.usePolling = false;
            this.stopPolling();
            this.updateConnectionBadge(true);
        };

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.showNotification(data.message, data.type);
            
            // Atualiza o conteúdo da página (Soft Reload)
            this.softReload();
        };

        this.socket.onclose = (e) => {
            console.error('WebSocket desconectado. Tentando reconectar em 5s...', e);
            this.updateConnectionBadge(false);
            setTimeout(() => this.connect(), this.reconnectInterval);
            
            // Ativa polling como fallback enquanto o socket está fora
            if (!this.usePolling) {
                this.startPolling();
            }
        };

        this.socket.onerror = (err) => {
            console.error('Erro no WebSocket:', err);
            this.socket.close();
        };
    }

    softReload() {
        console.log('Atualizando conteúdo da página...');
        const url = new URL(window.location.href);
        url.searchParams.set('t', new Date().getTime()); // Adiciona timestamp para evitar cache

        fetch(url.toString(), { cache: "no-store" })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                const newMain = doc.querySelector('main');
                const currentMain = document.querySelector('main');

                if (newMain && currentMain) {
                    currentMain.innerHTML = newMain.innerHTML;
                    // Re-inicializar componentes Bootstrap se necessário (ex: tooltips, dropdowns)
                    // mas como dropdowns usam delegação ou data-attributes, geralmente funcionam.
                }
            })
            .catch(err => console.error('Erro ao atualizar página:', err));
    }

    showNotification(message, type = 'info') {
        // Cria o elemento HTML do Toast (Bootstrap 5)
        const toastId = 'toast-' + Date.now();
        
        let bgClass = 'text-bg-primary';
        if (type === 'success') bgClass = 'text-bg-success';
        if (type === 'warning') bgClass = 'text-bg-warning';
        if (type === 'error') bgClass = 'text-bg-danger';

        const html = `
            <div id="${toastId}" class="toast align-items-center ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        // Adiciona ao container
        this.container.insertAdjacentHTML('beforeend', html);

        // Inicializa o Toast do Bootstrap
        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();

        // Remove do DOM após fechar
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    }

    updateConnectionBadge(isConnected) {
        // Procura por um elemento visual (badge) para mostrar status
        const badge = document.getElementById('ws-status-badge');
        if (badge) {
            if (isConnected) {
                badge.classList.remove('bg-danger');
                badge.classList.add('bg-success');
                badge.title = 'Conectado em tempo real';
            } else {
                badge.classList.remove('bg-success');
                badge.classList.add('bg-danger');
                badge.title = 'Desconectado (Usando Polling)';
            }
        }
    }

    // --- Lógica de Polling (Fallback) ---
    startPolling() {
        console.log('Iniciando Polling...');
        this.usePolling = true;
        this.pollingTimer = setInterval(() => {
            this.checkUpdates();
        }, this.pollingInterval);
    }

    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
        }
    }

    checkUpdates() {
        // Endpoint simples para checar se há algo novo (simulação)
        // Em produção, você teria uma API: /api/check-notifications/?last_id=...
        console.log('Polling: Verificando atualizações...');
        // fetch('/api/check-notifications/')...
    }
}

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.realTimeApp = new RealTimeNotifications();
});
