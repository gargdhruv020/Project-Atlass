<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Loader Class
 */
class CI_Loader {

    protected $_ci_models = array();
    protected $_ci_helpers = array();
    protected $_ci_libraries = array();

    public function view($view, $vars = array(), $return = FALSE) {
        $CI =& get_instance();

        foreach (get_object_vars($CI) as $_ci_key => $_ci_var) {
            if (!isset($this->$_ci_key)) {
                $this->$_ci_key =& $CI->$_ci_key;
            }
        }

        if (is_array($vars)) {
            extract($vars);
        }

        $view_path = VIEWPATH . $view;
        if (!preg_match('/\.php$/', $view_path)) {
            $view_path .= '.php';
        }

        if (!file_exists($view_path)) {
            show_error('Unable to load the requested view: ' . $view);
        }

        ob_start();
        include($view_path);
        $buffer = ob_get_contents();
        ob_end_clean();

        if ($return === TRUE) {
            return $buffer;
        }

        $CI->output->append_output($buffer);
    }

    public function model($model, $name = '', $db_conn = FALSE) {
        if (empty($model)) {
            return $this;
        }

        if (is_array($model)) {
            foreach ($model as $m) {
                $this->model($m);
            }
            return $this;
        }

        $model_name = !empty($name) ? $name : basename($model);
        $model_class = ucfirst($model_name);

        if (isset($this->_ci_models[$model_name])) {
            return $this;
        }

        $CI =& get_instance();
        if (isset($CI->$model_name)) {
            return $this;
        }

        $path = APPPATH . 'models/' . $model . '.php';
        if (!file_exists($path)) {
            $path = APPPATH . 'models/' . ucfirst($model) . '.php';
        }

        if (!file_exists($path)) {
            show_error('Unable to locate the model you have specified: ' . $model);
        }

        require_once($path);

        $CI->$model_name = new $model_class();
        $this->_ci_models[$model_name] = $model_name;

        return $this;
    }

    public function library($library, $params = NULL, $object_name = NULL) {
        if (empty($library)) {
            return $this;
        }

        if (is_array($library)) {
            foreach ($library as $l) {
                $this->library($l);
            }
            return $this;
        }

        $class_name = !empty($object_name) ? $object_name : strtolower(basename($library));
        $CI =& get_instance();

        if (isset($CI->$class_name)) {
            return $this;
        }

        # Check in application/libraries
        $found = FALSE;
        $file_app = APPPATH . 'libraries/' . ucfirst($library) . '.php';
        if (file_exists($file_app)) {
            require_once($file_app);
            $real_class = ucfirst($library);
            $found = TRUE;
        } else {
            # Check system/libraries
            $file_sys = BASEPATH . 'libraries/' . ucfirst($library) . '.php';
            if (file_exists($file_sys)) {
                require_once($file_sys);
                $real_class = 'CI_' . ucfirst($library);
                $found = TRUE;
            }
        }

        if (!$found) {
            # Check lowercase
            $file_app_lower = APPPATH . 'libraries/' . strtolower($library) . '.php';
            if (file_exists($file_app_lower)) {
                require_once($file_app_lower);
                $real_class = ucfirst($library);
                $found = TRUE;
            }
        }

        if (!$found) {
            show_error('Unable to load requested library: ' . $library);
        }

        $CI->$class_name = isset($params) ? new $real_class($params) : new $real_class();
        $this->_ci_libraries[$class_name] = $class_name;

        return $this;
    }

    public function helper($helpers = array()) {
        if (!is_array($helpers)) {
            $helpers = array($helpers);
        }

        foreach ($helpers as $h) {
            $h = strtolower($h);
            if (isset($this->_ci_helpers[$h])) {
                continue;
            }

            # Application helper first
            $file = APPPATH . 'helpers/' . $h . '_helper.php';
            if (file_exists($file)) {
                include_once($file);
                $this->_ci_helpers[$h] = TRUE;
                continue;
            }

            # System helper
            $file = BASEPATH . 'helpers/' . $h . '_helper.php';
            if (file_exists($file)) {
                include_once($file);
                $this->_ci_helpers[$h] = TRUE;
                continue;
            }

            $this->_ci_helpers[$h] = TRUE;
        }

        return $this;
    }

    public function database($params = '', $return = FALSE, $query_builder = NULL) {
        $CI =& get_instance();

        if (isset($CI->db) && is_object($CI->db) && $return === FALSE) {
            return FALSE;
        }

        require_once(BASEPATH . 'database/DB.php');

        if ($return === TRUE) {
            return DB($params, $query_builder);
        }

        $CI->db = DB($params, $query_builder);
        return $this;
    }
}
