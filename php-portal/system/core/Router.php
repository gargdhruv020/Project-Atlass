<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Router Class
 */
class CI_Router {

    public $class = 'chat';
    public $method = 'index';
    public $params = array();

    public function __construct() {
        $this->_route();
    }

    protected function _route() {
        $routes = array();
        if (file_exists(APPPATH . 'config/routes.php')) {
            require(APPPATH . 'config/routes.php');
        }

        $default_controller = !empty($routes['default_controller']) ? $routes['default_controller'] : 'chat';

        $uri =& load_class('URI', 'core');
        $uri_string = $uri->uri_string();

        if (empty($uri_string)) {
            $this->class = $default_controller;
            $this->method = 'index';
            return;
        }

        # Check explicit routes
        foreach ($routes as $key => $val) {
            $key = str_replace(array(':any', ':num'), array('[^/]+', '[0-9]+'), $key);
            if (preg_match('#^' . $key . '$#', $uri_string, $matches)) {
                $val = preg_replace('#^' . $key . '$#', $val, $uri_string);
                $parts = explode('/', $val);
                $this->class = array_shift($parts);
                $this->method = !empty($parts) ? array_shift($parts) : 'index';
                $this->params = $parts;
                return;
            }
        }

        # Default standard routing: controller/method/params
        $parts = $uri->segments;
        if (!empty($parts)) {
            $this->class = array_shift($parts);
            $this->method = !empty($parts) ? array_shift($parts) : 'index';
            $this->params = $parts;
        }
    }

    public function fetch_class() {
        return $this->class;
    }

    public function fetch_method() {
        return $this->method;
    }
}
