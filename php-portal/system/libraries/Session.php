<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Session Class
 */
class CI_Session {

    public function __construct() {
        if (session_status() === PHP_SESSION_NONE) {
            @session_start();
        }
    }

    public function userdata($item = NULL) {
        if ($item === NULL) {
            return isset($_SESSION) ? $_SESSION : array();
        }
        return isset($_SESSION[$item]) ? $_SESSION[$item] : NULL;
    }

    public function set_userdata($data, $value = NULL) {
        if (is_array($data)) {
            foreach ($data as $key => $val) {
                $_SESSION[$key] = $val;
            }
            return;
        }
        $_SESSION[$data] = $value;
    }

    public function unset_userdata($key) {
        if (is_array($key)) {
            foreach ($key as $k) {
                unset($_SESSION[$k]);
            }
            return;
        }
        unset($_SESSION[$key]);
    }

    public function sess_destroy() {
        if (session_status() === PHP_SESSION_ACTIVE) {
            session_destroy();
            $_SESSION = array();
        }
    }
}
