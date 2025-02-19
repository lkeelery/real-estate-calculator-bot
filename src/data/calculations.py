"""Hub for all the calculations needed"""

import json
import os.path
from dataclasses import dataclass
from traceback import format_tb

import numpy_financial as npf

from src.data import user
from src.data.colors_for_print import BAD, OK, GOOD, GREAT, END
from src.data.database import amortization_table, drop_amortization_table, \
    create_amortization_table, add_amortization_data, get_amortization_table
from src.data.user import WebScraper, UserValues
from src.web.get_property_info import set_page_property_info, get_url


@dataclass
class PropertyInfo:
    """Contains information about the property"""
    down_payment: float
    loan: float
    interest_rate_monthly: float
    months: int
    property_taxes_monthly: float
    insurance_cost: float
    amortization_table: dict
    analysis: dict
    property_info: dict
    estimations = {}
    new_analysis_list = []


def update_values(url=None,
                  save_to_file=True,
                  update_interest_rate=True
                  ) -> bool:
    """Updates the values when a new property is being evaluated."""

    # These are what gets the html pages
    if update_interest_rate:
        user.set_interest_rate()
    set_page_property_info(url=url)

    # Logs errors if there are any and stop analysis of this specific
    # property ONLY.
    try:
        # Gets values from html pages
        user.set_info()

    # THE GOAL IS FOR THIS BLOCK TO NEVER BE EXECUTED.
    # IF IT DOES, THE PROGRAM STOPS THE ANALYSIS FOR THIS SPECIFIC PROPERTY.
    # This logs the error to ..\output\errors.log, what ever it is.
    # Complete with the problematic property url, traceback,
    # and type of exception.
    except Exception as exception:
        exception_name = exception.__class__.__qualname__

        extra = ""
        if exception_name == 'AttributeError':
            extra = "--- (IS THE PROPERTY OFF MARKET? IF SO YOU CAN DELETE " \
                    "THE URL IF IT WAS INDIVIDUALLY ADDED TO PROPERTY URLs. " \
                    "IF IT WAS ADDED BY A SEARCH URL, IGNORE THIS PROPERTY " \
                    "INSTEAD. FOR EITHER OPTION, " \
                    "RUN property_tracker.py.)---"

        # When printing analysis of a single property, url=None.
        # This allows that URL to be saved as well.
        if not url:
            url = get_url()

        # Get exception name as well as traceback info for easy debugging.
        tb_title = "Traceback (most recent call last):"
        traceback = format_tb(exception.__traceback__)
        tb_string = ""
        for tb in traceback:
            tb_string += tb

        # "###" can be used to navigate between errors in log file.
        error = f"### {url}: [\n" \
                f"{tb_title}\n" \
                f"{tb_string}" \
                f"{exception_name}: {exception}\n" \
                f"]{extra}\n\n"

        with open(os.path.join('output', 'errors.log'), 'a') as file:
            file.write(error)

        # Ends current analysis
        return False

    basic_calculations()

    PropertyInfo.amortization_table = mortgage_amortization()
    PropertyInfo.analysis = returns_analysis()
    PropertyInfo.property_info = {
        "Address": WebScraper.address,
        "Price ($)": WebScraper.price,
        "Year Built": WebScraper.year,
        "Description": WebScraper.description,
        "House Size (sqft)": WebScraper.sqft,
        "Price/sqft ($)": WebScraper.price_per_sqft,
        "Lot Size (sqft)": WebScraper.lot_size,
        "Parking": WebScraper.parking,
        "Down Payment (Fraction)": float(
            f"{UserValues.down_payment_percent:.2f}"
        ),
        "Fix Up Cost ($)": UserValues.fix_up_cost,
        "Loan ($)": int(PropertyInfo.loan),
        "Interest Rate (Fraction)": float(f"{WebScraper.interest_rate:.4f}"),
        "Loan Length (Years)": UserValues.years,
        "Mortgage Payment [Monthly] ($)": float(
            f"{-PropertyInfo.amortization_table['Monthly Payment'][0]:.2f}"
        ),
        "Property Taxes [Monthly] ($)": float(
            f"{PropertyInfo.property_taxes_monthly:.2f}"
        ),
        "Insurance [Monthly] ($)": float(
            f"{-PropertyInfo.insurance_cost / 12:.2f}"
        ),
        "Units": WebScraper.num_units,
        "Rent Per Unit ($)": WebScraper.rent_per_unit,
        "Vacancy (Fraction)": float(f"{UserValues.vacancy_percent:.2f}")
    }

    # This is getting the wrong estimations and I can't figure out why.
    # Not necessary to the program.
    PropertyInfo.estimations = {'?': '???'}
    # for key in WebScraper.found:
    #     found, value = WebScraper.found[key][0], WebScraper.found[key][1]
    #     if not found:
    #         PropertyInfo.estimations[key] = value

    if save_to_file:
        save_analysis()

    return True


