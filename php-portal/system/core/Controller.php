<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Controller Class
 */
class CI_Controller {

    private static $instance;
    public $load;

    public function __construct() {
        self::$instance =& $this;

        # Core framework classes
        $this->config   =& load_class('Config', 'core');
        $this->uri      =& load_class('URI', 'core');
        $this->router   =& load_class('Router', 'core');
        $this->output   =& load_class('Output', 'core');
        $this->security =& load_class('Security', 'core');
        $this->input    =& load_class('Input', 'core');
        $this->load     =& load_class('Loader', 'core');

        foreach (is_loaded() as $var => $class) {
            $this->$var =& load_class($class);
        }

        # Autoload components
        if (file_exists(APPPATH . 'config/autoload.php')) {
            require(APPPATH . 'config/autoload.php');
            if (isset($autoload)) {
                if (!empty($autoload['helper'])) {
                    $this->load->helper($autoload['helper']);
                }
                if (!empty($autoload['libraries'])) {
                    foreach ($autoload['libraries'] as $item) {
                        if ($item === 'database') {
                            $this->load->database();
                        } else {
                            $this->load->library($item);
                        }
                    }
                }
                if (!empty($autoload['model'])) {
                    $this->load->model($autoload['model']);
                }
            }
        }
    }

    public static function &get_instance() {
        return self::$instance;
    }
}
