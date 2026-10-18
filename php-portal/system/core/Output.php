<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_Output Class
 */
class CI_Output {

    protected $final_output = '';
    protected $headers = array();
    protected $status_header = array(200, 'OK');
    protected $mime_type = 'text/html';

    public function set_output($output) {
        $this->final_output = $output;
        return $this;
    }

    public function append_output($output) {
        $this->final_output .= $output;
        return $this;
    }

    public function get_output() {
        return $this->final_output;
    }

    public function set_content_type($mime_type, $charset = 'utf-8') {
        $this->mime_type = $mime_type;
        $this->set_header('Content-Type: ' . $mime_type . '; charset=' . $charset);
        return $this;
    }

    public function set_header($header, $replace = TRUE) {
        $this->headers[] = array($header, $replace);
        return $this;
    }

    public function set_status_header($code = 200, $text = '') {
        $this->status_header = array($code, $text);
        return $this;
    }

    public function _display($output = '') {
        if ($output === '') {
            $output = $this->final_output;
        }

        http_response_code($this->status_header[0]);

        foreach ($this->headers as $header) {
            header($header[0], $header[1]);
        }

        echo $output;
    }
}
