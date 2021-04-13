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
