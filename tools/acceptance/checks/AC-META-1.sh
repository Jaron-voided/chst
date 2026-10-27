diff <(./check.sh --list-ids | sort) \
     <(grep -oE '^#### AC-[A-Z0-9-]+' ACCEPTANCE.md | cut -c6- | sort)
