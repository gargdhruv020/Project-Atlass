<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CodeIgniter 3 Autoload Configuration
 */
$autoload['packages'] = array();
$autoload['libraries'] = array('database', 'session', 'fastapi_client');
$autoload['drivers'] = array();
$autoload['helper'] = array('url', 'form', 'html', 'security');
$autoload['config'] = array();
$autoload['language'] = array();
$autoload['model'] = array('chat_model');
