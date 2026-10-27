test "$(sha256 fixtures/MANIFEST.sha256)" = "$PINNED_MANIFEST_HASH"
(cd fixtures && { sha256sum --check --quiet MANIFEST.sha256 2>/dev/null || shasum -a 256 -c -s MANIFEST.sha256; })
diff <(cd fixtures && find . -type f ! -name MANIFEST.sha256 | sed 's|^\./||' | sort) \
     <(sed 's/^[0-9a-f]* [ *]//' fixtures/MANIFEST.sha256 | sort)