def basic_calculations() -> None:
    """Basic calculations necessary module wide"""

    PropertyInfo.down_payment = \
        WebScraper.price * UserValues.down_payment_percent
    PropertyInfo.loan = WebScraper.price - PropertyInfo.down_payment
    PropertyInfo.interest_rate_monthly = WebScraper.interest_rate / 12
    PropertyInfo.months = UserValues.years * 12
    PropertyInfo.property_taxes_monthly = WebScraper.property_taxes / 12


def get_property_key() -> str:
    """Get key used to hash different properties"""
    return f"https://www.zillow.com/homedetails/{get_url().split('/')[-2]}/"


def mortgage_amortization() -> dict:
    """Returns amortization table for given args.
    If no args, defaults to constants in calculations.py

    Table includes: 'Period', 'Monthly Payment', 'Principal Payment',
    'Interest Payment', 'Loan Balance', and 'Loan Constant'
    """

    period = 1
    monthly_payment = npf.pmt(PropertyInfo.interest_rate_monthly,
                              PropertyInfo.months, PropertyInfo.loan
                              )
    monthly_principal = npf.ppmt(PropertyInfo.interest_rate_monthly, period,
                                 PropertyInfo.months, PropertyInfo.loan
                                 )
    monthly_interest = npf.ipmt(PropertyInfo.interest_rate_monthly, period,
                                PropertyInfo.months, PropertyInfo.loan
                                )
    loan_balance = npf.fv(PropertyInfo.interest_rate_monthly, period,
                          monthly_payment, PropertyInfo.loan
                          )

    amortization = {
        'Period': [period], 'Monthly Payment': [monthly_payment],
        'Principal Payment': [monthly_principal],
        'Interest Payment': [monthly_interest],
        'Loan Balance': [loan_balance]
    }

    for i in range(2, PropertyInfo.months + 1):
        period = i
        monthly_principal = npf.ppmt(PropertyInfo.interest_rate_monthly, period,
                                     PropertyInfo.months, PropertyInfo.loan
                                     )
        monthly_interest = npf.ipmt(PropertyInfo.interest_rate_monthly, period,
                                    PropertyInfo.months, PropertyInfo.loan
                                    )
        loan_balance = npf.fv(PropertyInfo.interest_rate_monthly, period,
                              monthly_payment, PropertyInfo.loan
                              )

        amortization['Period'].append(period)
        amortization['Monthly Payment'].append(monthly_payment)
        amortization['Principal Payment'].append(monthly_principal)
        amortization['Interest Payment'].append(monthly_interest)
        amortization['Loan Balance'].append(loan_balance)

    return amortization


def purchase_analysis() -> float:
    """Amount required to purchase the property"""

    closing_cost = PropertyInfo.loan * UserValues.closing_percent

    return PropertyInfo.down_payment + UserValues.fix_up_cost + closing_cost


def income_analysis() -> float:
    """Effective gross income of the property"""

    rent = WebScraper.rent_per_unit * WebScraper.num_units
    gross_potential_income = rent * 12
    vacancy_cost = -(gross_potential_income * UserValues.vacancy_percent)
    effective_gross_income = gross_potential_income + vacancy_cost

    return effective_gross_income


def expenses_analysis() -> float:
    """Cost of owning of the property"""

    effective_gross_income = income_analysis()

    maintenance_cost = -(
            effective_gross_income * UserValues.maintenance_percent)
    management_cost = -(effective_gross_income * UserValues.management_percent)
    property_taxes_cost = -WebScraper.property_taxes
    PropertyInfo.insurance_cost = -(WebScraper.price * 0.00425)
    total_cost = maintenance_cost + management_cost + \
                 property_taxes_cost + PropertyInfo.insurance_cost

    return total_cost


