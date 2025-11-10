#!/usr/bin/env bash

win_token_path="$(wslpath -u 'c:/Users/ZheRao/OneDrive - Monette Farms/Monette Farms Team Site - Innovation Projects/Production/Database/Bronze/Authentication/QBO/')"
wsl_token_path=~/projects/ETLPipeline/Database/.inputs/dev/


# Windows to Linux
rsync -av --ignore-times "$win_token_path" "$wsl_token_path"

# backup tokens file
cd ~/projects/ETLPipeline/Database/.inputs/dev
cp tokens.json copies_Linux/tokens.json


# Linux to Windows 
 rsync -av --ignore-times "$wsl_token_path" "$win_token_path"
