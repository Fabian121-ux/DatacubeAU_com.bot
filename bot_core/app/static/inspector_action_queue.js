(() => {
  'use strict';

  const allowedAction = 'reply_now';

  function actionQueueUrl(item) {
    const chatId = String(item?.whatsapp_id || '').trim();
    if (!chatId) return null;
    const params = new URLSearchParams({ chat_id: chatId, action: allowedAction });
    return `/admin/action-queue?${params.toString()}`;
  }

  window.zinaInspectorActionQueueUrl = actionQueueUrl;

  window.loadConversationInspector = async function loadConversationInspectorWithActionQueue() {
    try {
      const d = await api('/admin/conversation-inspector?limit=50');
      const table = document.getElementById('conversationInspectorTable');
      if (!d.items.length) {
        table.innerHTML = '<em>No conversations inspected yet.</em>';
        return;
      }

      table.innerHTML = `<table>
        <thead><tr><th>Time</th><th>User</th><th>Message</th><th>Intent</th><th>Route</th><th>Sources Used</th><th>Hits</th><th>Fallback</th><th>Reason</th><th>Final Response</th><th>Actions</th></tr></thead>
        <tbody>${d.items.map(m => {
          const queueUrl = actionQueueUrl(m);
          return `<tr>
            <td style="white-space:nowrap">${new Date(m.created_at).toLocaleString()}</td>
            <td><strong>${esc(m.user_name || 'Unknown')}</strong><br><small>${esc(m.phone_number || m.whatsapp_id || '—')}</small></td>
            <td title="${esc(m.message || m.question || '')}">${esc((m.message || m.question || '').substring(0,70))}</td>
            <td><span class="badge badge-gray">${esc(m.intent || m.router_analytics?.intent || 'unknown')}</span></td>
            <td><span class="badge badge-purple">${esc(m.selected_source || m.selected_route || m.decision_type || '—')}</span><br><small>${esc(m.topic || '—')}</small></td>
            <td class="mono">
              I:${m.identity_used ? '1' : '0'} M:${m.memory_used ? '1' : '0'} F:${m.faq_used ? '1' : '0'}<br>
              K:${m.knowledge_used ? '1' : '0'} P:${m.project_context ? '1' : '0'}
            </td>
            <td class="mono">M:${m.memory_hits || 0}<br>F:${m.faq_hits || 0}<br>K:${m.knowledge_hits || 0}<br>I:${m.internet_hits || 0}<br>AI:${m.ai_hits || 0}</td>
            <td title="${esc(m.fallback_reason || '')}">${esc((m.fallback_reason || '—').substring(0,50))}</td>
            <td title="${esc(m.reason || '')}">${esc((m.reason || '').substring(0,70))}</td>
            <td title="${esc(m.final_response || '')}">${esc((m.final_response || '—').substring(0,90))}</td>
            <td>${queueUrl ? `<a class="btn btn-ghost btn-sm" href="${esc(queueUrl)}">Action Queue</a>` : '<span class="badge badge-gray">DM only</span>'}</td>
          </tr>`;
        }).join('')}</tbody></table>`;
    } catch (_) {}
  };
})();
