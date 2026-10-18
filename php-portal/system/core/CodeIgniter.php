<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CodeIgniter 3 Core Bootstrap
 */

define('CI_VERSION', '3.1.13');

require_once(BASEPATH . 'core/Common.php');

# Load core classes
$CFG =& load_class('Config', 'core');
$URI =& load_class('URI', 'core');
$RTR =& load_class('Router', 'core');
$OUT =& load_class('Output', 'core');
$SEC =& load_class('Security', 'core');
$IN  =& load_class('Input', 'core');

# CSRF Verification
$SEC->csrf_verify();

# Load base Controller and Model
require_once(BASEPATH . 'core/Controller.php');
require_once(BASEPATH . 'core/Model.php');

$class = ucfirst($RTR->fetch_class());
$method = $RTR->fetch_method();

# Locate controller
$controller_file = APPPATH . 'controllers/' . $class . '.php';
if (!file_exists($controller_file)) {
    # Check lowercase
    $controller_file = APPPATH . 'controllers/' . strtolower($class) . '.php';
}

if (!file_exists($controller_file)) {
    show_404();
}

require_once($controller_file);

if (!class_exists($class, FALSE)) {
    show_404();
}

$CI = new $class();

if (!method_exists($CI, $method) || strpos($method, '_') === 0) {
    show_404();
}

# Execute controller method
call_user_func_array(array(&$CI, $method), $RTR->params);

# Send output buffer
$OUT->_display();
