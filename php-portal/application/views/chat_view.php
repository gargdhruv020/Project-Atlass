<?php
defined('BASEPATH') OR exit('No direct script access allowed');
/**
 * Project Atlas - CodeIgniter 3 Market Research Copilot Chat View
 * Renders conversation history, structured citations, conflicts, derived values,
 * human escalation badges, and interactive feedback controls with CSRF & XSS protection.
 */
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Atlas &mdash; Market Research Report Copilot</title>
    <style>
        :root {
            --bg-page: #0f172a;
            --bg-card: #1e293b;
            --bg-chat: #0f172a;
            --bg-user-bubble: #2563eb;
            --bg-ai-bubble: #1e293b;
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-family);
            background: var(--bg-page);
            color: var(--text-primary);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: 320px;
            background: #090d16;
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 16px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }
        .brand-icon {
            width: 34px;
            height: 34px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 18px;
            color: #fff;
        }
        .brand-text h1 {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            letter-spacing: 0.5px;
        }
        .brand-text span {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        /* Client Info Card */
        .client-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            margin-top: 14px;
        }
        .client-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .client-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            background: #1e3a8a;
            color: #93c5fd;
        }
        .client-name {
            font-size: 13px;
            font-weight: 600;
            color: #f1f5f9;
        }
        .client-sub {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
            line-height: 1.4;
        }
        .client-switch-form {
            margin-top: 8px;
            display: flex;
            gap: 6px;
        }
        .client-switch-select {
            flex: 1;
            background: #0f172a;
            color: #f1f5f9;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }
        .client-switch-btn {
            background: #334155;
            color: #fff;
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 12px;
            cursor: pointer;
        }
        .client-switch-btn:hover { background: #475569; }

        /* New Chat Button */
        .btn-new-chat {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #2563eb;
            color: #fff;
            text-decoration: none;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            margin-top: 14px;
            transition: background 0.15s;
        }
        .btn-new-chat:hover { background: #1d4ed8; }

        /* History List */
        .history-section {
            flex: 1;
            overflow-y: auto;
            margin-top: 16px;
        }
        .history-title {
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .history-item {
            display: block;
            padding: 8px 10px;
            color: #cbd5e1;
            text-decoration: none;
            font-size: 12px;
            border-radius: 6px;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            transition: background 0.15s;
        }
        .history-item:hover { background: #1e293b; color: #fff; }
        .history-item.active { background: #1e3a8a; color: #bfdbfe; font-weight: 600; }

        /* Main Chat Container */
        .chat-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }

        /* Top Bar */
        .top-bar {
            height: 56px;
            border-bottom: 1px solid var(--border-color);
            background: #090d16;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
        }
        .top-title {
            font-size: 14px;
            font-weight: 600;
            color: #f1f5f9;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-green);
        }

        /* Messages Area */
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .welcome-hero {
            text-align: center;
            margin: auto;
            max-width: 580px;
            padding: 40px 20px;
        }
        .welcome-hero h2 {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #fff;
        }
        .welcome-hero p {
            font-size: 14px;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .suggestions-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            text-align: left;
        }
        .suggestion-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 14px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .suggestion-card:hover {
            border-color: var(--accent-blue);
            transform: translateY(-1px);
        }
        .suggestion-card strong {
            display: block;
            font-size: 12px;
            color: #93c5fd;
            margin-bottom: 4px;
        }
        .suggestion-card span {
            font-size: 12px;
            color: #cbd5e1;
            line-height: 1.4;
        }

        /* Message Bubbles */
        .message-row {
            display: flex;
            gap: 12px;
            max-width: 85%;
        }
        .message-row.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }
        .message-row.assistant {
            align-self: flex-start;
        }
        .avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
        }
        .avatar.user { background: #3b82f6; color: #fff; }
        .avatar.assistant { background: #6366f1; color: #fff; }

        .bubble-content {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .bubble {
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.6;
            color: #f1f5f9;
        }
        .message-row.user .bubble {
            background: var(--bg-user-bubble);
            border-bottom-right-radius: 2px;
        }
        .message-row.assistant .bubble {
            background: var(--bg-ai-bubble);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: 2px;
        }

        /* Structured Cards */
        .meta-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin-top: 4px;
        }
        .badge-confidence {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .badge-escalated {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .badge-conflict {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        /* Citations Panel */
        .citations-box {
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 8px;
        }
        .citations-header {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .citation-item {
            font-size: 12px;
            padding: 6px 0;
            border-bottom: 1px solid #1e293b;
            color: #cbd5e1;
        }
        .citation-item:last-child { border-bottom: none; }
        .citation-tag {
            font-weight: 700;
            color: #60a5fa;
            margin-right: 6px;
        }
        .citation-detail {
            color: #94a3b8;
            font-size: 11px;
        }

        /* Conflict Alert Box */
        .conflict-box {
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 8px;
        }
        .conflict-header {
            font-size: 12px;
            font-weight: 700;
            color: #fbbf24;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }
        .conflict-desc {
            font-size: 12px;
            color: #fef3c7;
            line-height: 1.4;
        }

        /* Derived Values Box */
        .derived-box {
            background: rgba(59, 130, 246, 0.08);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 8px;
        }
        .derived-header {
            font-size: 12px;
            font-weight: 700;
            color: #93c5fd;
            margin-bottom: 4px;
        }
        .derived-val {
            font-size: 12px;
            color: #e2e8f0;
            font-family: monospace;
        }

        /* Feedback Buttons */
        .feedback-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
        }
        .feedback-btn {
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-muted);
            padding: 3px 8px;
            font-size: 11px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.15s;
        }
        .feedback-btn:hover {
            border-color: #64748b;
            color: #f1f5f9;
        }
        .feedback-btn.active-up {
            background: rgba(16, 185, 129, 0.2);
            border-color: var(--accent-green);
            color: #34d399;
        }
        .feedback-btn.active-down {
            background: rgba(239, 68, 68, 0.2);
            border-color: var(--accent-red);
            color: #f87171;
        }

        /* Input Bar */
        .input-bar {
            padding: 16px 24px;
            background: #090d16;
            border-top: 1px solid var(--border-color);
        }
        .input-form {
            display: flex;
            gap: 12px;
            position: relative;
        }
        .chat-textarea {
            flex: 1;
            background: #1e293b;
            color: #fff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 14px;
            font-family: inherit;
            resize: none;
            height: 48px;
            max-height: 120px;
            line-height: 1.4;
            outline: none;
            transition: border-color 0.15s;
        }
        .chat-textarea:focus { border-color: var(--accent-blue); }
        .send-btn {
            background: #2563eb;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 0 20px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: background 0.15s;
        }
        .send-btn:hover { background: #1d4ed8; }
        .send-btn:disabled { background: #334155; color: #64748b; cursor: not-allowed; }

        /* Loading Spinner */
        .loading-bubble {
            display: none;
            align-self: flex-start;
            gap: 12px;
        }
        .typing-dots {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 14px 18px;
            background: var(--bg-ai-bubble);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }
        .dot {
            width: 7px;
            height: 7px;
            background: #64748b;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1.0); }
        }

        /* Error Notification Banner */
        .alert-banner {
            display: none;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
            padding: 10px 16px;
            border-radius: 6px;
            margin: 0 24px 12px;
            font-size: 13px;
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <aside class="sidebar">
        <div class="brand">
            <div class="brand-icon">A</div>
            <div class="brand-text">
                <h1>PROJECT ATLAS</h1>
                <span>Market Intelligence Copilot</span>
            </div>
        </div>

        <!-- Client Identity Card -->
        <div class="client-card">
            <div class="client-header">
                <span class="client-name"><?php echo html_escape($client['company']); ?></span>
                <span class="client-badge"><?php echo html_escape($client_id); ?></span>
            </div>
            <p class="client-sub">
                <strong>Contact:</strong> <?php echo html_escape($client['contact_email']); ?><br>
                <strong>Entitlements:</strong> <?php echo html_escape($client['purchased_reports'] ?: 'Public reports only'); ?>
            </p>

            <!-- Server-Side Client Switcher -->
            <form action="<?php echo site_url('chat/switch_client'); ?>" method="post" class="client-switch-form">
                <input type="hidden" name="<?php echo $csrf_token_name; ?>" value="<?php echo $csrf_hash; ?>">
                <select name="client_id" class="client-switch-select">
                    <?php foreach ($all_clients as $cl): ?>
                        <option value="<?php echo html_escape($cl['id']); ?>" <?php echo ($cl['id'] === $client_id) ? 'selected' : ''; ?>>
                            <?php echo html_escape($cl['id'] . ' &mdash; ' . $cl['company']); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
                <button type="submit" class="client-switch-btn">Switch</button>
            </form>
        </div>

        <!-- New Chat Button -->
        <a href="<?php echo site_url('chat/new'); ?>" class="btn-new-chat">
            <span>+</span> New Conversation
        </a>

        <!-- Conversation History -->
        <div class="history-section">
            <div class="history-title">Conversations</div>
            <?php if (empty($conversations)): ?>
                <div style="font-size: 12px; color: var(--text-muted); padding: 8px;">No previous sessions.</div>
            <?php else: ?>
                <?php foreach ($conversations as $c): ?>
                    <a href="<?php echo site_url('chat/c/' . $c['id']); ?>" 
                       class="history-item <?php echo ($c['id'] === $active_conversation_id) ? 'active' : ''; ?>"
                       title="<?php echo html_escape($c['title']); ?>">
                        💬 <?php echo html_escape($c['title']); ?>
                    </a>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>
    </aside>

    <!-- Main Chat Workspace -->
    <main class="chat-main">
        <header class="top-bar">
            <span class="top-title">Session: <?php echo html_escape($conversation['title']); ?></span>
            <div class="status-pill">
                <span class="status-dot"></span>
                <span>FastAPI Backend Active</span>
            </div>
        </header>

        <!-- Error Alert Banner -->
        <div id="errorBanner" class="alert-banner"></div>

        <!-- Chat Messages -->
        <div class="messages-container" id="messagesContainer">
            <?php if (empty($messages)): ?>
                <div class="welcome-hero" id="welcomeHero">
                    <h2>Market Research Intelligence</h2>
                    <p>Ask empirical market questions, project CAGR-based estimates, and analyze report scope differences with full source attribution.</p>
                    <div class="suggestions-grid">
                        <div class="suggestion-card" onclick="sendSuggested('What was the global smart water meter market size in 2024 according to R-101?')">
                            <strong>Market Size Lookup</strong>
                            <span>2024 Smart Water Metering size in R-101</span>
                        </div>
                        <div class="suggestion-card" onclick="sendSuggested('Calculate the projected smart water meter market size in 2026 based on R-101.')">
                            <strong>CAGR Projection</strong>
                            <span>Project 2026 market size using 11.2% growth</span>
                        </div>
                        <div class="suggestion-card" onclick="sendSuggested('What is the smart water meter market size reported in R-102?')">
                            <strong>Methodological Scope</strong>
                            <span>Examine R-102 hardware-only market metrics</span>
                        </div>
                        <div class="suggestion-card" onclick="sendSuggested('Compare 2024 smart water market estimates between R-101 and R-102.')">
                            <strong>Conflict Analysis</strong>
                            <span>Compare scope differences without illegal averaging</span>
                        </div>
                    </div>
                </div>
            <?php else: ?>
                <?php foreach ($messages as $msg): ?>
                    <div class="message-row <?php echo html_escape($msg['sender']); ?>">
                        <div class="avatar <?php echo html_escape($msg['sender']); ?>">
                            <?php echo ($msg['sender'] === 'user') ? 'U' : 'AI'; ?>
                        </div>
                        <div class="bubble-content">
                            <div class="bubble">
                                <?php echo nl2br(html_escape($msg['content'])); ?>

                                <!-- Methodological Conflicts -->
                                <?php if (!empty($msg['conflicts'])): ?>
                                    <div class="conflict-box">
                                        <div class="conflict-header">⚠️ Methodological Scope Conflict Detected</div>
                                        <?php foreach ($msg['conflicts'] as $cf): ?>
                                            <div class="conflict-desc">
                                                <strong><?php echo html_escape(isset($cf['metric']) ? $cf['metric'] : 'Conflict'); ?>:</strong>
                                                <?php echo html_escape(isset($cf['description']) ? $cf['description'] : ''); ?>
                                            </div>
                                        <?php endforeach; ?>
                                    </div>
                                <?php endif; ?>

                                <!-- Derived Values -->
                                <?php if (!empty($msg['derived_values'])): ?>
                                    <div class="derived-box">
                                        <div class="derived-header">📊 Calculated Projections (Deterministic)</div>
                                        <?php foreach ($msg['derived_values'] as $dk => $dv): ?>
                                            <div class="derived-val">
                                                <strong><?php echo html_escape($dk); ?>:</strong> <?php echo html_escape(is_array($dv) ? json_encode($dv) : $dv); ?>
                                            </div>
                                        <?php endforeach; ?>
                                    </div>
                                <?php endif; ?>

                                <!-- Citations -->
                                <?php if (!empty($msg['citations'])): ?>
                                    <div class="citations-box">
                                        <div class="citations-header">Authorized Source Citations (<?php echo count($msg['citations']); ?>)</div>
                                        <?php foreach ($msg['citations'] as $cit): ?>
                                            <div class="citation-item">
                                                <span class="citation-tag">[<?php echo html_escape(isset($cit['report_id']) ? $cit['report_id'] : 'DOC'); ?>]</span>
                                                <strong><?php echo html_escape(isset($cit['title']) ? $cit['title'] : (isset($cit['report_title']) ? $cit['report_title'] : 'Report')); ?></strong>
                                                <?php if (!empty($cit['metric'])): ?> &bull; <?php echo html_escape($cit['metric']); ?><?php endif; ?>
                                                <?php if (!empty($cit['period'])): ?> (<?php echo html_escape($cit['period']); ?>)<?php endif; ?>
                                                <?php if (!empty($cit['value'])): ?>: <em><?php echo html_escape($cit['value']); ?></em><?php endif; ?>
                                                <?php if (!empty($cit['page'])): ?><span class="citation-detail"> [Page <?php echo intval($cit['page']); ?>]</span><?php endif; ?>
                                            </div>
                                        <?php endforeach; ?>
                                    </div>
                                <?php endif; ?>
                            </div>

                            <!-- Badges and Feedback for Assistant Messages -->
                            <?php if ($msg['sender'] === 'assistant'): ?>
                                <div class="meta-badges">
                                    <?php if ($msg['confidence'] !== null): ?>
                                        <span class="badge-confidence">Confidence: <?php echo round($msg['confidence'] * 100); ?>%</span>
                                    <?php endif; ?>

                                    <?php if ($msg['escalated']): ?>
                                        <span class="badge-escalated">
                                            🚨 Escalated to Analyst <?php echo !empty($msg['escalation_ticket']) ? '(' . html_escape($msg['escalation_ticket']) . ')' : ''; ?>
                                        </span>
                                    <?php endif; ?>

                                    <!-- Feedback Controls -->
                                    <div class="feedback-actions">
                                        <button class="feedback-btn <?php echo ($msg['feedback_rating'] === 'thumbs_up') ? 'active-up' : ''; ?>"
                                                onclick="submitFeedback(<?php echo intval($msg['id']); ?>, 'thumbs_up', this)">
                                            👍 Helpful
                                        </button>
                                        <button class="feedback-btn <?php echo ($msg['feedback_rating'] === 'thumbs_down') ? 'active-down' : ''; ?>"
                                                onclick="submitFeedback(<?php echo intval($msg['id']); ?>, 'thumbs_down', this)">
                                            👎 Unhelpful
                                        </button>
                                    </div>
                                </div>
                            <?php endif; ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            <?php endif; ?>

            <!-- Loading Skeleton -->
            <div class="message-row assistant loading-bubble" id="loadingBubble">
                <div class="avatar assistant">AI</div>
                <div class="typing-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        </div>

        <!-- Chat Input Form -->
        <div class="input-bar">
            <form id="chatForm" class="input-form" onsubmit="handleSend(event)">
                <input type="hidden" id="csrfToken" name="<?php echo $csrf_token_name; ?>" value="<?php echo $csrf_hash; ?>">
                <input type="hidden" id="conversationId" value="<?php echo html_escape($active_conversation_id); ?>">
                
                <textarea id="questionInput" 
                          class="chat-textarea" 
                          placeholder="Ask a market research question (e.g. 2024 water meter market size, 2026 CAGR projection)..."
                          onkeydown="handleKeyDown(event)"
                          required></textarea>
                
                <button type="submit" id="sendBtn" class="send-btn">
                    <span>Send</span> &rarr;
                </button>
            </form>
        </div>
    </main>

    <script>
        const csrfTokenName = '<?php echo $csrf_token_name; ?>';
        let currentCsrfHash = '<?php echo $csrf_hash; ?>';
        const activeConversationId = '<?php echo $active_conversation_id; ?>';
        const sendUrl = '<?php echo site_url("chat/send"); ?>';
        const feedbackUrl = '<?php echo site_url("chat/feedback"); ?>';

        function escapeHtml(str) {
            if (!str) return '';
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function scrollToBottom() {
            const container = document.getElementById('messagesContainer');
            container.scrollTop = container.scrollHeight;
        }

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('chatForm').dispatchEvent(new Event('submit', { cancelable: true }));
            }
        }

        function sendSuggested(query) {
            document.getElementById('questionInput').value = query;
            document.getElementById('chatForm').dispatchEvent(new Event('submit', { cancelable: true }));
        }

        function showError(msg) {
            const banner = document.getElementById('errorBanner');
            banner.textContent = msg;
            banner.style.display = 'block';
            setTimeout(() => { banner.style.display = 'none'; }, 8000);
        }

        function appendUserMessage(text) {
            const welcome = document.getElementById('welcomeHero');
            if (welcome) welcome.style.display = 'none';

            const container = document.getElementById('messagesContainer');
            const row = document.createElement('div');
            row.className = 'message-row user';
            row.innerHTML = `
                <div class="avatar user">U</div>
                <div class="bubble-content">
                    <div class="bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
                </div>
            `;
            container.insertBefore(row, document.getElementById('loadingBubble'));
            scrollToBottom();
        }

        function appendAssistantMessage(data) {
            const container = document.getElementById('messagesContainer');
            const row = document.createElement('div');
            row.className = 'message-row assistant';

            let citationsHtml = '';
            if (data.citations && data.citations.length > 0) {
                let items = data.citations.map(c => `
                    <div class="citation-item">
                        <span class="citation-tag">[${escapeHtml(c.report_id || 'DOC')}]</span>
                        <strong>${escapeHtml(c.title || c.report_title || 'Report')}</strong>
                        ${c.metric ? ' &bull; ' + escapeHtml(c.metric) : ''}
                        ${c.period ? ' (' + escapeHtml(c.period) + ')' : ''}
                        ${c.value ? ': <em>' + escapeHtml(c.value) + '</em>' : ''}
                        ${c.page ? '<span class="citation-detail"> [Page ' + escapeHtml(String(c.page)) + ']</span>' : ''}
                    </div>
                `).join('');
                citationsHtml = `
                    <div class="citations-box">
                        <div class="citations-header">Authorized Source Citations (${data.citations.length})</div>
                        ${items}
                    </div>
                `;
            }

            let conflictsHtml = '';
            if (data.conflicts && data.conflicts.length > 0) {
                let items = data.conflicts.map(cf => `
                    <div class="conflict-desc">
                        <strong>${escapeHtml(cf.metric || 'Conflict')}:</strong>
                        ${escapeHtml(cf.description || '')}
                    </div>
                `).join('');
                conflictsHtml = `
                    <div class="conflict-box">
                        <div class="conflict-header">⚠️ Methodological Scope Conflict Detected</div>
                        ${items}
                    </div>
                `;
            }

            let derivedHtml = '';
            if (data.derived_values && Object.keys(data.derived_values).length > 0) {
                let items = Object.entries(data.derived_values).map(([k, v]) => `
                    <div class="derived-val">
                        <strong>${escapeHtml(k)}:</strong> ${escapeHtml(typeof v === 'object' ? JSON.stringify(v) : String(v))}
                    </div>
                `).join('');
                derivedHtml = `
                    <div class="derived-box">
                        <div class="derived-header">📊 Calculated Projections (Deterministic)</div>
                        ${items}
                    </div>
                `;
            }

            let confidenceHtml = '';
            if (data.confidence !== undefined && data.confidence !== null) {
                confidenceHtml = `<span class="badge-confidence">Confidence: ${Math.round(data.confidence * 100)}%</span>`;
            }

            let escalatedHtml = '';
            if (data.escalated) {
                const ticketText = data.escalation_ticket ? `(${escapeHtml(data.escalation_ticket)})` : '';
                escalatedHtml = `<span class="badge-escalated">🚨 Escalated to Analyst ${ticketText}</span>`;
            }

            let feedbackHtml = '';
            if (data.message_id) {
                feedbackHtml = `
                    <div class="feedback-actions">
                        <button class="feedback-btn" onclick="submitFeedback(${data.message_id}, 'thumbs_up', this)">
                            👍 Helpful
                        </button>
                        <button class="feedback-btn" onclick="submitFeedback(${data.message_id}, 'thumbs_down', this)">
                            👎 Unhelpful
                        </button>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="avatar assistant">AI</div>
                <div class="bubble-content">
                    <div class="bubble">
                        ${escapeHtml(data.answer).replace(/\n/g, '<br>')}
                        ${conflictsHtml}
                        ${derivedHtml}
                        ${citationsHtml}
                    </div>
                    <div class="meta-badges">
                        ${confidenceHtml}
                        ${escalatedHtml}
                        ${feedbackHtml}
                    </div>
                </div>
            `;

            container.insertBefore(row, document.getElementById('loadingBubble'));
            scrollToBottom();
        }

        async function handleSend(e) {
            e.preventDefault();
            const input = document.getElementById('questionInput');
            const question = input.value.trim();
            if (!question) return;

            const sendBtn = document.getElementById('sendBtn');
            const loader = document.getElementById('loadingBubble');

            appendUserMessage(question);
            input.value = '';
            input.disabled = true;
            sendBtn.disabled = true;
            loader.style.display = 'flex';
            scrollToBottom();

            const formData = new FormData();
            formData.append(csrfTokenName, currentCsrfHash);
            formData.append('question', question);
            formData.append('conversation_id', activeConversationId);

            try {
                const resp = await fetch(sendUrl, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: formData
                });

                const data = await resp.json();

                if (data.csrf_token) {
                    currentCsrfHash = data.csrf_token;
                    document.getElementById('csrfToken').value = data.csrf_token;
                }

                if (data.success) {
                    appendAssistantMessage(data);
                } else {
                    const fallback = data.fallback_answer || `⚠️ Service Notice: ${data.error || 'The research service is temporarily unavailable.'}`;
                    appendAssistantMessage({
                        answer: fallback,
                        escalated: true,
                        message_id: data.message_id
                    });
                    if (data.error) showError(data.error);
                }
            } catch (err) {
                showError('Network connection failed. Please ensure the server is running.');
                appendAssistantMessage({
                    answer: '⚠️ Connection Error: Unable to reach the Project Atlas portal service. Please try again.',
                    escalated: true
                });
            } finally {
                loader.style.display = 'none';
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
                scrollToBottom();
            }
        }

        async function submitFeedback(messageId, rating, btn) {
            const formData = new FormData();
            formData.append(csrfTokenName, currentCsrfHash);
            formData.append('message_id', messageId);
            formData.append('conversation_id', activeConversationId);
            formData.append('rating', rating);

            try {
                const resp = await fetch(feedbackUrl, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: formData
                });
                const res = await resp.json();

                if (res.csrf_token) {
                    currentCsrfHash = res.csrf_token;
                    document.getElementById('csrfToken').value = res.csrf_token;
                }

                if (res.success) {
                    const parent = btn.parentElement;
                    const buttons = parent.querySelectorAll('.feedback-btn');
                    buttons.forEach(b => b.classList.remove('active-up', 'active-down'));

                    if (rating === 'thumbs_up') {
                        btn.classList.add('active-up');
                    } else {
                        btn.classList.add('active-down');
                    }
                } else {
                    showError(res.error || 'Failed to submit feedback.');
                }
            } catch (err) {
                showError('Failed to record feedback due to a network error.');
            }
        }

        scrollToBottom();
    </script>
</body>
</html>
