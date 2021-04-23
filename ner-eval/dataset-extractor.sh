#!/bin/bash
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
	file="$lang/$meeting/${name}/${date}.raw"
	mkdir -p "$(dirname "$file")"
	echo -n "Writing $file"
	jq -r '.annotated_content' <<< "${line}" > "$file"
	#jq -r '.content' <<< "${line}" > "$file"
	echo " ($(cat "$file" | wc -w) words)"
done

# Data info
echo "[DONE] $(find -mindepth 3 -type d | wc -l) found"

# Clear duplicities (leaving only newest files)
find -mindepth 3 -type d | while read file; do
    todo=$(ls "$file" | grep .raw | head -n-1 | wc -l)
	if [ $todo -gt 0 ]; then
		echo "Removing $todo duplicties from $file"
		ls "$file" | grep .raw | head -n-1 | awk "{print \"$file/\"\$1}" | xargs -d "\n" rm
	fi
done

# Extract features
echo "Extracting features..."
find -mindepth 3 -type f -name "*.raw" | while read file; do
	folder="$(dirname "$file")"
	fixed="$folder/input.xml"
	cat <(echo "<?xml version=\"1.0\" encoding=\"utf-8\" ?>") <(echo "<txt>") "$file" <(echo -n "</txt>") > "$fixed"
	sed -i "s/\&nbsp;/ /g;s/<br>//g;" "$fixed"
	python3 ../feature_digger.py "$fixed" "$folder/features.csv" "$folder/input.txt"
done
echo "[DONE] $(find -name "features.csv" -exec wc -l {} \; | cut -f1 -d" " | awk '{ sum += $1 } END { print sum }') found"
