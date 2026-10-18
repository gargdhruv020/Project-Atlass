<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * Chat_model for CodeIgniter 3
 * Handles MySQL persistence for client identities, multi-turn conversations,
 * chat message history with structured AI metadata, and user feedback.
 */
class Chat_model extends CI_Model {

    public function __construct() {
        parent::__construct();
        $this->load->database();
    }

    /**
     * Retrieve client profile by ID
     *
     * @param string $client_id
     * @return array|null
     */
    public function get_client($client_id) {
        $query = $this->db->get_where('clients', array('id' => $client_id), 1);
        return $query->row_array();
    }

    /**
     * List all registered clients for switching / authorization
     *
     * @return array
     */
    public function list_clients() {
        $this->db->order_by('id', 'ASC');
        $query = $this->db->get('clients');
        return $query->result_array();
    }

    /**
     * Get or create a conversation for the given client
     *
     * @param string|null $conversation_id
     * @param string $client_id
     * @param string $initial_title
     * @return array Conversation record
     */
    public function get_or_create_conversation($conversation_id, $client_id, $initial_title = 'New Market Research') {
        if (!empty($conversation_id)) {
            $query = $this->db->get_where('conversations', array('id' => $conversation_id, 'client_id' => $client_id), 1);
            $existing = $query->row_array();
            if ($existing) {
                return $existing;
            }
        }

        # Generate new conversation ID (UUID v4)
        $new_id = $this->_generate_uuid();
        $data = array(
            'id'         => $new_id,
            'client_id'  => $client_id,
            'title'      => $initial_title,
            'created_at' => date('Y-m-d H:i:s'),
            'updated_at' => date('Y-m-d H:i:s')
        );

        $this->db->insert('conversations', $data);
        return $data;
    }

    /**
     * List conversations belonging to a client
     *
     * @param string $client_id
     * @param int $limit
     * @return array
     */
    public function get_client_conversations($client_id, $limit = 30) {
        $this->db->where('client_id', $client_id);
        $this->db->order_by('updated_at', 'DESC');
        $this->db->limit($limit);
        $query = $this->db->get('conversations');
        return $query->result_array();
    }

    /**
     * Save a chat message to history
     *
     * @param string $conversation_id
     * @param string $client_id
     * @param string $sender 'user' or 'assistant'
     * @param string $content
     * @param array $meta Structured metadata (citations, conflicts, derived_values, confidence, escalated, escalation_ticket)
     * @return int Insert ID
     */
    public function save_message($conversation_id, $client_id, $sender, $content, $meta = array()) {
        $data = array(
            'conversation_id'   => $conversation_id,
            'client_id'         => $client_id,
            'sender'            => $sender,
            'content'           => $content,
            'citations'         => !empty($meta['citations']) ? json_encode($meta['citations']) : null,
            'conflicts'         => !empty($meta['conflicts']) ? json_encode($meta['conflicts']) : null,
            'derived_values'    => !empty($meta['derived_values']) ? json_encode($meta['derived_values']) : null,
            'confidence'        => isset($meta['confidence']) ? floatval($meta['confidence']) : null,
            'escalated'         => !empty($meta['escalated']) ? 1 : 0,
            'escalation_ticket' => !empty($meta['escalation_ticket']) ? $meta['escalation_ticket'] : null,
            'created_at'        => date('Y-m-d H:i:s')
        );

        $this->db->insert('chat_messages', $data);
        $insert_id = $this->db->insert_id();

        # Update conversation timestamp and title if it's the initial user query
        $conv_update = array('updated_at' => date('Y-m-d H:i:s'));
        if ($sender === 'user') {
            # Set informative title from first question
            $short_title = mb_substr(trim($content), 0, 45);
            if (mb_strlen($content) > 45) {
                $short_title .= '...';
            }
            $conv_update['title'] = $short_title;
        }

        $this->db->where('id', $conversation_id);
        $this->db->update('conversations', $conv_update);

        return $insert_id;
    }

    /**
     * Retrieve messages for a specific conversation
     *
     * @param string $conversation_id
     * @param string $client_id
     * @return array
     */
    public function get_conversation_messages($conversation_id, $client_id) {
        $this->db->select('m.*, f.rating as feedback_rating, f.comment as feedback_comment');
        $this->db->from('chat_messages m');
        $this->db->join('message_feedback f', 'f.message_id = m.id AND f.client_id = m.client_id', 'left');
        $this->db->where('m.conversation_id', $conversation_id);
        $this->db->where('m.client_id', $client_id);
        $this->db->order_by('m.id', 'ASC');

        $query = $this->db->get();
        $messages = $query->result_array();

        # Parse JSON fields into arrays
        foreach ($messages as &$msg) {
            $msg['citations'] = !empty($msg['citations']) ? json_decode($msg['citations'], true) : array();
            $msg['conflicts'] = !empty($msg['conflicts']) ? json_decode($msg['conflicts'], true) : array();
            $msg['derived_values'] = !empty($msg['derived_values']) ? json_decode($msg['derived_values'], true) : array();
            $msg['escalated'] = (bool)$msg['escalated'];
        }

        return $messages;
    }

    /**
     * Record user thumbs-up or thumbs-down feedback
     *
     * @param int $message_id
     * @param string $conversation_id
     * @param string $client_id
     * @param string $rating 'thumbs_up' or 'thumbs_down'
     * @param string|null $comment
     * @return bool
     */
    public function record_feedback($message_id, $conversation_id, $client_id, $rating, $comment = null) {
        # Validate rating
        if (!in_array($rating, array('thumbs_up', 'thumbs_down'))) {
            return false;
        }

        # Verify message belongs to client and conversation
        $this->db->where(array('id' => $message_id, 'conversation_id' => $conversation_id, 'client_id' => $client_id));
        $msg = $this->db->get('chat_messages', 1)->row_array();
        if (!$msg) {
            return false;
        }

        # Check for existing feedback
        $this->db->where(array('message_id' => $message_id, 'client_id' => $client_id));
        $existing = $this->db->get('message_feedback', 1)->row_array();

        $data = array(
            'message_id'      => $message_id,
            'conversation_id' => $conversation_id,
            'client_id'       => $client_id,
            'rating'          => $rating,
            'comment'         => $comment,
            'created_at'      => date('Y-m-d H:i:s')
        );

        if ($existing) {
            $this->db->where(array('message_id' => $message_id, 'client_id' => $client_id));
            return $this->db->update('message_feedback', $data);
        } else {
            return $this->db->insert('message_feedback', $data);
        }
    }

    /**
     * Generates a UUID v4
     */
    protected function _generate_uuid() {
        return sprintf(
            '%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
            mt_rand(0, 0xffff), mt_rand(0, 0xffff),
            mt_rand(0, 0xffff),
            mt_rand(0, 0x0fff) | 0x4000,
            mt_rand(0, 0x3fff) | 0x8000,
            mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
        );
    }
}
