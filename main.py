import json
import math
import requests
import schedule
import time

GET_DETAILED_SALES = "https://partner.steam-api.com/IPartnerFinancialsService/GetDetailedSales/v001/"
GET_CHANGED_DATES = "https://partner.steam-api.com/IPartnerFinancialsService/GetChangedDatesForPartner/v001/"
GET_REVIEWS = "https://store.steampowered.com/appreviews/%s"

NTFY_TOPIC_ENDPOINT = "https://ntfy.sh/your-topic-name-here"

def post_message(message : str) -> None:
	print("Sending message: '%s'" % (message))
	response = requests.post(NTFY_TOPIC_ENDPOINT, data=message.encode(encoding="utf-8"))
	if not response.ok:
		print(response.status_code)

def main() -> None:
	try:
		fetch_sales()
		fetch_reviews()
	except Exception as e:
		print("Main exception: %s" % (str(e)))

def fetch_sales() -> None:
	current_sales = get_current_sales()

	dates_watermark = get_dates_watermark()
	dates, new_watermark = get_changed_dates(dates_watermark)
	if new_watermark == dates_watermark:
		print("No new sales")
		return
	
	initial_sales_metrics = get_sales_metrics(current_sales)
	
	for date in dates:
		print(date)
		updated_sales_data = get_sales_for_date(date, "0")
		for app_id in updated_sales_data:
			if app_id not in current_sales:
				current_sales[app_id] = {}
			if date not in current_sales[app_id] or current_sales[app_id][date]["gross_units"] != updated_sales_data[app_id]["gross_units"]:
				current_sales[app_id][date] = updated_sales_data[app_id]
	
	updated_sales_metrics = get_sales_metrics(current_sales)

	for app_id in current_sales:
		if app_id not in initial_sales_metrics:
			initial_sales_count = 0
		else:
			initial_sales_count, initial_sales_profit = initial_sales_metrics[app_id]
		updated_sales_count, updated_sales_profit = updated_sales_metrics[app_id]

		if updated_sales_count != initial_sales_count:
			actual_profit = math.floor(updated_sales_profit * 0.7)
			sales_count_diff = updated_sales_count - initial_sales_count
			diff_sign = "+" if sales_count_diff >= 0 else "-"
			formatted_profit = "{:,}".format(actual_profit)
			message = "%s\nUnits: %d (%s%d)\nProfit: $%s" % (app_id, updated_sales_count, diff_sign, sales_count_diff, formatted_profit)
			post_message(message)
	
	set_current_sales(current_sales)
	set_dates_watermark(new_watermark)

def get_sales_metrics(sales_data : dict[str, dict]) -> dict[str, (int, float)]:
	sales_metrics = {}
	for app_id in sales_data:
		total_units = 0
		total_profit = 0.0
		for date in sales_data[app_id]:
			total_units += sales_data[app_id][date]["gross_units"]
			total_profit += sales_data[app_id][date]["net_sales"]
		sales_metrics[app_id] = (total_units, total_profit)
	return sales_metrics

def fetch_reviews() -> None:
	current_sales = get_current_sales()
	current_reviews = get_current_reviews()
	
	for app_id in current_sales:
		app_reviews = get_reviews_for_app(app_id)
		if len(app_reviews) != 0:
			if app_id not in current_reviews or app_reviews["total"] != current_reviews[app_id]["total"]:
				message = "%s\nTotal Reviews: %d\nReview Score: %.1f" % (app_id, app_reviews["total"], 100.0 * app_reviews["positive"] / app_reviews["total"])
				post_message(message)
			current_reviews[app_id] = app_reviews
	
	set_current_reviews(current_reviews)

def get_reviews_for_app(app_id : str) -> dict[str, int]:
	response = requests.get(GET_REVIEWS % (app_id), {"json": "1", "language": "all", "num_per_page": "0"}, timeout=10)
	if response.ok:
		response_json = response.json()
		if "success" in response_json and response_json["success"] == 1:
			total = response_json["query_summary"]["total_reviews"]
			positive = response_json["query_summary"]["total_positive"]
			negative = response_json["query_summary"]["total_negative"]
			return {"total": total, "positive": positive, "negative": negative}
	return {}

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
	
	print(response.status_code)
	return [], watermark

def get_api_key() -> str:
	return read_file_line("api_key.txt").replace("\n", "")

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

def get_current_reviews() -> dict[str, dict]: # (app_id -> {"total", "positive", "negative"})
	try:
		return read_file_json("current_reviews.json")
	except:
		return {}

def set_current_reviews(data : dict[str, dict]) -> None:
	write_file_json("current_reviews.json", data)

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
		schedule.every(60).minutes.do(main)
		while True:
			schedule.run_pending()
			time.sleep(15)
	except Exception as ex:
		print(ex)
		raise
