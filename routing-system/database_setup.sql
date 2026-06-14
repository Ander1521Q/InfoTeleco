CREATE DATABASE IF NOT EXISTS centralized_routing_db
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE centralized_routing_db;

-- DISCONNECTED = perdió conexión TCP
-- INACTIVE     = apagado manualmente por el admin
CREATE TABLE IF NOT EXISTS routers (
    router_id   VARCHAR(50)  NOT NULL,
    ip          VARCHAR(45)  NOT NULL,
    port        INT          NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (router_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS topology (
    id           INT          NOT NULL AUTO_INCREMENT,
    router_id    VARCHAR(50)  NOT NULL,
    neighbor_id  VARCHAR(50)  NOT NULL,
    cost         DOUBLE       NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_link (router_id, neighbor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS routing_tables (
    id           INT          NOT NULL AUTO_INCREMENT,
    router_id    VARCHAR(50)  NOT NULL,
    destination  VARCHAR(50)  NOT NULL,
    next_hop     VARCHAR(50)  NOT NULL,
    cost         DOUBLE       NOT NULL,
    computed_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_route (router_id, destination)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE OR REPLACE VIEW v_network_state AS
    SELECT  r.router_id, r.ip, r.port, r.status,
            COUNT(t.id) AS link_count
    FROM    routers r
    LEFT JOIN topology t ON t.router_id = r.router_id
    GROUP BY r.router_id, r.ip, r.port, r.status
    ORDER BY r.router_id;

CREATE OR REPLACE VIEW v_topology AS
    SELECT router_id AS source, neighbor_id AS destination, cost
    FROM   topology ORDER BY router_id, neighbor_id;

CREATE OR REPLACE VIEW v_routing_tables AS
    SELECT router_id, destination, next_hop, cost, computed_at
    FROM   routing_tables ORDER BY router_id, cost;
