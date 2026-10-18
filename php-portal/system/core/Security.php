<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Security Class
 * Handles CSRF token creation, validation, and XSS sanitization
 */
class CI_Security {

    protected $_csrf_hash;
    protected $_csrf_expire = 7200;
    protected $_csrf_token_name = 'csrf_atlas_token';
    protected $_csrf_cookie_name = 'csrf_atlas_cookie';

    public function __construct() {
        $config =& load_class('Config', 'core');
        
        $this->_csrf_expire = $config->item('csrf_expire') ?: 7200;
        $this->_csrf_token_name = $config->item('csrf_token_name') ?: 'csrf_atlas_token';
        $this->_csrf_cookie_name = $config->item('csrf_cookie_name') ?: 'csrf_atlas_cookie';

        $this->_csrf_set_hash();
    }

    public function csrf_verify() {
        $config =& load_class('Config', 'core');
        if ($config->item('csrf_protection') !== TRUE) {
            return $this;
        }

        # If not POST, skip verification
        if (strtoupper($_SERVER['REQUEST_METHOD']) !== 'POST') {
            return $this;
        }

        $token = isset($_POST[$this->_csrf_token_name]) ? $_POST[$this->_csrf_token_name] : (
            isset($_COOKIE[$this->_csrf_cookie_name]) ? $_COOKIE[$this->_csrf_cookie_name] : NULL
        );

        # Allow headers if AJAX
        if (!$token && isset($_SERVER['HTTP_X_CSRF_TOKEN'])) {
            $token = $_SERVER['HTTP_X_CSRF_TOKEN'];
        }

        if (!$token || $token !== $this->_csrf_hash) {
            $this->csrf_show_error();
        }

        return $this;
    }

    public function get_csrf_hash() {
        return $this->_csrf_hash;
    }

    public function get_csrf_token_name() {
        return $this->_csrf_token_name;
    }

    protected function _csrf_set_hash() {
        if ($this->_csrf_hash) {
            return $this->_csrf_hash;
        }

        if (isset($_COOKIE[$this->_csrf_cookie_name]) && is_string($_COOKIE[$this->_csrf_cookie_name])
            && preg_match('#^[0-9a-f]{32}$#iS', $_COOKIE[$this->_csrf_cookie_name]) === 1) {
            return $this->_csrf_hash = $_COOKIE[$this->_csrf_cookie_name];
        }

        $rand = bin2hex(random_bytes(16));
        $this->_csrf_hash = $rand;
        
        @setcookie(
            $this->_csrf_cookie_name,
            $this->_csrf_hash,
            time() + $this->_csrf_expire,
            '/',
            '',
            FALSE,
            FALSE
        );

        return $this->_csrf_hash;
    }

    public function csrf_show_error() {
        show_error('The action you have requested is not allowed. CSRF verification failed.', 403, '403 Forbidden');
    }

    public function xss_clean($str, $is_image = FALSE) {
        if (is_array($str)) {
            foreach ($str as $key => $val) {
                $str[$key] = $this->xss_clean($val, $is_image);
            }
            return $str;
        }
        return htmlspecialchars((string)$str, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
}
