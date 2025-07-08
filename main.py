import json
import requests
import schedule
import time

GET_DETAILED_SALES = "https://partner.steam-api.com/IPartnerFinancialsService/GetDetailedSales/v001/"
GET_CHANGED_DATES = "https://partner.steam-api.com/IPartnerFinancialsService/GetChangedDatesForPartner/v001/"

def main() -> None:
	current_sales = get_current_sales()

	dates_watermark = get_dates_watermark()
	dates, new_watermark = get_changed_dates(dates_watermark)
	if new_watermark == dates_watermark:
		return
	
	changed_app_ids = {}
	for date in dates:
		print(date)
		sales_data = get_sales_for_date(date, "0")
		for app_id in sales_data:
			if app_id not in current_sales:
				current_sales[app_id] = {}
			current_sales[app_id][date] = sales_data[app_id]
			changed_app_ids[app_id] = True
	
	for app_id in current_sales:
		total_units = 0
		total_profit = 0.0
		for date in current_sales[app_id]:
			total_units += current_sales[app_id][date]["gross_units"]
			total_profit += current_sales[app_id][date]["net_sales"]
		
		total_profit *= 0.7
		if app_id in changed_app_ids:
			print("%s has sold %d units for a total of $%.2f" % (app_id, total_units, total_profit))
	
	set_current_sales(current_sales)
	set_dates_watermark(new_watermark)

def get_sales_for_date(date : str, watermark : str) -> dict[str, dict]: # (app_id -> Sales Data dict)
	response = requests.get(GET_DETAILED_SALES, {"date": date, "key": get_api_key(), "highwatermark_id": watermark}, timeout=10)
	if response.ok:
		response_json = response.json()
		results = response_json["response"]["results"]
		sales_dict = {}
		for data in results:
			if "primary_appid" in data and "gross_units_sold" in data and "net_units_sold" in data and "net_sales_usd" in data:
				app_id = str(data["primary_appid"])
				if app_id not in sales_dict:
					sales_dict[app_id] = {"app_id": app_id, "gross_units": 0, "net_units": 0, "net_sales": 0.0}
				
				sales_dict[app_id]["gross_units"] += data["gross_units_sold"]
				sales_dict[app_id]["net_units"] += data["net_units_sold"]
				sales_dict[app_id]["net_sales"] += float(data["net_sales_usd"])
		return sales_dict
	return None

def get_changed_dates(watermark : str = "0") -> (list[str], int):
	response = requests.get(GET_CHANGED_DATES, {"key": get_api_key(), "highwatermark_id": watermark}, timeout=10)
	if response.ok:
		response_json = response.json()
		dates = []
		if "dates" in response_json["response"]:
			dates = response_json["response"]["dates"]
		new_watermark = response_json["response"]["result_highwatermark"]
		return (dates, new_watermark)
	else:
		print(response.status_code)
	return None

def get_api_key() -> str:
	return read_file_line("api_key.txt")

def get_dates_watermark() -> str:
	return read_file_line("watermark_changed_dates.txt")

def set_dates_watermark(new_watermark : str) -> None:
	write_file_line("watermark_changed_dates.txt", new_watermark)

def get_current_sales() -> dict[str, dict]: # (app_id -> (date -> Sales Data dict))
	try:
		return read_file_json("current_sales.json")
	except:
		return {}

def set_current_sales(data : dict[str, dict]) -> None:
	write_file_json("current_sales.json", data)

def read_file_line(filename : str) -> str:
	with open(filename, "r") as file:
		return file.readline()

def write_file_line(filename : str, line : str) -> None:
	with open(filename, "w") as file:
		file.write(line)

def read_file_json(filename : str):
	with open(filename, "r") as file:
		return json.load(file)

def write_file_json(filename : str, data : dict) -> None:
	with open(filename, "w") as file:
		json.dump(data, file)

if __name__ == "__main__":
	try:
		main()
		schedule.every(5).minutes.do(main)
		while True:
			schedule.run_pending()
			time.sleep(5)
	except Exception as ex:
		print(ex)
		raise
