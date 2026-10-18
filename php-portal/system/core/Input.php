<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Input Class
 */
class CI_Input {

    protected $security;

    public function __construct() {
        $this->security =& load_class('Security', 'core');
    }

    public function get($index = NULL, $xss_clean = NULL) {
        return $this->_fetch_from_array($_GET, $index, $xss_clean);
    }

    public function post($index = NULL, $xss_clean = NULL) {
        return $this->_fetch_from_array($_POST, $index, $xss_clean);
    }

    public function post_get($index, $xss_clean = NULL) {
        return isset($_POST[$index]) ? $this->post($index, $xss_clean) : $this->get($index, $xss_clean);
    }

    public function get_post($index, $xss_clean = NULL) {
        return isset($_GET[$index]) ? $this->get($index, $xss_clean) : $this->post($index, $xss_clean);
    }

    public function server($index, $xss_clean = NULL) {
        return $this->_fetch_from_array($_SERVER, $index, $xss_clean);
    }

    public function method($upper = FALSE) {
        $method = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : 'GET';
        return $upper ? strtoupper($method) : strtolower($method);
    }

    public function is_ajax_request() {
        return (!empty($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest');
    }

    public function ip_address() {
        return isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1';
    }

    protected function _fetch_from_array(&$array, $index = NULL, $xss_clean = NULL) {
        if ($index === NULL) {
            $output = array();
            foreach (array_keys($array) as $key) {
                $output[$key] = $this->_fetch_from_array($array, $key, $xss_clean);
            }
            return $output;
        }

        if (isset($array[$index])) {
            $value = $array[$index];
            if ($xss_clean === TRUE) {
                return $this->security->xss_clean($value);
            }
            return $value;
        }

        return NULL;
    }
}
