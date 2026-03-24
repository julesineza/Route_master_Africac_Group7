CREATE DATABASE IF NOT EXISTS load_consolidation;
USE load_consolidation;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('trader', 'carrier', 'admin') NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE carriers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    company_name VARCHAR(150) NOT NULL,
    license_number VARCHAR(100),
    average_rating DECIMAL(3,2) DEFAULT 0.00,
    total_reviews INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    origin_city VARCHAR(100) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    distance_km DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE containers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    carrier_id INT NOT NULL,
    route_id INT NOT NULL,
    container_type ENUM('20ft', '40ft', 'truck_small', 'truck_large') NOT NULL,
    max_weight_kg DECIMAL(10,2) NOT NULL,
    max_cbm DECIMAL(10,2) NOT NULL,
    price_weight DECIMAL(10,2) NOT NULL,
    price_cbm DECIMAL(10,2) NOT NULL,
    departure_date DATE NOT NULL,
    status ENUM('open', 'full', 'in_transit', 'completed', 'cancelled') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (carrier_id) REFERENCES carriers(id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
);

CREATE TABLE shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    container_id INT NOT NULL,
    trader_id INT NOT NULL,
    total_weight_kg DECIMAL(10,2) NOT NULL,
    total_cbm DECIMAL(10,2) NOT NULL,
    calculated_price DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (container_id) REFERENCES containers(id) ON DELETE CASCADE,
    FOREIGN KEY (trader_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE shipment_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    product_type VARCHAR(100),
    weight_kg DECIMAL(10,2) NOT NULL,
    cbm DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
);

CREATE TABLE ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,
    carrier_id INT NOT NULL,
    trader_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (carrier_id) REFERENCES carriers(id) ON DELETE CASCADE,
    FOREIGN KEY (trader_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_expires_used (expires_at, used),
  CONSTRAINT fk_password_resets_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
);

CREATE INDEX idx_route_origin_destination ON routes(origin_city, destination_city);
CREATE INDEX idx_container_route ON containers(route_id);
CREATE INDEX idx_container_status ON containers(status);
CREATE INDEX idx_shipment_container ON shipments(container_id);
CREATE INDEX idx_shipments_container_trader ON shipments(container_id, trader_id);