document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const datasetsList = document.getElementById('datasets-list');
    const uploadBtn = document.getElementById('upload-btn');
    const fileUpload = document.getElementById('file-upload');
    
    const API_URL = '/api';

    // Inicializar sesión cargando los datos guardados en la API
    async function initSession() {
        // Borrar solo el historial al refrescar la página, manteniendo las tablas
        localStorage.removeItem('agent3_history');
        fetchDatasets();
        renderHistory();
    }
    
    initSession();

    // Lógica para subir archivos manualmente
    if(uploadBtn && fileUpload) {
        uploadBtn.addEventListener('click', () => fileUpload.click());

        fileUpload.addEventListener('change', async (e) => {
            const files = Array.from(e.target.files);
            if (!files.length) return;
            
            const totalFiles = files.length;
            appendMessage(`📁 Subiendo ${totalFiles} archivo${totalFiles > 1 ? 's' : ''}...`, 'user');
            const typingId = showTypingIndicator();
            
            let successCount = 0;
            let failCount = 0;
            const uploadedNames = [];

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('name', file.name.replace('.csv', ''));
                formData.append('description', 'Dataset subido manualmente.');

                try {
                    const resp = await fetch('/api/datasets/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        successCount++;
                        uploadedNames.push(data.name);
                    } else {
                        failCount++;
                    }
                } catch (error) {
                    failCount++;
                }
            }
            
            removeTypingIndicator(typingId);
            
            if (successCount > 0) {
                let msg = `✅ **${successCount}/${totalFiles}** dataset${successCount > 1 ? 's' : ''} subido${successCount > 1 ? 's' : ''} exitosamente:\n\n`;
                uploadedNames.forEach(name => {
                    msg += `  • **${name}**\n`;
                });
                if (failCount > 0) {
                    msg += `\n⚠️ ${failCount} archivo${failCount > 1 ? 's' : ''} fallaron al subir.`;
                }
                msg += `\n\n🚀 Ya puedes hacer preguntas, pedir gráficas o cruzar las tablas con JOINs.`;
                appendSystemMessageWithChart(msg, null);
                fetchDatasets();
            } else {
                appendMessage(`❌ No se pudieron subir los archivos. Verifica que la API esté corriendo.`, 'system');
            }
            
            fileUpload.value = '';
        });
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        userInput.value = '';

        const typingId = showTypingIndicator();

        try {
            const response = await fetch(`${API_URL}/process`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) throw new Error('Error al conectar con el servidor.');
            
            const data = await response.json();
            removeTypingIndicator(typingId);
            
            if (data.error) {
                appendMessage(`Error: ${data.error}`, 'system');
            } else {
                appendSystemMessageWithChart(data.explanation, data.chart_config);
                saveHistory(text);
            }
        } catch (error) {
            removeTypingIndicator(typingId);
            appendMessage(`Hubo un error de red o en el servidor. Revisa si la API corre en el 8080: ${error.message}`, 'system');
        }
    });

    async function fetchDatasets() {
        try {
            const response = await fetch(`${API_URL}/datasets`);
            if (!response.ok) return;
            const datasets = await response.json();
            
            if (datasets && datasets.length > 0) {
                datasetsList.innerHTML = '';
                datasets.forEach(ds => {
                    const li = document.createElement('li');
                    const displayName = (ds.name || `Dataset ${ds.id}`);
                    const rows = ds.rows_count != null ? ds.rows_count.toLocaleString() : '?';
                    const cols = ds.columns_count != null ? ds.columns_count : '?';
                    
                    li.innerHTML = `
                        <span class="status-dot"></span>
                        <div class="ds-info">
                            <span class="ds-name" title="${displayName}">${displayName}</span>
                            <div class="ds-meta">
                                <span>📋 ${rows} filas</span>
                                <span>📐 ${cols} cols</span>
                            </div>
                        </div>
                    `;
                    li.onclick = () => {
                        userInput.value = `Muéstrame las primeras 10 filas del dataset ${displayName}`;
                        chatForm.dispatchEvent(new Event('submit'));
                    };
                    datasetsList.appendChild(li);
                });
            } else {
                datasetsList.innerHTML = `
                    <li class="empty-state">
                        <span class="empty-icon">📂</span>
                        <span class="text-muted small">Sube un CSV para empezar</span>
                    </li>`;
            }
        } catch (error) {
            datasetsList.innerHTML = `
                <li class="empty-state">
                    <span class="empty-icon">⚠️</span>
                    <span class="text-muted small">Error conectando con API</span>
                </li>`;
        }
    }

    function saveHistory(query) {
        let history = JSON.parse(localStorage.getItem('agent3_history') || '[]');
        history.unshift(query);
        if(history.length > 10) history = history.slice(0, 10);
        localStorage.setItem('agent3_history', JSON.stringify(history));
        renderHistory();
    }

    function renderHistory() {
        const hList = document.getElementById('history-list');
        const history = JSON.parse(localStorage.getItem('agent3_history') || '[]');
        
        if (history.length > 0) {
            hList.innerHTML = '';
            history.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `💬 <span class="small" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">${item}</span>`;
                li.onclick = () => { userInput.value = item; userInput.focus(); };
                hList.appendChild(li);
            });
        } else {
            hList.innerHTML = '<p class="text-muted small">No hay historial de preguntas</p>';
        }
    }
    
    renderHistory();

    function appendMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message slide-in`;
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        if (typeof marked !== 'undefined' && sender === 'system') {
            const textWrapper = document.createElement('div');
            textWrapper.innerHTML = marked.parse(text);
            content.appendChild(textWrapper);
        } else {
            const paragraphs = text.split('\n\n').filter(p => p.trim());
            if (paragraphs.length > 0) {
                paragraphs.forEach(p => {
                    const pTag = document.createElement('p');
                    pTag.textContent = p;
                    content.appendChild(pTag);
                });
            } else {
                const pTag = document.createElement('p');
                pTag.textContent = text;
                content.appendChild(pTag);
            }
        }

        div.appendChild(content);
        chatMessages.appendChild(div);
        scrollToBottom();
    }

    function appendSystemMessageWithChart(explanation, chartConfig) {
        const div = document.createElement('div');
        div.className = 'message system-message slide-in';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        if (explanation) {
            if (typeof marked !== 'undefined') {
                const textWrapper = document.createElement('div');
                textWrapper.innerHTML = marked.parse(explanation);
                content.appendChild(textWrapper);
            } else {
                const paragraphs = explanation.split('\n\n').filter(p => p.trim());
                paragraphs.forEach(p => {
                    const pTag = document.createElement('p');
                    pTag.textContent = p;
                    content.appendChild(pTag);
                });
            }
        }

        if (chartConfig && chartConfig.data && chartConfig.data.length > 0) {
            const chartDiv = document.createElement('div');
            const chartId = `chart-${Date.now()}`;
            chartDiv.id = chartId;
            chartDiv.className = 'chart-container';
            content.appendChild(chartDiv);
            
            div.appendChild(content);
            chatMessages.appendChild(div);
            
            // Plot con Plotly
            Plotly.newPlot(chartId, chartConfig.data, chartConfig.layout, {responsive: true, displayModeBar: false});
            
            // Add resize listener to this specific plot
            window.addEventListener('resize', () => {
                Plotly.Plots.resize(chartId);
            });
        } else {
            div.appendChild(content);
            chatMessages.appendChild(div);
        }
        
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = `typing-${Date.now()}`;
        const html = `
            <div id="${id}" class="typing-indicator slide-in">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
