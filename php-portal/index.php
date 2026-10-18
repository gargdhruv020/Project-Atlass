<?php
/**
 * Project Atlas - CodeIgniter 3 Portal Entry Point
 */
define('ENVIRONMENT', isset($_SERVER['CI_ENV']) ? $_SERVER['CI_ENV'] : 'development');

switch (ENVIRONMENT) {
    case 'development':
        error_reporting(-1);
        ini_set('display_errors', 1);
        break;
    case 'testing':
    case 'production':
        ini_set('display_errors', 0);
        error_reporting(E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_STRICT & ~E_USER_NOTICE & ~E_USER_DEPRECATED);
        break;
    default:
        header('HTTP/1.1 503 Service Unavailable.', TRUE, 503);
        echo 'The application environment is not set correctly.';
        exit(1);
}

$system_path = 'system';
$application_folder = 'application';
$view_folder = '';

if (defined('STDIN')) {
    chdir(dirname(__FILE__));
}

define('SELF', pathinfo(__FILE__, PATHINFO_BASENAME));
define('BASEPATH', str_replace('\\', '/', $system_path));
define('FCPATH', dirname(__FILE__).'/');
define('SYSDIR', basename(BASEPATH));
define('APPPATH', $application_folder.'/');
define('VIEWPATH', APPPATH.'views/');

echo "<!DOCTYPE html><html><head><title>Project Atlas - Legacy Portal</title>";
echo "<style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.6;color:#333;background:#f8f9fa} .card{background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);max-width:800px;margin:auto} h1{color:#1a365d;margin-top:0} .badge{display:inline-block;padding:4px 8px;background:#e2e8f0;border-radius:4px;font-size:12px;font-weight:bold}</style></head><body>";
echo "<div class='card'>";
echo "<h1>Project Atlas &mdash; Client Portal</h1>";
echo "<span class='badge'>CodeIgniter 3 Integration</span>";
echo "<p>Welcome to the legacy client portal for Project Atlas. This interface connects to the <code>project_atlas</code> MySQL database and collaborates with the FastAPI AI Copilot backend.</p>";
echo "<h3>Active Services</h3>";
echo "<ul><li><strong>FastAPI Backend</strong>: <code>/api/v1</code></li><li><strong>MySQL Database</strong>: <code>project_atlas</code></li><li><strong>Vector Store</strong>: ChromaDB (Local Persistent)</li></ul>";
echo "</div></body></html>";