def profit_analysis() -> tuple:
    """Cashflow, net income, and yearly cost of property"""

    effective_gross_income = income_analysis()
    total_cost = expenses_analysis()
    net_operating_income = effective_gross_income + total_cost

    debt_service = PropertyInfo.amortization_table['Monthly Payment'][0] * 12
    cashflow = net_operating_income + debt_service

    yearly_cost = total_cost + debt_service

    return cashflow, net_operating_income, yearly_cost


def depreciation_analysis() -> float:
    """Taxes saved by depreciation of the property"""

    depreciation_short_total = (WebScraper.price + UserValues.fix_up_cost) * \
                               UserValues.depreciation_short_percent
    depreciation_short_yearly = depreciation_short_total / 5

    depreciation_long_total = (WebScraper.price + UserValues.fix_up_cost) * \
                              UserValues.depreciation_long_percent
    depreciation_long_yearly = depreciation_long_total / 27.5

    tax_exposure_decrease = \
        (depreciation_short_yearly + depreciation_long_yearly) * \
        UserValues.tax_bracket

    return tax_exposure_decrease


def returns_analysis() -> dict:
    """Yearly returns of the property along with extra details"""

    capital_required = purchase_analysis()
    cashflow, net_operating_income, yearly_cost = profit_analysis()
    effective_gross_income = income_analysis()
    tax_exposure_decrease = depreciation_analysis()
    principal_paydown = -sum(
        PropertyInfo.amortization_table['Principal Payment'][0:12]
    )
    total_return = cashflow + tax_exposure_decrease + principal_paydown

    return_on_investment_percent = round(total_return / capital_required * 100,
                                         2
                                         )
    c_on_c_return_percent = round(cashflow / capital_required * 100, 2)
    caprate_percent = round(net_operating_income / WebScraper.price * 100, 2)
    cashflow_per_month = cashflow / 12
    max_offer = (
                        (
                                effective_gross_income * 0.75 + -WebScraper.property_taxes - 600) *
                        (0.37 / 0.12)) / \
                (UserValues.closing_percent + UserValues.down_payment_percent) - \
                UserValues.fix_up_cost
    emergency_fund = -yearly_cost / 2 if UserValues.is_first_rental \
        else -yearly_cost / 4

    return_on_investment_string = f"{return_on_investment_percent}%"
    c_on_c_return_string = f"{c_on_c_return_percent}%"
    caprate_string = f"{caprate_percent}%"
    cashflow_per_month_string = f"${cashflow_per_month:.2f}"
    max_offer_string = f"${max_offer:.2f}"
    emergency_fund_string = f"${emergency_fund:.2f}"

    final_returns = {
        'Return On Investment': return_on_investment_string,
        'Cash on Cash Return': c_on_c_return_string,
        'Caprate': caprate_string,
        'Cashflow per month': cashflow_per_month_string,
        'Max Offer (Approximately)': max_offer_string,
        'Emergency Fund (Recommended)': emergency_fund_string
    }

    return final_returns


