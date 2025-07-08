# Steam-Info-Fetcher
Python script for retrieving Steam app info and publishing to ntfy.sh

## Requirements
### Create API Key
https://store.steampowered.com/news/group/4145017/view/532096678169150061

### Update api_key.txt
Copy your API key into this text file. It must be on the first line of the file by itself.

### Install Python Library
`pip install schedule`

## Executing the Script
`python main.py`

## Resetting Saved Data
"current_sales.json" and "watermark_changed_dates.txt" will update after running the script. If these files get corrupted or you need to refetch all dates for some reason, overwrite the files with their default values.

current_sales.json
```
{}
```

watermark_changed_dates.txt
```
0
```
