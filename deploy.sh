#!/bin/zsh
# Publish the site to the Hetzner box (same pattern as the other playground demos).
#   ./deploy.sh
set -e
cd "$HOME/playground/EuroGrants"

STAMP=$(date +%Y%m%d%H%M%S)
sed -i '' "s/const DATA_V='[^']*'/const DATA_V='${STAMP}'/" site/index.html
echo "data version stamped: ${STAMP}"

rsync -avz --delete site/ dictionaryofml:html/who-gets-the-grants/
echo "DEPLOY COMPLETE: https://dictionaryofml.org/who-gets-the-grants/"
