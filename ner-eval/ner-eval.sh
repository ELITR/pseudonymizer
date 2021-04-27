#!/bin/sh

function outputPipe {
	while read -r row; do
		input="$row"
		output="$(dirname "$row")/$1.csv"
		output_plus="$(dirname "$row")/$1_plus.csv"
		echo "$input;$output;$output_plus"
	done
}

# For each NER
for ner in "nametag" "nltk" "spacy"; do
	echo $ner
	find -name input.txt -path "./dataset/*" | outputPipe $ner | python3 ner_digger.py $ner 
done

# Summary
echo "Building summary..."
mkdir -p ./dataset/out/
echo "test-name,ner,features,exact,inside,partial,lines" > "./dataset/out/summary.csv" 
find "./dataset" -name input.txt -exec dirname {} \; | while read -r folder; do
	test_name=$(echo "$folder" | cut -d"/" -f 4,5 | tr "/" "-")
	output="./dataset/out/$test_name.csv"
	find "$folder" -name "*.csv" | sort | grep -v features.csv | xargs -d "\n" python3 summary_builder.py "$test_name" "$output" "$folder/features.csv" >> "./dataset/out/summary.csv"
done
echo "... $(wc -l ./dataset/out/summary.csv) found"
