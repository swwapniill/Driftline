from datetime import date, timedelta

DATASET_START = date(2020, 11, 1)
DATASET_LENGTH_DAYS = 92  # Nov 1 2020 to Jan 31 2021
ANCHOR_DATE = date(2026, 9, 20)  # "day zero" of the simulation — today

def get_simulated_date(real_today=None):
    if real_today is None:
        real_today = date.today()
    offset_days = (real_today - ANCHOR_DATE).days
    mapped_offset = offset_days % DATASET_LENGTH_DAYS
    simulated_date = DATASET_START + timedelta(days=mapped_offset)
    return simulated_date.strftime('%Y%m%d')

if __name__ == "__main__":
    print("Simulated date for today:", get_simulated_date())
    # test a few future dates to confirm it cycles correctly
    for i in [0, 1, 50, 91, 92, 93]:
        test_date = ANCHOR_DATE + timedelta(days=i)
        print(f"real date {test_date} -> simulated {get_simulated_date(test_date)}")