def write_urls(urls, overwrite=False, search=False, delete=False) -> None:
    """Saves user inputted search URL. Does not preserve order."""

    # Remove ignored urls from urls before saving them.
    # Does not apply if deleting
    if not delete:
        try:
            with open(os.path.join('output', 'ignored_urls.txt')) as txt_file:
                urls_txt = {url.strip() for url in txt_file.readlines()}
            if urls.intersection(urls_txt):
                print(
                    f"{BAD}!!! At least one of the URLs entered is being "
                    f"ignored. They were not added to urls.json... !!!{END}"
                )
            urls.difference_update(urls_txt)
        except FileNotFoundError:
            pass

    if search:
        key = 'Search'
    else:
        key = 'Property'

    if delete:
        try:
            with open(os.path.join('output', 'urls.json')) as json_file:
                urls_json = json.load(json_file)

            # Deletes analysis for soon to be deleted urls
            try:
                with open(os.path.join('output', 'analysis.json')) as json_file:
                    analysis_json = json.load(json_file)

                # Updates the relevant analysis that need to be deleted
                # due to deletion of urls
                if search:
                    for search_url in urls:
                        for url in urls_json[key].get(search_url, []):
                            analysis_json.pop(
                                f"https://www.zillow.com/homedetails/"
                                f"{url.split('/')[-2]}/", None
                            )
                else:
                    for url in urls:
                        analysis_json.pop(
                            f"https://www.zillow.com/homedetails/"
                            f"{url.split('/')[-2]}/", None
                        )
                with open(os.path.join(
                        'output', 'analysis.json'
                ), 'w'
                ) as json_file:
                    json.dump(analysis_json, json_file, indent=4)
            except (FileNotFoundError, json.JSONDecodeError, TypeError):
                pass

            # Check if new urls already in json.
            # Also remove any duplicates in json if any got by.
            values = set(urls_json.setdefault(key, [])).difference(urls)

            # Updates the file with new dict.
            # Note, json doesn't accept set so must convert to list before.
            urls_json[key] = {value: [] for value in values}
            with open(os.path.join('output', 'urls.json'), 'w') as json_file:
                json.dump(urls_json, json_file, indent=4)
            return
        except FileNotFoundError:
            return
        except json.JSONDecodeError:  # When json file is empty.
            return
        except TypeError:  # When json file is not dict.
            return

    # Order of next two blocks matter.
    # May delete analysis when appending URLs if moved.
    if not overwrite:  # This is what appends URLs
        try:
            with open(os.path.join('output', 'urls.json')) as json_file:
                urls_json = json.load(json_file)

            # Check if new urls already in json.
            # Also remove any duplicates in json if any got by.
            values = set(urls_json.setdefault(key, [])).union(urls)

            # Updates the file with new dict.
            # Note, json doesn't accept set so must convert to list before.
            urls_json[key] = {value: [] for value in values}
            with open(os.path.join('output', 'urls.json'), 'w') as json_file:
                json.dump(urls_json, json_file, indent=4)
            return
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            link = {key: {url: [] for url in urls}}
            with open(os.path.join('output', 'urls.json'), 'w') as json_file:
                json.dump(link, json_file, indent=4)
            return

    # Code for overwriting files. Only reached during overwrite.
    try:
        with open(os.path.join('output', 'urls.json')) as json_file:
            urls_json = json.load(json_file)

        # Deletes analysis files that were previously for the urls being deleted
        try:
            with open(os.path.join('output', 'analysis.json')) as json_file:
                analysis_json = json.load(json_file)

            # Take all the previous analyses and remove them.
            # Ignoring the new overwriting ones.
            if search:
                for search_url in urls_json.setdefault(key, {}):
                    if search_url not in urls:
                        for url in urls_json[key].get(search_url, []):
                            analysis_json.pop(
                                f"https://www.zillow.com/homedetails/"
                                f"{url.split('/')[-2]}/", None
                            )
            else:
                for url in urls_json.setdefault(key, {}):
                    if url not in urls:
                        analysis_json.pop(
                            f"https://www.zillow.com/homedetails/"
                            f"{url.split('/')[-2]}/", None
                        )
            with open(os.path.join(
                    'output', 'analysis.json'
            ), 'w'
            ) as json_file:
                json.dump(analysis_json, json_file, indent=4)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            pass

        # Overwrites URLs of Search or Property depending on selection.
        urls_json[key] = {url: [] for url in urls}
        with open(os.path.join('output', 'urls.json'), 'w') as json_file:
            json.dump(urls_json, json_file, indent=4)

    # Overwrites URLs of Search or Property depending on selection.
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        link = {key: {url: [] for url in urls}}
        with open(os.path.join('output', 'urls.json'), 'w') as json_file:
            json.dump(link, json_file, indent=4)


def write_urls_ignore(urls) -> None:
    """Saves urls to ignored_urls.txt"""

    urls_list = [url + "\n" for url in urls]

    with open(os.path.join('output', 'ignored_urls.txt'), 'a') as txt_file:
        txt_file.writelines(urls_list)


def save_analysis() -> None:
    """Saves analysis of property to analyzedProperties.json"""

    key, property_analysis = get_property_analysis()
    write_property_analysis(key, property_analysis)


def get_property_analysis() -> tuple:
    """Gets the data that is eventually written to analysis.json"""

    key = get_property_key()
    property_analysis = {
        key: {
            "Property URL": get_url(property_url=True),
            "Property Taxes URL": get_url(taxes_url=True),
            "Property Info": PropertyInfo.property_info,
            "Analysis": print_analysis(dump=True),
            "Estimations": PropertyInfo.estimations
        }
    }

    return key, property_analysis


