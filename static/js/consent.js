// Consent UI logic: set consent, export and delete data via API endpoints

async function getCsrfToken() {
    // If the app uses CSRF tokens, fetch or read it here. For now assume session auth and same-site cookies.
    return null;
}

async function setConsent(consent) {
    try {
        const resp = await fetch('/api/user/consent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ consent: !!consent })
        });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        showFeedback('Consentimiento actualizado.');
        return data;
    } catch (err) {
        console.error('Error setting consent', err);
        showFeedback('Error al actualizar consentimiento. Revisa la consola.');
    }
}

async function exportData() {
    try {
        showFeedback('Preparando exportación...');
        const resp = await fetch('/api/user/data-export', { method: 'GET' });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(text || 'Error en export');
        }
        const blob = await resp.blob();
        const filename = 'jp_ia_user_data_export.json';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showFeedback('Exportación descargada.');
    } catch (err) {
        console.error('Export error', err);
        showFeedback('Error al exportar datos.');
    }
}

async function deleteData() {
    try {
        if (!confirm('¿Estás seguro? Esta acción anonimizará o eliminará tus datos y no se puede revertir fácilmente.')) return;
        showFeedback('Eliminando datos...');
        const resp = await fetch('/api/user/data-delete', { method: 'DELETE' });
        if (!resp.ok) throw new Error(await resp.text());
        showFeedback('Tus datos han sido eliminados o anonimizados.');
    } catch (err) {
        console.error('Delete error', err);
        showFeedback('Error al eliminar datos.');
    }
}

function showFeedback(msg) {
    const el = document.getElementById('privacyFeedback');
    if (!el) return;
    el.textContent = msg;
}

function bindUI() {
    const checkbox = document.getElementById('memoryConsent');
    const exportBtn = document.getElementById('exportDataBtn');
    const deleteBtn = document.getElementById('deleteDataBtn');

    if (checkbox) {
        checkbox.addEventListener('change', async (e) => {
            await setConsent(e.target.checked);
        });
    }
    if (exportBtn) exportBtn.addEventListener('click', exportData);
    if (deleteBtn) deleteBtn.addEventListener('click', deleteData);

    // Optionally, fetch current consent state to initialize checkbox
    (async function init() {
        try {
            const resp = await fetch('/api/user/consent', { method: 'GET' });
            if (!resp.ok) return;
            const json = await resp.json();
            if (json && typeof json.consent !== 'undefined') {
                if (checkbox) checkbox.checked = !!json.consent;
            }
        } catch (err) {
            // ignore
        }
    })();
}

// Attach when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindUI);
} else {
    bindUI();
}
