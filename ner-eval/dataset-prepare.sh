#!/bin/sh
cd dataset

# Create lang folders
jq -r '.[].language' data.json | sort | uniq | xargs mkdir -p

# For each entry in array
jq -c '.[]' data.json | while IFS=$"\n" read -r line
do
	# Stats
	lang=$(jq -r .language <<< "${line}")
	meeting=$(jq -r .meetingId <<< "${line}")
	oid=$(jq -r '._id."$oid"' <<< "${line}")
	date=$(jq -r '.createdAt."$date"' <<< "${line}")
	name=$(jq -r .name <<< "${line}")

	# Parsing
	file=$lang/$meeting/${name}/$date
	mkdir -p "$(dirname "$file")"
	echo -n "Writing $file"
	jq -r '.annotated_content' <<< "${line}" > "$file"
	#jq -r '.content' <<< "${line}" > "$file"
	echo " ($(cat "$file" | wc -w) words)"
done

# Data info
echo "Found $(find -mindepth 3 -type d | wc -l) texts"

# Clear duplicities (leaving only newest files)
find -mindepth 3 -type d | while read file; do
    todo=$(ls "$file" | head -n-1 | wc -l)
	if [ $todo -gt 0 ]; then
		echo "Removing $todo duplicties from $file"
		ls "$file" | head -n-1 | awk "{print \"$file/\"\$1}" | xargs -d "\n" rm
	fi
done