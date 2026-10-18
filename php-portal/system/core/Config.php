<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Config Class
 */
class CI_Config {

    public $config = array();

    public function __construct() {
        if (file_exists(APPPATH . 'config/config.php')) {
            require(APPPATH . 'config/config.php');
            if (isset($config) && is_array($config)) {
                $this->config = $config;
            }
        }
    }

    public function item($item, $index = '') {
        if ($index == '') {
            return isset($this->config[$item]) ? $this->config[$item] : NULL;
        }
        return isset($this->config[$index][$item]) ? $this->config[$index][$item] : NULL;
    }

    public function set_item($item, $value) {
        $this->config[$item] = $value;
    }

    public function site_url($uri = '', $protocol = NULL) {
        $base = $this->item('base_url');
        $index = $this->item('index_page');
        
        $url = rtrim($base, '/') . '/';
        if (!empty($index)) {
            $url .= trim($index, '/') . '/';
        }
        if (!empty($uri)) {
            $url .= ltrim($uri, '/');
        }
        return $url;
    }

    public function base_url($uri = '', $protocol = NULL) {
        $base = $this->item('base_url');
        return rtrim($base, '/') . '/' . ltrim($uri, '/');
    }
}
