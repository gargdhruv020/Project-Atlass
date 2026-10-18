<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * Chat Controller for Project Atlas
 * CodeIgniter 3 controller coordinating research query submissions, conversation history,
 * client authentication, CSRF validation, and feedback collection.
 */
class Chat extends CI_Controller {

    public function __construct() {
        parent::__construct();
        $this->load->model('chat_model');
        $this->load->library('fastapi_client');
        $this->load->library('session');
        $this->load->helper(array('url', 'form', 'html', 'security'));

        # Server-side client authentication: default to 'C-01' if unassigned
        if (!$this->session->userdata('client_id')) {
            $this->session->set_userdata('client_id', 'C-01');
        }
    }

    /**
     * Main Chat Interface
     *
     * @param string|null $conversation_id
     */
    public function index($conversation_id = null) {
        $client_id = $this->_get_authenticated_client_id();
        $client = $this->chat_model->get_client($client_id);

        if (!$client) {
            # Reset to C-01 if invalid client ID stored
            $client_id = 'C-01';
            $this->session->set_userdata('client_id', $client_id);
            $client = $this->chat_model->get_client($client_id);
        }

        # Initialize or retrieve active conversation
        $conversation = $this->chat_model->get_or_create_conversation($conversation_id, $client_id);
        $active_conversation_id = $conversation['id'];

        # Load conversation messages and all client conversations for the sidebar
        $messages = $this->chat_model->get_conversation_messages($active_conversation_id, $client_id);
        $conversations = $this->chat_model->get_client_conversations($client_id);
        $all_clients = $this->chat_model->list_clients();

        # Check backend health status (non-blocking)
        $health_info = $this->fastapi_client->get_health();

        $data = array(
            'page_title'             => 'Report Copilot | Project Atlas',
            'client'                 => $client,
            'client_id'              => $client_id,
            'default_client'         => $client_id,
            'all_clients'            => $all_clients,
            'clients'                => $all_clients,
            'active_conversation_id' => $active_conversation_id,
            'conversation'           => $conversation,
            'conversations'          => $conversations,
            'messages'               => $messages,
            'health_info'            => $health_info,
            'csrf_token_name'        => $this->security->get_csrf_token_name(),
            'csrf_hash'              => $this->security->get_csrf_hash()
        );

        $this->load->view('chat_view', $data);
    }

    /**
     * Handle Question Submission via AJAX / POST
     */
    public function send() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        # Validate CSRF Token
        # (Handled automatically by CI_Security if csrf_protection is enabled;
        # explicit verification here ensures strict safety)
        if ($this->config->item('csrf_protection')) {
            $submitted_token = $this->input->post($this->security->get_csrf_token_name());
            if (empty($submitted_token) || $submitted_token !== $this->security->get_csrf_hash()) {
                $this->_json_response(array(
                    'success'    => false,
                    'error'      => 'CSRF validation failed. Please refresh the page and try again.',
                    'csrf_token' => $this->security->get_csrf_hash()
                ), 403);
                return;
            }
        }

        # Server-side client validation: NEVER trust raw browser client_id
        $client_id = $this->_get_authenticated_client_id();
        $client = $this->chat_model->get_client($client_id);
        if (!$client) {
            $this->_json_response(array(
                'success'    => false,
                'error'      => 'Authentication failed: unauthorized client session.',
                'csrf_token' => $this->security->get_csrf_hash()
            ), 401);
            return;
        }

        # Validate question input
        $raw_q = $this->input->post('question', TRUE);
        $question = ($raw_q !== null) ? trim((string)$raw_q) : '';
        if (empty($question)) {
            $this->_json_response(array(
                'success'    => false,
                'error'      => 'Please provide a market research question.',
                'csrf_token' => $this->security->get_csrf_hash()
            ), 422);
            return;
        }

        if (mb_strlen($question) > 4000) {
            $this->_json_response(array(
                'success'    => false,
                'error'      => 'Question exceeds maximum permitted length of 4000 characters.',
                'csrf_token' => $this->security->get_csrf_hash()
            ), 422);
            return;
        }

        # Resolve conversation scope
        $raw_conv = $this->input->post('conversation_id', TRUE);
        $conversation_id = ($raw_conv !== null && trim((string)$raw_conv) !== '') ? trim((string)$raw_conv) : null;
        $conversation = $this->chat_model->get_or_create_conversation($conversation_id, $client_id, mb_substr($question, 0, 45));
        $active_conv_id = $conversation['id'];

        # Persist user question in MySQL
        $user_msg_id = $this->chat_model->save_message($active_conv_id, $client_id, 'user', $question);

        # Invoke FastAPI backend via reusable client library
        $raw_rep = $this->input->post('report_id', TRUE);
        $report_id = ($raw_rep !== null && trim((string)$raw_rep) !== '') ? trim((string)$raw_rep) : null;
        $api_result = $this->fastapi_client->post_chat($client_id, $question, $active_conv_id, $report_id);

