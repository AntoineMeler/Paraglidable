import os
import inc.google_drive_downloader

scripts_dir = os.path.dirname(os.path.realpath(__file__))

root_dir = scripts_dir + "/.."
dest_dir = root_dir + "/neural_network/bin/data"

files = [("12h64ld1wTxuz12o35eWWmtQVA2V9-QMk", "flights_by_cell_day_spot.pkl.zip"),
		 ("15IeY97EmMvR-wDAsZunlWoAp7ePkId4v", "flights_by_cell_day.pkl.zip"),
		 ("1sJRxQxTgZOav9EdlOAF4IR8-PLW7aa_F", "flights_by_spot.pkl.zip"),
		 ("1zC2M_19roJK0ktZLDY8wQoQG1p_aoMA3", "meteo_content_by_cell_day.pkl.zip"),
		 ("1x-vPcQ-EALIG6axTNlYZlP5cGH_1UljP", "meteo_days.pkl.zip"),
		 ("1NAAeci_TkEV3O65jsWfPyI7_3umgO3g8", "meteo_params.pkl.zip"),
		 ("1yjjgJqBdEq1zrNLidcyq5w4wJCPkNASp", "mountainess_by_cell_alt.pkl.zip"),
		 ("17SPU9JYV3fAQ0MdrbqMOCArSo6JghEVz", "sorted_cells_latlon.pkl.zip"),
		 ("1viHJFMGjFbBfLpFStNHkw8r-uf-pRTLn", "sorted_cells.pkl.zip"),
		 ("1IZAIPq6kG6f_k48mtuKFniV-wxme4633", "spots_by_cell.pkl.zip"),
		 ("1NNRn1f3_E4XbM7rvWqz7C1LYrvik1WC7", "spots_merged.pkl.zip"),
		 ("1FgkfCzmJmsEmZ_LZIHggBAcOhDZZwTK1", "spots.pkl.zip")]

for file_id, res_file in files:
	print("Downloading", dest_dir+"/"+res_file, "...")
	inc.google_drive_downloader.download(file_id, dest_dir, res_file)
