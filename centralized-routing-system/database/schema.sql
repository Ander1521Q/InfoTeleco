-- =====================================================
-- CENTRALIZED ROUTING SYSTEM DATABASE SCHEMA
-- Compatible with XAMPP / MySQL
-- =====================================================

-- Create database
CREATE DATABASE IF NOT EXISTS routing_system;
USE routing_system;

-- =====================================================
-- TABLE: routers
-- Stores registered router information
-- =====================================================
CREATE TABLE IF NOT EXISTS routers (
    router_id VARCHAR(10) PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    port_number INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_active ON routers(is_active);
CREATE INDEX idx_last_update ON routers(last_update);

-- =====================================================
-- TABLE: topology_links
-- Stores network topology (bidirectional links)
-- =====================================================
CREATE TABLE IF NOT EXISTS topology_links (
    link_id INT AUTO_INCREMENT PRIMARY KEY,
    router1 VARCHAR(10) NOT NULL,
    router2 VARCHAR(10) NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT different_routers CHECK (router1 != router2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE UNIQUE INDEX unique_link ON topology_links(router1, router2);
CREATE INDEX idx_topology_routers ON topology_links(router1, router2);
CREATE INDEX idx_topology_cost ON topology_links(cost);

-- =====================================================
-- TABLE: routing_tables
-- Stores computed routing tables history
-- =====================================================
CREATE TABLE IF NOT EXISTS routing_tables (
    table_id INT AUTO_INCREMENT PRIMARY KEY,
    router_id VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    next_hop VARCHAR(10) NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_routing_router ON routing_tables(router_id);
CREATE INDEX idx_routing_current ON routing_tables(is_current);
CREATE INDEX idx_routing_computed ON routing_tables(computed_at);
CREATE INDEX idx_routing_cost ON routing_tables(cost);

-- =====================================================
-- TABLE: neighbor_relationships
-- Stores neighbor announcements from routers
-- =====================================================
CREATE TABLE IF NOT EXISTS neighbor_relationships (
    relationship_id INT AUTO_INCREMENT PRIMARY KEY,
    router_id VARCHAR(10) NOT NULL,
    neighbor_id VARCHAR(10) NOT NULL,
    announced_cost DECIMAL(10,2) NOT NULL,
    announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_neighbor_router ON neighbor_relationships(router_id);
CREATE INDEX idx_neighbor_id ON neighbor_relationships(neighbor_id);

-- =====================================================
-- TABLE: events_log
-- Stores system events for auditing
-- =====================================================
CREATE TABLE IF NOT EXISTS events_log (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    event_description TEXT,
    router_id VARCHAR(10) NULL,
    details TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_events_type ON events_log(event_type);
CREATE INDEX idx_events_router ON events_log(router_id);
CREATE INDEX idx_events_created ON events_log(created_at);

-- =====================================================
-- TABLE: system_configuration
-- Stores system parameters
-- =====================================================
CREATE TABLE IF NOT EXISTS system_configuration (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- DEFAULT DATA
-- =====================================================

-- Insert default configuration
INSERT IGNORE INTO system_configuration (config_key, config_value, description) VALUES
('dijkstra_auto_recompute', 'true', 'Auto-recompute routes on topology change'),
('max_routers', '100', 'Maximum number of supported routers'),
('connection_timeout', '30', 'TCP connection timeout in seconds'),
('backup_interval', '300', 'Backup interval in seconds');

-- Insert demo routers
INSERT IGNORE INTO routers (router_id, ip_address, port_number, is_active) VALUES
('R1', '127.0.0.1', 5001, TRUE),
('R2', '127.0.0.1', 5002, TRUE),
('R3', '127.0.0.1', 5003, TRUE),
('R4', '127.0.0.1', 5004, TRUE);

-- Insert demo topology (4 routers, 5 links)
INSERT IGNORE INTO topology_links (router1, router2, cost, is_active) VALUES
('R1', 'R2', 2, TRUE),
('R1', 'R3', 5, TRUE),
('R1', 'R4', 4, TRUE),
('R2', 'R3', 1, TRUE),
('R3', 'R4', 3, TRUE);

-- Insert initialization event
INSERT INTO events_log (event_type, event_description, details) VALUES
('SYSTEM_INIT', 'Database initialized with demo topology', '{"version": "1.0"}');

-- =====================================================
-- VIEWS
-- =====================================================

CREATE OR REPLACE VIEW v_current_topology AS
SELECT router1, router2, cost, updated_at as last_updated
FROM topology_links WHERE is_active = TRUE;

CREATE OR REPLACE VIEW v_active_routers AS
SELECT router_id, ip_address, port_number, last_update
FROM routers WHERE is_active = TRUE;

CREATE OR REPLACE VIEW v_current_routing_tables AS
SELECT router_id, destination, next_hop, cost, computed_at
FROM routing_tables WHERE is_current = TRUE ORDER BY router_id, destination;

-- =====================================================
-- VERIFICATION
-- =====================================================
SELECT 'Database setup complete!' as Status;
SELECT COUNT(*) as Total_Routers FROM routers;
SELECT COUNT(*) as Total_Links FROM topology_links;