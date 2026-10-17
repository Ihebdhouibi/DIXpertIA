-- Real errors in the configuration files on disk, read by the running server
-- before a restart (#158). Used by apply.sh, and rehearsed by ci-check.sh.
--
-- pg_file_settings also flags a valid setting that only takes effect at the
-- next restart (max_connections, shared_buffers - context "postmaster") with
-- "setting could not be applied". That is a pending change, not an error:
-- counting it stopped apply.sh before the very restart that applies it.
SELECT count(*)
FROM pg_file_settings f
LEFT JOIN pg_settings s ON s.name = f.name
WHERE f.error IS NOT NULL
  AND NOT (s.context = 'postmaster' AND f.error = 'setting could not be applied');
