#!/bin/bash
files=("$@")
for file in "${files[@]}"
do
    if [[ "$file" == *".js" ]]
    then
        filename=${file%.js}
        curl -X POST -s --data-urlencode input@$filename.js http://javascript-minifier.com/raw > $filename.min.js
        chmod 644 $filename.min.js
    elif [[ "$file" == *".css" ]]
    then
        filename=${file%.css}
        curl -X POST -s --data-urlencode input@$filename.css http://cssminifier.com/raw > $filename.min.css
        chmod 644 $filename.min.css
    fi
done