def write_property_analysis(key, property_analysis) -> None:
    """Writes the data to analysis.json.
    Only handles a single property. write_property_analyses() for multiple.
    """

    try:
        with open(os.path.join('output', 'analysis.json')) as json_file:
            analysis_json = json.load(json_file)

        if property_analysis[key]["Property Info"]["Price ($)"] \
                != analysis_json.get(key, dict()).get("Property Info", dict()
                                                      ).get("Price ($)", 0):
            analysis_json.update(property_analysis)
            with open(os.path.join('output', 'analysis.json'), 'w'
                      ) as json_file:
                json.dump(analysis_json, json_file, indent=4)
    except (FileNotFoundError, json.JSONDecodeError,
            TypeError):  # Explained in save_urls() above
        with open(os.path.join('output', 'analysis.json'), 'w') as json_file:
            json.dump(property_analysis, json_file, indent=4)


def write_property_analyses(keys, property_analyses) -> None:
    """Writes multiple property analyses to analysis.json"""

    PropertyInfo.new_analysis_list.clear()

    try:
        with open(os.path.join('output', 'analysis.json')) as json_file:
            analysis_json = json.load(json_file)

        # Uses IO buffering to store data in dict,
        # then only writes to file once when everything is done.
        for key, property_analysis in zip(keys, property_analyses):
            if property_analysis[key]["Property Info"]["Price ($)"] \
                    != analysis_json.get(key, dict()) \
                    .get("Property Info", dict()).get("Price ($)", 0):
                analysis_json.update(property_analysis)
                PropertyInfo.new_analysis_list.append(True)

        if any(is_new_analyses()):
            with open(os.path.join('output', 'analysis.json'), 'w'
                      ) as json_file:
                json.dump(analysis_json, json_file, indent=4)

    except (FileNotFoundError, json.JSONDecodeError,
            TypeError):  # Explained in save_urls() above

        PropertyInfo.new_analysis_list.append(True)

        # Creating a dict to store the multiple analyses.
        # Allows writing to file once.
        analysis_json = {}
        for _, property_analysis in zip(keys, property_analyses):
            analysis_json.update(property_analysis)

        with open(os.path.join('output', 'analysis.json'), 'w') as json_file:
            json.dump(analysis_json, json_file, indent=4)


def is_new_analyses() -> list:
    """Used to check if any analysis was updated"""
    return PropertyInfo.new_analysis_list


def print_sql_amortization_table() -> None:
    """Prints the amortization table from the analysis.db file"""

    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print("Amortization Table:")
    print()
    amortization_data = {
        'Period': [], 'Monthly Payment': [],
        'Principal Payment': [], 'Interest Payment': [],
        'Loan Balance': []
    }

    for key, value in PropertyInfo.amortization_table.items():
        for num in value:
            if key == 'Period':
                amortization_data[key].append(num)
            else:
                amortization_data[key].append(f"{num:,.2f}")

    with amortization_table() as (con, cur):
        drop_amortization_table(con, cur)
        create_amortization_table(con, cur)
        add_amortization_data(con, cur, amortization_data)
        print(get_amortization_table(con))

    print()
    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print()


def print_amortization_table() -> None:
    """Prints amortization table to terminal"""

    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print("Amortization Table:")
    print()
    d = {
        'Period': [], 'Monthly Payment': [],
        'Principal Payment': [], 'Interest Payment': [],
        'Loan Balance': []
    }

    for key, value in PropertyInfo.amortization_table.items():
        for num in value:
            if key == 'Period':
                num = f"{num}".center(len(key))
                d[key].append(f"{num}")
            else:
                num = f"{num:,.2f}".center(len(key))
                d[key].append(f"{num}")

    for each_row in zip(
            *([key + " |"] + [val + " |" for val in value] for key, value in
              d.items())
    ):
        print(*each_row, " ")
    print()
    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print()


