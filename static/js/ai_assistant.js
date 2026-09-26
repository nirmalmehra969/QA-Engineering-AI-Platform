// AI QA Copilot Assistant Client
class AICopilotAssistant {
    constructor() {
        this.panel = document.getElementById('ai-assistant-panel');
        this.toggleBtn = document.getElementById('toggle-copilot-btn');
        this.closeBtn = document.getElementById('close-copilot-btn');
        this.messagesContainer = document.getElementById('copilot-messages');
        this.inputForm = document.getElementById('copilot-form');
        this.textInput = document.getElementById('copilot-input');
        this.quickChips = document.querySelectorAll('.quick-chip');
        this.init();
    }

    init() {
        this.toggleBtn?.addEventListener('click', () => this.togglePanel());
        this.closeBtn?.addEventListener('click', () => this.closePanel());

        this.inputForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        this.quickChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const prompt = chip.getAttribute('data-prompt');
                if (prompt) {
                    this.textInput.value = prompt;
                    this.sendMessage();
                }
            });
        });
    }

    togglePanel() {
        if (this.panel.classList.contains('closed')) {
            this.panel.classList.remove('closed');
        } else {
            this.panel.classList.add('closed');
        }
    }

    closePanel() {
        this.panel.classList.add('closed');
    }

    async sendMessage() {
        const text = this.textInput.value.trim();
        if (!text) return;

        // Append User Message
        this.appendMessage('user', text);
        this.textInput.value = '';

        // Add Thinking Bubble
        const thinkingBubble = this.appendMessage('ai', 'Analyzing test strategy...');

        try {
            const res = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            // Update bubble with AI reply & provider tag
            const providerTag = data.display_name ? `<div class="msg-provider-tag" style="font-size:0.75rem;color:var(--neon-cyan);margin-bottom:4px;opacity:0.85;">⚡ ${data.display_name}</div>` : '';
            thinkingBubble.querySelector('.msg-bubble').innerHTML = `${providerTag}${this.formatMarkdown(data.reply)}`;
            this.scrollToBottom();
        } catch (err) {
            thinkingBubble.querySelector('.msg-bubble').textContent = "I encountered an issue connecting to the AI backend.";
        }
    }

    appendMessage(sender, text, providerLabel = '') {
        const msg = document.createElement('div');
        msg.className = `copilot-msg ${sender}-msg`;
        const providerHeader = providerLabel ? `<div class="msg-provider-tag" style="font-size:0.75rem;color:var(--neon-cyan);margin-bottom:4px;opacity:0.85;">⚡ ${providerLabel}</div>` : '';
        msg.innerHTML = `
            <div class="msg-avatar">${sender === 'ai' ? 'AI:' : 'You:'}</div>
            <div class="msg-bubble">${providerHeader}${this.formatMarkdown(text)}</div>
        `;
        this.messagesContainer.appendChild(msg);
        this.scrollToBottom();
        return msg;
    }

    formatMarkdown(text) {
        if (!text) return '';
        // Escape HTML
        let formatted = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Code blocks
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Bullet points
        formatted = formatted.replace(/^• (.*$)/gim, '<li>$1</li>');
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br/>');
        return formatted;
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AICopilotAssistant();
});
