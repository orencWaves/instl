-- noinspection SqlNoDataSourceInspectionForFile

-- item found on disk that has a guid. This trigger will find the IID
-- for that guid in IndexItemDetailRow and update the found_installed_binaries_t row
CREATE TRIGGER IF NOT EXISTS add_iid_to_FoundOnDiskItemRow_guid_not_null
AFTER INSERT ON found_installed_binaries_t
    WHEN(NEW.guid IS NOT NULL)
BEGIN
    UPDATE found_installed_binaries_t
    SET iid  = (
        SELECT name_item_t.owner_iid
        FROM IndexItemDetailRow AS guid_item_t
          JOIN IndexItemDetailRow AS name_item_t
            ON (name_item_t.detail_name = 'install_sources'
              OR
              name_item_t.detail_name = 'previous_sources')
            AND name_item_t.detail_value LIKE '%' || NEW.name
            AND name_item_t.owner_iid=guid_item_t.owner_iid
        WHERE guid_item_t.detail_name='guid'
          AND guid_item_t.detail_value=NEW.guid)
   WHERE found_installed_binaries_t._id=NEW._id;
END;

-- item found on disk that has no guid. This trigger will find the IID
-- for that  in IndexItemDetailRow by comparing the file's name and update the found_installed_binaries_t row
CREATE TRIGGER IF NOT EXISTS add_iid_to_FoundOnDiskItemRow_guid_is_null
AFTER INSERT ON found_installed_binaries_t
    WHEN NEW.guid IS NULL
BEGIN
    UPDATE OR IGNORE found_installed_binaries_t
    SET iid  = (
        SELECT IndexItemDetailRow.owner_iid
        FROM IndexItemDetailRow
        WHERE (detail_name='install_sources' OR detail_name='previous_sources')
        AND detail_value LIKE '%' || NEW.name)
   WHERE found_installed_binaries_t._id=NEW._id;
END;
-- when reading "require_by" detail, add to require_translate_t table
CREATE TRIGGER IF NOT EXISTS translate_require_by_trigger
    AFTER INSERT ON IndexItemDetailRow
    WHEN NEW.detail_name="require_by"
BEGIN
    INSERT OR IGNORE INTO require_translate_t (iid, require_by, status)
    VALUES (NEW.owner_iid,  NEW.detail_value, 0);
END;

CREATE TRIGGER IF NOT EXISTS create_require_by_for_main_iids_trigger
AFTER UPDATE OF install_status ON IndexItemRow
WHEN NEW.install_status = 1  -- 1 means iid requested explicitly by the user (not update or dependant)
AND NEW.ignore = 0
BEGIN
  -- self-referenced require_by for main install iids
  INSERT OR IGNORE INTO IndexItemDetailRow (original_iid, owner_iid, os_id, detail_name, detail_value, generation)
  VALUES (NEW.iid, NEW.iid, 0, 'require_by', NEW.iid, 0);
END;

CREATE TRIGGER IF NOT EXISTS create_require_for_all_iids_trigger
AFTER UPDATE OF install_status ON IndexItemRow
WHEN NEW.install_status > 0
AND NEW.ignore = 0
BEGIN
  -- remove previous require_version, require_guid owned NEW.iid
  DELETE FROM IndexItemDetailRow
  WHERE owner_iid = NEW.iid
  AND detail_name IN ("require_version", "require_guid");

  -- add require_version
  INSERT OR IGNORE INTO IndexItemDetailRow (original_iid, owner_iid, os_id, detail_name, detail_value, generation)
  SELECT original_iid, owner_iid, os_id, 'require_version', detail_value, min(generation)
  FROM IndexItemDetailRow
  WHERE owner_iid  = NEW.iid
  AND os_is_active = 1
  AND detail_name='version'
  GROUP BY owner_iid;

  -- add require_guid
  INSERT OR IGNORE INTO IndexItemDetailRow (original_iid, owner_iid, os_id, detail_name, detail_value, generation)
  SELECT original_iid, owner_iid, os_id, 'require_guid', detail_value, min(generation)
  FROM IndexItemDetailRow
  WHERE IndexItemDetailRow.owner_iid = NEW.iid
  AND os_is_active = 1
  AND detail_name='guid'
  GROUP BY owner_iid;

  -- require_by for all dependant of new iid
  INSERT OR IGNORE INTO IndexItemDetailRow (original_iid, owner_iid, os_id, detail_name, detail_value, generation)
  SELECT original_iid, detail_value, os_id, 'require_by', NEW.iid, generation
  FROM IndexItemDetailRow
  WHERE IndexItemDetailRow.owner_iid = NEW.iid
  AND os_is_active = 1
  AND detail_name='depends';
END;

-- when changing the status of item to uninstall, remove item's require_XXX details
CREATE TRIGGER IF NOT EXISTS remove_require_for_uninstalled_iids_trigger
AFTER UPDATE OF install_status ON IndexItemRow
WHEN NEW.install_status < 0
AND NEW.ignore = 0
BEGIN
    DELETE FROM IndexItemDetailRow
    WHERE IndexItemDetailRow.owner_iid=NEW.iid
    AND IndexItemDetailRow.detail_name LIKE "req%";

    DELETE FROM IndexItemDetailRow
    WHERE IndexItemDetailRow.detail_value=NEW.iid
    AND IndexItemDetailRow.detail_name = "require_by";
END;

-- when an os becomes active/de-active set all details accordingly
CREATE TRIGGER IF NOT EXISTS adjust_active_os_for_details
AFTER UPDATE OF os_is_active ON active_operating_systems_t
BEGIN
    UPDATE IndexItemDetailRow
    SET    os_is_active =  NEW.os_is_active
    WHERE  IndexItemDetailRow.os_id = NEW._id;
END;

-- when adding new detail set it's active state according to os
CREATE TRIGGER IF NOT EXISTS set_active_os_for_details
AFTER INSERT ON IndexItemDetailRow
BEGIN
     UPDATE IndexItemDetailRow
     SET os_is_active = (SELECT active_operating_systems_t.os_is_active
                    FROM active_operating_systems_t
                    WHERE active_operating_systems_t._id=NEW.os_id)
     WHERE IndexItemDetailRow._id = NEW._id;
END;