def print_property_info() -> None:
    """Prints information gathered about the property"""

    print("Info used for calculations:")
    print()
    print("Property Description -", end=' ')
    if WebScraper.description:
        description = WebScraper.description
        max_size = 120
        length = len(description)
        slices = int(length / max_size)

        for i in range(slices):
            print(f"{description[i * max_size: (i + 1) * max_size]}", end='')
            if description[(i + 1) * max_size - 1] != ' ' and \
                    description[(i + 1) * max_size + 1] != ' ':
                print("-")
            else:
                print("")
        else:
            print(f"{description[slices * max_size:]}")
    else:
        print("None")
    print(f"\nParking - {WebScraper.parking}")
    print()
    print(f"Address: {WebScraper.address}")
    print(f"Price: ${WebScraper.price:,}")
    print(f"Year Built: {WebScraper.year}")
    print(f"House Size: {WebScraper.sqft} sqft")
    print(f"Price/sqft: ${WebScraper.price_per_sqft}")
    print(f"Lot Size: {WebScraper.lot_size} sqft")
    print(f"Down Payment: {UserValues.down_payment_percent * 100:.0f}%")
    print(f"Fix Up Cost: ${UserValues.fix_up_cost:,}")
    print(f"Loan: ${int(PropertyInfo.loan):,}")
    print(f"Interest Rate: {WebScraper.interest_rate * 100:.2f}%")
    print(f"Loan Length (Years): {UserValues.years}")
    print(
        f"Mortgage Payment (Monthly): "
        f"${-PropertyInfo.amortization_table['Monthly Payment'][0]:,.2f}"
    )
    print(
        f"Property Taxes (Monthly): ${PropertyInfo.property_taxes_monthly:,.2f}"
    )
    print(f"Insurance (Monthly): ${-PropertyInfo.insurance_cost / 12:,.2f}")
    print(f"Units: {WebScraper.num_units}")
    print(f"Rent Per Unit: ${WebScraper.rent_per_unit:,}")
    print(f"Vacancy: {UserValues.vacancy_percent * 100:.0f}%")
    print()
    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print()


def print_analysis(dump=False) -> any:
    """Prints analysis results to terminal"""

    temp = {}

    if not dump:
        print("Analysis of property:")
        print()

    # Handles printing analysis with color coded results
    # based on how good of a deal it is
    for item in PropertyInfo.analysis:
        value = PropertyInfo.analysis[item]
        is_dollar_sign = True
        color = ""

        if item == 'Return On Investment':
            stripped_val = float(value.rstrip('%'))
            is_dollar_sign = False

            if stripped_val < 12:
                color = BAD
            if 12 <= stripped_val < 20:
                color = OK
            if 20 <= stripped_val < 25:
                color = GOOD
            if stripped_val >= 25:
                color = GREAT

        elif item == 'Cash on Cash Return':
            stripped_val = float(value.rstrip('%'))
            is_dollar_sign = False

            if stripped_val < 8:
                color = BAD
            if 8 <= stripped_val < 10:
                color = OK
            if 10 <= stripped_val < 12:
                color = GOOD
            if stripped_val >= 12:
                color = GREAT

        elif item == 'Caprate':
            stripped_val = float(value.rstrip('%'))
            is_dollar_sign = False

            if stripped_val < 5:
                color = BAD
            if 5 <= stripped_val < 7:
                color = OK
            if 7 <= stripped_val < 8:
                color = GOOD
            if stripped_val >= 8:
                color = GREAT

        elif item == 'Cashflow per month':
            stripped_val = float(value.lstrip('$'))

            if stripped_val < 150:
                color = BAD
            elif 150 <= stripped_val < 300:
                color = OK
            elif 300 <= stripped_val < 500:
                color = GOOD
            elif stripped_val >= 500:
                color = GREAT

        elif item == 'Max Offer (Approximately)':
            stripped_val = float(value.lstrip('$'))

            if stripped_val < WebScraper.price * 0.95:
                color = BAD
            elif WebScraper.price * 0.95 <= stripped_val < \
                    WebScraper.price * 1.05:
                color = OK
            elif WebScraper.price * 1.05 <= stripped_val < \
                    WebScraper.price * 1.1:
                color = GOOD
            elif stripped_val >= WebScraper.price * 1.1:
                color = GREAT
        else:
            stripped_val = float(value.lstrip('$'))

        if dump:
            if is_dollar_sign:
                temp[item] = f"${stripped_val:,.2f}"
            else:
                temp[item] = f"{stripped_val:,}%"
        else:
            if is_dollar_sign:
                print(f"{item}: {color}${stripped_val:,.2f}{END}")
            else:
                print(f"{item}: {color}{stripped_val}%{END}")

    if dump:
        return temp

    if not all([values[0] for values in WebScraper.found.values()]):
        print()
        print(
            f"{BAD}WARNING: THESE ITEMS COULD NOT BE FOUND THUS "
            f"DEFAULTED TO AN ESTIMATE VALUE. THEY MAY BE WRONG.{END}"
        )
        for item, value in WebScraper.found.items():
            if value[0] is False:
                print(f"{OK}{item}: ??? --> {value[1]}{END}")
    print()
    print(
        "----------------------------------------"
        "----------------------------------------"
    )
    print()
