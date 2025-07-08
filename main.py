import json
import requests

GET_DETAILED_SALES = "https://partner.steam-api.com/IPartnerFinancialsService/GetDetailedSales/v001/"
GET_CHANGED_DATES = "https://partner.steam-api.com/IPartnerFinancialsService/GetChangedDatesForPartner/v001/"

def main() -> None:
	pass

def get_api_key() -> str:
	with open("api_key.txt", "r") as file:
		return file.readline()

def get_sales_for_date(date : str, api_key : str, watermark : int = 0) -> int:
	response = requests.get(GET_DETAILED_SALES, {"date": date, "key": api_key, "highwatermark_id": watermark}, timeout=10)
	if response.ok:
		results = response.json().response.results
		count = 0
		for data in results:
			if "gross_units_sold" in data:
				count += data["gross_units_sold"]
		return count
	return -1

def get_request(url : str, headers : dict):
	response = requests.get(url, headers=headers, timeout=10)
	if response.ok:
		return response.json()
	return None

if __name__ == "__main__":
	main()