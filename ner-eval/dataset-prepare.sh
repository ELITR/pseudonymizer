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
	name=$(jq -r .name <<< "${line}")

	# Parsing
	file=$lang/$meeting/${name}/$oid
	mkdir -p "$(dirname "$file")"
	echo -n "Writing $file"
	jq -r '.annotated_content' <<< "${line}" > "$file"
	#jq -r '.content' <<< "${line}" > "$file"
	echo " ($(cat "$file" | wc -w) words)"
done
