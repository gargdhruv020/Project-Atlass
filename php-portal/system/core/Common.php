<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CodeIgniter 3 Common Functions
 */

if (!function_exists('is_php')) {
    function is_php($version) {
        static $_is_php;
        $version = (string)$version;
        if (!isset($_is_php[$version])) {
            $_is_php[$version] = version_compare(PHP_VERSION, $version, '>=');
        }
        return $_is_php[$version];
    }
}

if (!function_exists('get_instance')) {
    function &get_instance() {
        return CI_Controller::get_instance();
    }
}

if (!function_exists('load_class')) {
    function &load_class($class, $directory = 'libraries', $param = NULL) {
        static $_classes = array();

        if (isset($_classes[$class])) {
            return $_classes[$class];
        }

        $name = FALSE;
        foreach (array(APPPATH, BASEPATH) as $path) {
            if (file_exists($path . $directory . '/' . $class . '.php')) {
                $name = 'CI_' . $class;
                if (class_exists($name, FALSE) === FALSE) {
                    require_once($path . $directory . '/' . $class . '.php');
                }
                break;
            }
        }

        if ($name === FALSE) {
            header('HTTP/1.1 503 Service Unavailable.', TRUE, 503);
            echo 'Unable to locate the specified class: ' . $class . '.php';
            exit(5);
        }

        $_classes[$class] = isset($param) ? new $name($param) : new $name();
        is_loaded($class);
        return $_classes[$class];
    }
}

if (!function_exists('is_loaded')) {
    function &is_loaded($class = '') {
        static $_is_loaded = array();
        if ($class !== '') {
            $_is_loaded[strtolower($class)] = $class;
        }
        return $_is_loaded;
    }
}

if (!function_exists('config_item')) {
    function config_item($item) {
        static $_config;
        if (empty($_config)) {
            $_config[0] =& load_class('Config', 'core');
        }
        return $_config[0]->item($item);
    }
}

if (!function_exists('html_escape')) {
    function html_escape($var, $double_encode = TRUE) {
        if (empty($var)) {
            return $var;
        }
        if (is_array($var)) {
            foreach (array_keys($var) as $key) {
                $var[$key] = html_escape($var[$key], $double_encode);
            }
            return $var;
        }
        return htmlspecialchars($var, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8', $double_encode);
    }
}

if (!function_exists('log_message')) {
    function log_message($level, $message) {
        $level = strtoupper($level);
        error_log("[CI3-{$level}] {$message}");
    }
}

if (!function_exists('show_error')) {
    function show_error($message, $status_code = 500, $heading = 'An Error Was Encountered') {
        $status_code = abs($status_code);
        if ($status_code < 100) {
            $status_code = 500;
        }
        header('HTTP/1.1 ' . $status_code, TRUE, $status_code);
        echo "<!DOCTYPE html><html><head><title>{$heading}</title></head><body><h1>{$heading}</h1><p>{$message}</p></body></html>";
        exit(1);
    }
}

if (!function_exists('show_404')) {
    function show_404($page = '', $log_error = TRUE) {
        show_error('The page you requested was not found.', 404, '404 Page Not Found');
    }
}

if (!function_exists('site_url')) {
    function site_url($uri = '', $protocol = NULL) {
        $CI =& get_instance();
        return $CI->config->site_url($uri, $protocol);
    }
}

if (!function_exists('base_url')) {
    function base_url($uri = '', $protocol = NULL) {
        $CI =& get_instance();
        return $CI->config->base_url($uri, $protocol);
    }
}

if (!function_exists('redirect')) {
    function redirect($uri = '', $method = 'auto', $code = NULL) {
        if (!preg_match('#^https?://#i', $uri)) {
            $uri = site_url($uri);
        }
        header('Location: ' . $uri, TRUE, $code ?: 302);
        exit;
    }
}
