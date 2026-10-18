<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CodeIgniter 3 Routing for Project Atlas Portal
 */
$route['default_controller'] = 'chat';
$route['404_override'] = '';
$route['translate_uri_dashes'] = FALSE;

# Chat routes
$route['chat'] = 'chat/index';
$route['chat/c/(:any)'] = 'chat/index/$1';
$route['chat/send'] = 'chat/send';
$route['chat/feedback'] = 'chat/feedback';
$route['chat/history/(:any)'] = 'chat/history/$1';
$route['chat/new'] = 'chat/new_conversation';
$route['chat/switch_client'] = 'chat/switch_client';
