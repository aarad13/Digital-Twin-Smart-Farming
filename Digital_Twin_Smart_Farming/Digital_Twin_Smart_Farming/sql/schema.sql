CREATE DATABASE IF NOT EXISTS smart_farming_digital_twin
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_farming_digital_twin;

CREATE TABLE IF NOT EXISTS farms (
    farm_id INT AUTO_INCREMENT PRIMARY KEY,
    farm_code VARCHAR(120) NOT NULL UNIQUE,
    display_name VARCHAR(160) NOT NULL,
    location VARCHAR(180) DEFAULT 'Kolkata, West Bengal, India',
    crop_name VARCHAR(120) DEFAULT NULL,
    soil_type VARCHAR(120) DEFAULT NULL,
    field_area_ha DECIMAL(10,3) DEFAULT NULL,
    moisture_threshold_pct DECIMAL(7,3) NOT NULL DEFAULT 12.000,
    threshold_note VARCHAR(255) DEFAULT 'Prototype threshold, requires crop/soil-specific verification',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS observations (
    observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    observed_at DATETIME NOT NULL,
    moisture_pct DECIMAL(9,4) NOT NULL,
    sensor_board_temp_c DECIMAL(9,4) NULL,
    raw_capacitive_adc INT NULL,
    sensor_voltage_v DECIMAL(9,4) NULL,
    atmospheric_pressure_inhg DECIMAL(9,4) NULL,
    atmospheric_temp_c DECIMAL(9,4) NULL,
    soil_temp_c DECIMAL(9,4) NULL,
    sm_level_15cm DECIMAL(9,4) NULL,
    sm_volume_15cm DECIMAL(9,4) NULL,
    sm_aggregate_pct DECIMAL(9,4) NULL,
    sm_volume_pct DECIMAL(9,4) NULL,
    hour_value TINYINT NULL,
    day_value TINYINT NULL,
    month_value TINYINT NULL,
    day_of_week TINYINT NULL,
    day_of_year SMALLINT NULL,
    hour_sin DECIMAL(9,6) NULL,
    hour_cos DECIMAL(9,6) NULL,
    day_sin DECIMAL(9,6) NULL,
    day_cos DECIMAL(9,6) NULL,
    source_name VARCHAR(120) NOT NULL DEFAULT 'EcoIrrigate dataset',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_observations_farm FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE CASCADE,
    CONSTRAINT uq_farm_observation_time UNIQUE (farm_id, observed_at),
    INDEX idx_observation_time (observed_at),
    INDEX idx_observation_farm_time (farm_id, observed_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    origin_at DATETIME NOT NULL,
    target_at DATETIME NOT NULL,
    horizon_minutes INT NOT NULL,
    model_name VARCHAR(80) NOT NULL,
    feature_set VARCHAR(80) NOT NULL,
    predicted_moisture_pct DECIMAL(9,4) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_forecasts_farm FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE CASCADE,
    INDEX idx_forecast_farm_time (farm_id, generated_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS advisories (
    advisory_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    forecast_id BIGINT NOT NULL,
    farm_id INT NOT NULL,
    current_moisture_pct DECIMAL(9,4) NOT NULL,
    predicted_moisture_pct DECIMAL(9,4) NOT NULL,
    threshold_pct DECIMAL(9,4) NOT NULL,
    advisory_level VARCHAR(30) NOT NULL,
    advisory_text VARCHAR(500) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_advisories_forecast FOREIGN KEY (forecast_id) REFERENCES forecasts(forecast_id) ON DELETE CASCADE,
    CONSTRAINT fk_advisories_farm FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE CASCADE,
    INDEX idx_advisories_farm_time (farm_id, generated_at)
) ENGINE=InnoDB;

-- User-defined Indian farm digital structures, separate from the two-farm
-- EcoIrrigate experimental dataset above.
CREATE TABLE IF NOT EXISTS virtual_farms (
    virtual_farm_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    farm_name VARCHAR(160) NOT NULL,
    village VARCHAR(120) NULL,
    district VARCHAR(120) NOT NULL,
    state VARCHAR(120) NOT NULL,
    country VARCHAR(80) NOT NULL DEFAULT 'India',
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    total_area_ha DECIMAL(12,4) NOT NULL,
    agro_climatic_zone_id VARCHAR(8) NULL,
    agro_climatic_zone_name VARCHAR(180) NULL,
    farming_system VARCHAR(100) NULL,
    land_form VARCHAR(80) NULL,
    water_source VARCHAR(100) NULL,
    primary_irrigation_method VARCHAR(100) NULL,
    boundary_geojson LONGTEXT NULL,
    climate_profile_json LONGTEXT NULL,
    soil_profile_json LONGTEXT NULL,
    regional_context_json LONGTEXT NULL,
    data_provenance_json LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_virtual_farm_region (state, district)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS virtual_farm_plots (
    plot_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    virtual_farm_id BIGINT NOT NULL,
    plot_code VARCHAR(40) NOT NULL,
    plot_name VARCHAR(120) NOT NULL,
    area_ha DECIMAL(12,4) NOT NULL,
    crop_name VARCHAR(120) NULL,
    crop_variety VARCHAR(120) NULL,
    season VARCHAR(30) NULL,
    sowing_date DATE NULL,
    crop_stage VARCHAR(80) NULL,
    indian_soil_group VARCHAR(100) NULL,
    soil_texture VARCHAR(100) NULL,
    soil_ph DECIMAL(5,2) NULL,
    soil_ec_ds_m DECIMAL(7,3) NULL,
    organic_carbon_pct DECIMAL(7,3) NULL,
    available_n_kg_ha DECIMAL(10,2) NULL,
    available_p_kg_ha DECIMAL(10,2) NULL,
    available_k_kg_ha DECIMAL(10,2) NULL,
    soil_test_source VARCHAR(100) NULL,
    soil_test_date DATE NULL,
    irrigation_method VARCHAR(100) NULL,
    water_source VARCHAR(100) NULL,
    boundary_geojson LONGTEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_vfarm_plot FOREIGN KEY (virtual_farm_id) REFERENCES virtual_farms(virtual_farm_id) ON DELETE CASCADE,
    UNIQUE KEY uq_virtual_farm_plot_code (virtual_farm_id, plot_code),
    INDEX idx_virtual_plot_crop_season (crop_name, season)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS virtual_farm_assets (
    asset_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    virtual_farm_id BIGINT NOT NULL,
    asset_type VARCHAR(80) NOT NULL,
    asset_name VARCHAR(120) NOT NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    capacity_or_size VARCHAR(100) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vfarm_asset FOREIGN KEY (virtual_farm_id) REFERENCES virtual_farms(virtual_farm_id) ON DELETE CASCADE,
    INDEX idx_virtual_asset_farm (virtual_farm_id)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS soil_reports (
    report_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    virtual_farm_id BIGINT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    report_source VARCHAR(100) NOT NULL DEFAULT 'Farmer-provided report',
    report_date DATE NULL,
    notes VARCHAR(1000) NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_soil_report_farm FOREIGN KEY (virtual_farm_id) REFERENCES virtual_farms(virtual_farm_id) ON DELETE CASCADE,
    INDEX idx_soil_report_farm_date (virtual_farm_id, uploaded_at)
) ENGINE=InnoDB;

-- Assisted village-service workflows. These records are entered by a field team
-- and authorised laboratory staff; farmers are not required to operate the app.
CREATE TABLE IF NOT EXISTS field_farmers (
    farmer_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    farmer_code VARCHAR(40) NOT NULL UNIQUE,
    farmer_name VARCHAR(160) NOT NULL,
    mobile VARCHAR(20) NULL,
    preferred_language VARCHAR(30) NOT NULL DEFAULT 'Hindi',
    village VARCHAR(120) NOT NULL,
    district VARCHAR(120) NOT NULL,
    state VARCHAR(120) NOT NULL,
    virtual_farm_id BIGINT NULL,
    farm_latitude DECIMAL(10,7) NULL,
    farm_longitude DECIMAL(10,7) NULL,
    farm_name VARCHAR(160) NULL,
    farm_area_ha DECIMAL(12,4) NULL,
    primary_crop VARCHAR(120) NULL,
    consent_recorded TINYINT(1) NOT NULL DEFAULT 0,
    consent_recorded_at DATETIME NULL,
    created_by VARCHAR(120) NOT NULL,
    registered_by_role VARCHAR(32) NULL,
    registered_by_organization VARCHAR(180) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_field_farmer_virtual_farm FOREIGN KEY (virtual_farm_id) REFERENCES virtual_farms(virtual_farm_id) ON DELETE SET NULL,
    INDEX idx_field_farmer_region (state, district, village),
    INDEX idx_field_farmer_name (farmer_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS field_visits (
    visit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    farmer_id BIGINT NOT NULL,
    officer_name VARCHAR(120) NOT NULL,
    visit_date DATETIME NOT NULL,
    visit_purpose VARCHAR(120) NOT NULL DEFAULT 'Farm registration and soil sampling',
    visit_status VARCHAR(30) NOT NULL DEFAULT 'Scheduled',
    notes VARCHAR(1000) NULL,
    officer_role VARCHAR(32) NULL,
    organization_name VARCHAR(180) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_field_visit_farmer FOREIGN KEY (farmer_id) REFERENCES field_farmers(farmer_id) ON DELETE CASCADE,
    INDEX idx_field_visit_date (visit_date, visit_status),
    INDEX idx_field_visit_farmer (farmer_id, visit_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS soil_samples (
    sample_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sample_code VARCHAR(48) NOT NULL UNIQUE,
    farmer_id BIGINT NOT NULL,
    sample_description VARCHAR(255) NULL,
    collected_by VARCHAR(120) NOT NULL,
    collected_at DATETIME NOT NULL,
    collection_role VARCHAR(32) NULL,
    collection_organization VARCHAR(180) NULL,
    assigned_lab_organization VARCHAR(180) NULL,
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    lab_name VARCHAR(180) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Collected',
    received_at DATETIME NULL,
    tested_at DATETIME NULL,
    tested_by VARCHAR(120) NULL,
    lab_role VARCHAR(32) NULL,
    lab_organization VARCHAR(180) NULL,
    soil_ph DECIMAL(5,2) NULL,
    soil_ec_ds_m DECIMAL(9,3) NULL,
    organic_carbon_pct DECIMAL(7,3) NULL,
    available_n_kg_ha DECIMAL(10,2) NULL,
    available_p_kg_ha DECIMAL(10,2) NULL,
    available_k_kg_ha DECIMAL(10,2) NULL,
    lab_verified TINYINT(1) NOT NULL DEFAULT 0,
    verified_by VARCHAR(120) NULL,
    verified_at DATETIME NULL,
    report_original_filename VARCHAR(255) NULL,
    report_stored_filename VARCHAR(255) NULL,
    report_mime_type VARCHAR(120) NULL,
    lab_notes VARCHAR(1500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_soil_sample_farmer FOREIGN KEY (farmer_id) REFERENCES field_farmers(farmer_id) ON DELETE CASCADE,
    INDEX idx_soil_sample_status (status, collected_at),
    INDEX idx_soil_sample_farmer (farmer_id, collected_at)
) ENGINE=InnoDB;

-- Local account identities. Organisation roles are provisioned by an administrator;
-- public users cannot self-assign government, company or laboratory roles.
CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    display_name VARCHAR(160) NOT NULL,
    organization_name VARCHAR(180) NULL,
    farmer_id BIGINT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    must_change_password TINYINT(1) NOT NULL DEFAULT 0,
    activation_code_hash VARCHAR(255) NULL,
    activation_expires_at DATETIME NULL,
    last_login_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_user_farmer FOREIGN KEY (farmer_id) REFERENCES field_farmers(farmer_id) ON DELETE SET NULL,
    INDEX idx_app_user_role (role),
    INDEX idx_app_user_farmer (farmer_id)
) ENGINE=InnoDB;
