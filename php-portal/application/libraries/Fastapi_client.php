<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * Fastapi_client Library for CodeIgniter 3
 * Reusable HTTP client service communicating with the Project Atlas FastAPI backend.
 * Enforces API authentication server-side, request timeouts, and resilient error fallbacks.
 */
class Fastapi_client {

    protected $CI;
    protected $base_url;
    protected $api_key;
    protected $timeout;

    /**
     * Constructor
     * @param array $config
     */
    public function __construct($config = array()) {
        $this->CI =& get_instance();
        
        $default_base = $this->CI->config->item('fastapi_base_url');
        $default_key = $this->CI->config->item('fastapi_api_key');
        $default_timeout = $this->CI->config->item('fastapi_timeout');

        $this->base_url = rtrim(!empty($config['base_url']) ? $config['base_url'] : ($default_base ?: 'http://127.0.0.1:8000'), '/');
        $this->api_key = !empty($config['api_key']) ? $config['api_key'] : ($default_key ?: 'atlas-dev-key-2026');
        $this->timeout = !empty($config['timeout']) ? intval($config['timeout']) : ($default_timeout ? intval($default_timeout) : 30);
    }

    /**
     * Submit query to FastAPI POST /chat endpoint
     *
     * @param string $client_id Validated client ID (e.g. 'C-01')
     * @param string $query Research question
     * @param string|null $conversation_id Optional conversation ID
     * @param string|null $report_id Optional report scope constraint
     * @return array Standardized result [success, status, data, error]
     */
    public function post_chat($client_id, $query, $conversation_id = null, $report_id = null) {
        $endpoint = $this->base_url . '/chat';

        $payload = array(
            'client_id' => trim($client_id),
            'query'     => trim($query)
        );

        if (!empty($conversation_id)) {
            $payload['conversation_id'] = trim($conversation_id);
        }
        if (!empty($report_id)) {
            $payload['report_id'] = trim($report_id);
        }

        return $this->_send_request('POST', $endpoint, $payload);
    }

    /**
     * Query backend GET /health endpoint
     *
     * @return array Standardized result [success, status, data, error]
     */
    public function get_health() {
        $endpoint = $this->base_url . '/health';
        return $this->_send_request('GET', $endpoint);
    }

    /**
     * Query backend GET /escalations endpoint
     *
     * @param string|null $client_id
     * @param string|null $status
     * @return array Standardized result [success, status, data, error]
     */
    public function get_escalations($client_id = null, $status = null) {
        $params = array();
        if (!empty($client_id)) {
            $params['client_id'] = $client_id;
        }
        if (!empty($status)) {
            $params['status'] = $status;
        }

        $query_str = !empty($params) ? '?' . http_build_query($params) : '';
        $endpoint = $this->base_url . '/escalations' . $query_str;

        return $this->_send_request('GET', $endpoint);
    }

    /**
     * Core HTTP execution helper supporting cURL and stream context fallbacks
     *
     * @param string $method GET, POST
     * @param string $url Target endpoint URL
     * @param array|null $body Payload for POST
     * @return array Standardized response array
     */
    protected function _send_request($method, $url, $body = null) {
        $headers = array(
            'Content-Type: application/json',
            'Accept: application/json',
            'X-API-Key: ' . $this->api_key
        );

        if (function_exists('curl_init')) {
            return $this->_curl_request($method, $url, $headers, $body);
        } else {
            return $this->_stream_request($method, $url, $headers, $body);
        }
    }

    /**
     * cURL Request Handler
     */
    protected function _curl_request($method, $url, $headers, $body) {
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);

        if (strtoupper($method) === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
        }

        $raw_response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_errno = curl_errno($ch);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($curl_errno !== 0) {
            log_message('error', "Fastapi_client cURL error ({$curl_errno}): {$curl_error} on {$url}");
            if ($curl_errno === 28) { // CURLE_OPERATION_TIMEDOUT
                return array(
                    'success' => false,
                    'status'  => 504,
                    'data'    => null,
                    'error'   => 'The AI Research Copilot request timed out after ' . $this->timeout . ' seconds. Please try again.'
                );
            }
            return array(
                'success' => false,
                'status'  => 503,
                'data'    => null,
                'error'   => 'The AI Research Copilot service is currently unavailable. Please verify the backend service is running.'
            );
        }

        return $this->_format_response($http_code, $raw_response);
    }

    /**
     * Stream Context Request Handler (Fallback if cURL extension is not installed)
     */
    protected function _stream_request($method, $url, $headers, $body) {
        $opts = array(
            'http' => array(
                'method'  => strtoupper($method),
                'header'  => implode("\r\n", $headers),
                'timeout' => $this->timeout,
                'ignore_errors' => true
            )
        );

        if (strtoupper($method) === 'POST' && !empty($body)) {
            $opts['http']['content'] = json_encode($body);
        }

        $context = stream_context_create($opts);
        $raw_response = @file_get_contents($url, false, $context);

        $http_code = 500;
        if (isset($http_response_header) && is_array($http_response_header)) {
            if (preg_match('/HTTP\/\S*\s+(\d{3})/', $http_response_header[0], $matches)) {
                $http_code = intval($matches[1]);
            }
        }

        if ($raw_response === false) {
            log_message('error', "Fastapi_client stream error on {$url}");
            return array(
                'success' => false,
                'status'  => 503,
                'data'    => null,
                'error'   => 'The AI Research Copilot service is currently unavailable.'
            );
        }

        return $this->_format_response($http_code, $raw_response);
    }

    /**
     * Decodes and validates JSON responses
     */
    protected function _format_response($http_code, $raw_response) {
        $data = json_decode($raw_response, true);

        if ($http_code >= 200 && $http_code < 300) {
            return array(
                'success' => true,
                'status'  => $http_code,
                'data'    => is_array($data) ? $data : array('raw' => $raw_response),
                'error'   => null
            );
        }

        $error_message = 'Backend API returned error code ' . $http_code;
        if (is_array($data) && !empty($data['detail'])) {
            $error_message = is_string($data['detail']) ? $data['detail'] : json_encode($data['detail']);
        }

        log_message('error', "Fastapi_client HTTP {$http_code} response: {$error_message}");

        return array(
            'success' => false,
            'status'  => $http_code,
            'data'    => $data,
            'error'   => $error_message
        );
    }
}
