#!/bin/bash
DIR="/home/amohs002/projects/research/ALLEGRO_Fungi_Downloader/data/fourdbs_concat/proteomes/"

for FILE in $(ls $DIR)
do
    NAME=$(echo "$FILE" | cut -d'.' -f1)
    diamond makedb --in $DIR$FILE -d inputs/databases/$NAME
done
