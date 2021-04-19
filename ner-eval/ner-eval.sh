#!/bin/sh

function outputPipe {
	while read -r row; do
		input="$row"
		output="$(dirname "$row")/$1.csv"
		echo "$input;$output"
	done
}

# For each NER
for ner in "nametag" "nltk" "spacy"; do
	echo $ner
	find -name input.txt -path "./dataset/*" | outputPipe $ner | python3 ner_digger.py $ner 
done

mkdir -p ./dataset/out/
find "./dataset" -name input.txt -exec dirname {} \; | while read -r folder; do
	output="./dataset/out/$(echo "$folder" | cut -d"/" -f 4,5 | tr "/" "-").csv"
	find "$folder" -name "*.csv" | grep -v features.csv | xargs -d "\n" python3 summary_builder.py "$output" "$folder/features.csv"
done