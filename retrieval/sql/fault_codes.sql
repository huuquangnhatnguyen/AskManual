-- AS2.3: one row per fault/warning table row, per family. Rebuilt from chunks.jsonl, never edited by hand.
-- A code is unique only within a family: 2330 exists in both ACS580 and ACS880.
CREATE TABLE IF NOT EXISTS fault_codes (
    code            text    NOT NULL,          -- 4 uppercase hex, e.g. '2330', 'A2B1'
    product_family  text    NOT NULL,          -- one row per family the document covers
    doc_id          text    NOT NULL,
    page            integer NOT NULL,
    chunk_id        text    NOT NULL,
    text            text    NOT NULL,
    PRIMARY KEY (code, product_family, chunk_id)
);
CREATE INDEX IF NOT EXISTS fault_codes_code_family ON fault_codes (code, product_family);
