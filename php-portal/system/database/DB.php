<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * CI_DB Class (CodeIgniter 3 MySQLi Database Driver & Query Builder)
 */

function &DB($params = '', $query_builder_override = NULL) {
    if (file_exists(APPPATH . 'config/database.php')) {
        require(APPPATH . 'config/database.php');
    }

    if (!isset($db) || !isset($active_group) || !isset($db[$active_group])) {
        show_error('No database configuration found in application/config/database.php');
    }

    $config = $db[$active_group];
    $db_obj = new CI_DB_driver($config);
    return $db_obj;
}

class CI_DB_driver {

    protected $conn;
    protected $config;
    protected $select = '*';
    protected $from = '';
    protected $joins = array();
    protected $wheres = array();
    protected $orders = array();
    protected $limit = null;
    protected $offset = null;

    public function __construct($config) {
        $this->config = $config;
        $this->_connect();
    }

    protected function _connect() {
        $host = !empty($this->config['hostname']) ? $this->config['hostname'] : '127.0.0.1';
        $port = !empty($this->config['port']) ? intval($this->config['port']) : 3306;
        $user = !empty($this->config['username']) ? $this->config['username'] : 'root';
        $pass = isset($this->config['password']) ? $this->config['password'] : '';
        $name = !empty($this->config['database']) ? $this->config['database'] : 'project_atlas';

        $this->conn = @new mysqli($host, $user, $pass, $name, $port);

        if ($this->conn->connect_error) {
            log_message('error', 'MySQL Connection Failed: ' . $this->conn->connect_error);
            show_error('Unable to connect to the database: ' . $this->conn->connect_error, 500);
        }

        $charset = !empty($this->config['char_set']) ? $this->config['char_set'] : 'utf8mb4';
        $this->conn->set_charset($charset);
    }

    public function select($select) {
        $this->select = $select;
        return $this;
    }

    public function from($from) {
        $this->from = $from;
        return $this;
    }

    public function join($table, $cond, $type = '') {
        $this->joins[] = array($table, $cond, strtoupper($type));
        return $this;
    }

    public function where($key, $value = NULL) {
        if (is_array($key)) {
            foreach ($key as $k => $v) {
                $this->where($k, $v);
            }
            return $this;
        }

        if ($value === NULL) {
            $this->wheres[] = $key;
        } else {
            $safe_val = $this->escape($value);
            if (strpos($key, ' ') !== false) {
                $this->wheres[] = "{$key} {$safe_val}";
            } else {
                $this->wheres[] = "`{$key}` = {$safe_val}";
            }
        }
        return $this;
    }

    public function order_by($orderby, $direction = 'ASC') {
        $this->orders[] = "{$orderby} " . strtoupper($direction);
        return $this;
    }

    public function limit($value, $offset = 0) {
        $this->limit = intval($value);
        if ($offset > 0) {
            $this->offset = intval($offset);
        }
        return $this;
    }

    public function get($table = '', $limit = null, $offset = null) {
        if ($table !== '') {
            $this->from($table);
        }
        if ($limit !== null) {
            $this->limit($limit, $offset);
        }

        $sql = "SELECT {$this->select} FROM {$this->from}";

        foreach ($this->joins as $j) {
            $type = !empty($j[2]) ? $j[2] . ' JOIN' : 'JOIN';
            $sql .= " {$type} {$j[0]} ON {$j[1]}";
        }

        if (!empty($this->wheres)) {
            $sql .= " WHERE " . implode(" AND ", $this->wheres);
        }

        if (!empty($this->orders)) {
            $sql .= " ORDER BY " . implode(", ", $this->orders);
        }

        if ($this->limit !== null) {
            $sql .= " LIMIT " . $this->limit;
            if ($this->offset !== null) {
                $sql .= " OFFSET " . $this->offset;
            }
        }

        $res = $this->query($sql);
        $this->_reset_select();
        return $res;
    }

    public function get_where($table, $where = array(), $limit = null, $offset = null) {
        if (!empty($where)) {
            $this->where($where);
        }
        return $this->get($table, $limit, $offset);
    }

    public function insert($table, $data) {
        $keys = array();
        $vals = array();
        foreach ($data as $k => $v) {
            $keys[] = "`{$k}`";
            $vals[] = $this->escape($v);
        }

        $sql = "INSERT INTO `{$table}` (" . implode(', ', $keys) . ") VALUES (" . implode(', ', $vals) . ")";
        $this->query($sql);
        $this->_reset_select();
        return $this->conn->affected_rows > 0;
    }

    public function insert_id() {
        return $this->conn->insert_id;
    }

    public function update($table, $data, $where = array()) {
        if (!empty($where)) {
            $this->where($where);
        }

        $sets = array();
        foreach ($data as $k => $v) {
            $sets[] = "`{$k}` = " . $this->escape($v);
        }

        $sql = "UPDATE `{$table}` SET " . implode(', ', $sets);
        if (!empty($this->wheres)) {
            $sql .= " WHERE " . implode(' AND ', $this->wheres);
        }

        $this->query($sql);
        $this->_reset_select();
        return $this->conn->affected_rows >= 0;
    }

    public function delete($table, $where = array()) {
        if (!empty($where)) {
            $this->where($where);
        }

        $sql = "DELETE FROM `{$table}`";
        if (!empty($this->wheres)) {
            $sql .= " WHERE " . implode(' AND ', $this->wheres);
        }

        $this->query($sql);
        $this->_reset_select();
        return $this->conn->affected_rows >= 0;
    }

    public function query($sql) {
        $res = $this->conn->query($sql);
        if ($res === false) {
            log_message('error', "Database Query Failed: {$sql} | Error: " . $this->conn->error);
            show_error("Database Error: " . $this->conn->error, 500);
        }
        return new CI_DB_result($res);
    }

    public function escape($str) {
        if ($str === null) {
            return 'NULL';
        }
        if (is_bool($str)) {
            return $str ? '1' : '0';
        }
        if (is_int($str) || is_float($str)) {
            return (string)$str;
        }
        return "'" . $this->conn->real_escape_string((string)$str) . "'";
    }

    protected function _reset_select() {
        $this->select = '*';
        $this->from = '';
        $this->joins = array();
        $this->wheres = array();
        $this->orders = array();
        $this->limit = null;
        $this->offset = null;
    }
}

class CI_DB_result {
    protected $result;

    public function __construct($result) {
        $this->result = $result;
    }

    public function num_rows() {
        return ($this->result instanceof mysqli_result) ? $this->result->num_rows : 0;
    }

    public function result_array() {
        $rows = array();
        if ($this->result instanceof mysqli_result) {
            while ($row = $this->result->fetch_assoc()) {
                $rows[] = $row;
            }
        }
        return $rows;
    }

    public function row_array() {
        if ($this->result instanceof mysqli_result) {
            return $this->result->fetch_assoc() ?: null;
        }
        return null;
    }
}
