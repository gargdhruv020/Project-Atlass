<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_URI Class
 */
class CI_URI {

    public $uri_string = '';
    public $segments = array();

    public function __construct() {
        $this->_parse_uri();
    }

    protected function _parse_uri() {
        $uri = '';
        if (!empty($_SERVER['PATH_INFO'])) {
            $uri = $_SERVER['PATH_INFO'];
        } elseif (!empty($_SERVER['REQUEST_URI'])) {
            $uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
            $script_name = $_SERVER['SCRIPT_NAME'];
            if (strpos($uri, $script_name) === 0) {
                $uri = substr($uri, strlen($script_name));
            } elseif (strpos($uri, dirname($script_name)) === 0) {
                $uri = substr($uri, strlen(dirname($script_name)));
            }
        }

        $uri = trim($uri, '/');
        $this->uri_string = $uri;

        if ($uri !== '') {
            $this->segments = explode('/', $uri);
        }
    }

    public function segment($n, $no_result = NULL) {
        $idx = $n - 1;
        return isset($this->segments[$idx]) ? $this->segments[$idx] : $no_result;
    }

    public function uri_string() {
        return $this->uri_string;
    }
}
