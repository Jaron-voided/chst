for r in $(grep -oE '^\| \*\*(HDR|TRL|SEC|BLB|ENT|PATH|CAN|LIM)-[0-9]+\*\*' FORMAT_SPEC.md | tr -d '|* ' | sort -u); do
  [ "$r" = LIM-6 ] && continue                                  # Extended-only (encoded blobs)
  compgen -G "$FX/core/invalid/$r.*" > /dev/null || compgen -G "$FX/core/invalid/$r-*.chst" > /dev/null \
    || { echo "missing $r"; exit 1; }
done
for n in TRL-2-low TRL-2-overflow SEC-1-straddle SEC-3-repeat SEC-5-entry BLB-4-zero-blobs BLB-4-short-last \
         ENT-1-type0 PATH-2-unicode16 PATH-3-empty PATH-3-2 PATH-6-c1 PATH-6-bidi PATH-6-isolate PATH-9-2 PATH-9-3 \
         PATH-9-com0 PATH-9-com1sup PATH-9-com2sup PATH-9-com3sup PATH-9-lpt1sup PATH-9-lpt2sup PATH-9-lpt3sup ENT-6-2 \
         PATH-6-rlm PATH-6-alm; do
  test -f "$FX/core/invalid/$n.expect.json" || { echo "missing sub-condition fixture $n"; exit 1; }
done