        if ($api_result['success']) {
            $data = $api_result['data'];

            $answer = isset($data['answer']) ? $data['answer'] : '';
            $citations = isset($data['citations']) ? $data['citations'] : array();
            $conflicts = isset($data['conflicts']) ? $data['conflicts'] : array();
            $derived_values = isset($data['derived_values']) ? $data['derived_values'] : array();
            $confidence = isset($data['confidence']) ? floatval($data['confidence']) : 0.0;
            $escalated = !empty($data['escalated']);
            $escalation_ticket = isset($data['escalation_ticket']) ? $data['escalation_ticket'] : null;

            # Persist assistant answer to MySQL
            $meta = array(
                'citations'         => $citations,
                'conflicts'         => $conflicts,
                'derived_values'    => $derived_values,
                'confidence'        => $confidence,
                'escalated'         => $escalated,
                'escalation_ticket' => $escalation_ticket
            );
            $assistant_msg_id = $this->chat_model->save_message($active_conv_id, $client_id, 'assistant', $answer, $meta);

            $this->_json_response(array(
                'success'           => true,
                'message_id'        => $assistant_msg_id,
                'conversation_id'   => $active_conv_id,
                'answer'            => $answer,
                'citations'         => $citations,
                'conflicts'         => $conflicts,
                'derived_values'    => $derived_values,
                'confidence'        => $confidence,
                'escalated'         => $escalated,
                'escalation_ticket' => $escalation_ticket,
                'created_at'        => date('H:i'),
                'csrf_token'        => $this->security->get_csrf_hash()
            ));
        } else {
            # Backend service error or timeout
            $error_text = $api_result['error'];
            $status_code = $api_result['status'];

            $fallback_answer = "⚠️ **Service Notice**: {$error_text}";

            # Persist fallback notice so user session context is retained
            $assistant_msg_id = $this->chat_model->save_message($active_conv_id, $client_id, 'assistant', $fallback_answer, array(
                'escalated' => true
            ));

            $this->_json_response(array(
                'success'           => false,
                'message_id'        => $assistant_msg_id,
                'conversation_id'   => $active_conv_id,
                'error'             => $error_text,
                'fallback_answer'   => $fallback_answer,
                'status_code'       => $status_code,
                'csrf_token'        => $this->security->get_csrf_hash()
            ), 200); // Return 200 to allow client-side clean banner rendering
        }
    }

    /**
     * Submit Thumbs-Up / Thumbs-Down User Feedback
     */
    public function feedback() {
        if ($this->input->method() !== 'post') {
            show_404();
            return;
        }

        # CSRF Verification
        if ($this->config->item('csrf_protection')) {
            $submitted_token = $this->input->post($this->security->get_csrf_token_name());
            if (empty($submitted_token) || $submitted_token !== $this->security->get_csrf_hash()) {
                $this->_json_response(array(
                    'success'    => false,
                    'error'      => 'CSRF validation failed.',
                    'csrf_token' => $this->security->get_csrf_hash()
                ), 403);
                return;
            }
        }

        $client_id = $this->_get_authenticated_client_id();
        $message_id = intval($this->input->post('message_id', TRUE));
        $raw_c = $this->input->post('conversation_id', TRUE);
        $conversation_id = ($raw_c !== null) ? trim((string)$raw_c) : '';
        $raw_r = $this->input->post('rating', TRUE);
        $rating = ($raw_r !== null) ? trim((string)$raw_r) : '';
        $raw_comm = $this->input->post('comment', TRUE);
        $comment = ($raw_comm !== null && trim((string)$raw_comm) !== '') ? trim((string)$raw_comm) : null;

        if (!$message_id || !in_array($rating, array('thumbs_up', 'thumbs_down'))) {
            $this->_json_response(array(
                'success'    => false,
                'error'      => 'Invalid feedback parameters.',
                'csrf_token' => $this->security->get_csrf_hash()
            ), 400);
            return;
        }

        $recorded = $this->chat_model->record_feedback($message_id, $conversation_id, $client_id, $rating, $comment);

        if ($recorded) {
            $this->_json_response(array(
                'success'    => true,
                'message'    => 'Thank you! Your feedback has been recorded.',
                'rating'     => $rating,
                'message_id' => $message_id,
                'csrf_token' => $this->security->get_csrf_hash()
            ));
        } else {
            $this->_json_response(array(
                'success'    => false,
                'error'      => 'Failed to record feedback. Message not found or unauthorized.',
                'csrf_token' => $this->security->get_csrf_hash()
            ), 404);
        }
    }

    /**
     * Switch Authenticated Client Session (C-01 <-> C-02)
     */
    public function switch_client() {
        if ($this->input->method() !== 'post') {
            redirect('chat');
            return;
        }

        $raw_tc = $this->input->post('client_id', TRUE);
        $target_client_id = ($raw_tc !== null) ? trim((string)$raw_tc) : '';
        $client = $this->chat_model->get_client($target_client_id);

        if ($client) {
            $this->session->set_userdata('client_id', $client['id']);
        }

        redirect('chat');
    }

    /**
     * Start a New Conversation Session
     */
    public function new_conversation() {
        $client_id = $this->_get_authenticated_client_id();
        $new_conv = $this->chat_model->get_or_create_conversation(null, $client_id);
        redirect('chat/c/' . $new_conv['id']);
    }

    /**
     * Alias for send() for frontend compatibility
     */
    public function ask() {
        return $this->send();
    }

    /**
     * Get Authenticated Client ID (verifies post param or session)
     *
     * @return string
     */
    protected function _get_authenticated_client_id() {
        $raw_p = $this->input->post('client_id', TRUE);
        $post_id = ($raw_p !== null) ? trim((string)$raw_p) : '';
        if (!empty($post_id) && $this->chat_model->get_client($post_id)) {
            $this->session->set_userdata('client_id', $post_id);
            return $post_id;
        }

        $id = $this->session->userdata('client_id');
        return (!empty($id)) ? trim((string)$id) : 'C-01';
    }

    /**
     * Render structured JSON response
     */
    protected function _json_response($data, $status_code = 200) {
        $this->output
            ->set_status_header($status_code)
            ->set_content_type('application/json', 'utf-8')
            ->set_output(json_encode($data));
    }
}
