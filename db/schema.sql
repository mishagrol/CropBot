-- Features
PRAGMA foreign_keys = ON;


-- Tables
CREATE TABLE users
(
    id      INT PRIMARY KEY NOT NULL,
    name    TEXT            NOT NULL,
    UNIQUE(id)
);

CREATE TABLE fields
(
    id         TEXT PRIMARY KEY          NOT NULL,
    name       TEXT                      NOT NULL,
    creator_id INT REFERENCES users (id) NOT NULL,
    latitude   INT                       NOT NULL,
    longitude  INT                       NOT NULL,
    crop_start DATE                      NOT NULL, 
    crop_end   DATE                      NOT NULL, 
    crop_name  TEXT                      NOT NULL,
    UNIQUE(id),
    FOREIGN KEY (creator_id) REFERENCES users (id) ON DELETE CASCADE

);

CREATE TABLE irrigations
(
    id         TEXT PRIMARY KEY          NOT NULL,
    field_id   INT                       NOT NULL,
    date       DATE                       NOT NULL,
    amount     DECIMAL                   NOT NULL,
    UNIQUE(id),
    FOREIGN KEY (field_id) REFERENCES fields (id) ON DELETE CASCADE

);


CREATE TABLE npks
(
    id         TEXT PRIMARY KEY          NOT NULL,
    field_id   INT                      NOT NULL,
    date       DATE                       NOT NULL,
    npk         TEXT                   NOT NULL,    
    UNIQUE(id),
    FOREIGN KEY (field_id) REFERENCES fields (id) ON DELETE CASCADE

);


CREATE TABLE income
(
    id         TEXT PRIMARY KEY          NOT NULL,
    field_id   INT,
    income_per_ga     DECIMAL            NOT NULL,    
    UNIQUE(id),
    FOREIGN KEY (field_id) REFERENCES fields (id) ON DELETE CASCADE
);