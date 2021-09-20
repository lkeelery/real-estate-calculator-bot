import time
from calculations import save_urls
from user import get_url_from_input
from colors_for_print import PrintColors


# Stores the urls from inputs. Gets written to file after add_link() is completed. If was cancelled, it gets cleared.
urls = set()

# Variables that dictate how each option that the user chooses is handled
to_overwrite = is_search = to_delete = False
s_p, search, property_, a_o_d = 's_p', 's', 'p', 'a_o_d'
append, overwrite, delete, cancel, exe = 'a', 'o', 'd', 'c', 'e'

# Used for delaying terminating program so user can read final text
sleep_timer = 1


def quit_program() -> None:
    """Quits programing without saving an data"""

    global to_overwrite, is_search, to_delete
    to_overwrite = is_search = to_delete = False
    urls.clear()

    print_captions(mode=cancel)
    time.sleep(sleep_timer)


def url_is_valid(url) -> bool:
    """Checks if URL is valid"""

    # If not zillow URL, return false
    if url[:23] != 'https://www.zillow.com/' or len(url) <= 29:
        return False

    # If a property URL, return depending on mode user picked.
    if url[:27] == 'https://www.zillow.com/home' and len(url) >= 35:
        if is_search:
            return False
        return True
    else:
        if is_search:
            return True
        return False


def commit_updates_to_file() -> None:
    """Commits changes to file"""

    if urls:
        save_urls(urls, overwrite=to_overwrite, search=is_search, delete=to_delete)

    print_captions(execute=True)
    time.sleep(sleep_timer)


def print_captions(mode=None, e=False, valid=True, received=False, execute=False) -> None:
    """Prints text that tells the user what the programing is doing"""

    BAD, OK, GOOD, GREAT = PrintColors.FAIL, PrintColors.WARNING, PrintColors.OKCYAN, PrintColors.OKGREEN
    END = PrintColors.ENDC

    if mode == 's_p':
        print(f"{GOOD}Do you want to update search URLs 's' or property URLs 'p'? ('c' to cancel):{END}", end=" ")
    elif mode == 'a_o_d':
        print(f"{GOOD}Do you want to append 'a', overwrite 'o', or delete 'd'? ('c' to cancel):{END}", end=" ")
    elif mode == 'a':
        print(f"\n{OK}--- APPEND MODE... URLs in this session will be appended to file! ---{END}")
        if e:
            print(f"{GOOD}Enter another URL to append ('e' to execute changes, 'c' to cancel):{END}", end=" ")
        else:
            print(f"{GOOD}- Enter URL to append ('c' to cancel):{END}", end=" ")
    elif mode == 'o':
        print(f"\n{OK}--- OVERWRITE MODE... URLs before this session will be lost! ---{END}")
        if e:
            print(f"{GOOD}Enter another URL to write ('e' to execute changes, 'c' to cancel):{END}", end=" ")
        else:
            print(f"{GOOD}Enter URL to write ('c' to cancel):{END}", end=" ")
    elif mode == 'd':
        print(f"\n{OK}--- DELETE MODE... URLs in session will be lost! ---{END}")
        if e:
            print(f"{GOOD}Enter another URL to delete ('e' to execute changes, 'c' to cancel):{END}", end=" ")
        else:
            print(f"{GOOD}Enter URL to delete ('c' to cancel):{END}", end=" ")
    elif mode == 'c':
        print(f"\n{BAD}!!! No changes were made! Ending program... !!!{END}")

    elif not valid:
        print(f"\n{BAD}!!! Invalid URL... Try again! (Correct URL for Search/Property?) !!!{END}")
    elif received:
        print(f"\n{GREAT}!!! URL received! !!!{END}")
    elif execute:
        print(f"\n{GREAT}!!! Committed changes to file! Ending program... !!!{END}")


def add_link(mode) -> None:
    """Logic for adding URLs"""

    global is_search

    print_captions(mode=mode)
    search_or_property = input()
    while search_or_property != search and search_or_property != property_ and search_or_property != cancel:
        print_captions(mode=mode)
        search_or_property = input()

    if search_or_property != cancel:
        if search_or_property == search:
            is_search = True
            _choose_options(a_o_d)
        elif search_or_property == property_:
            is_search = False
            _choose_options(a_o_d)
    elif search_or_property == cancel:
        quit_program()
        return


def _choose_options(mode) -> None:
    """Handles the user choosing different options for URLs"""

    global to_overwrite, to_delete

    print_captions(mode=mode)
    append_overwrite_delete = input()
    while append_overwrite_delete != append and append_overwrite_delete != overwrite \
            and append_overwrite_delete != delete and append_overwrite_delete != cancel:
        print_captions(mode=mode)
        append_overwrite_delete = input()

    if append_overwrite_delete != cancel:
        if append_overwrite_delete == append:
            to_overwrite = False
            _get_urls_from_input(append)
        elif append_overwrite_delete == overwrite:
            to_overwrite = True
            _get_urls_from_input(overwrite)
        elif append_overwrite_delete == delete:
            to_delete = True
            _get_urls_from_input(delete)
    elif append_overwrite_delete == cancel:
        quit_program()
        return


def _get_urls_from_input(mode) -> None:
    """Gets URLs from user. Calls functions that adds them to file"""

    print_captions(mode=mode)
    new_url = get_url_from_input()

    if new_url != cancel:
        valid = url_is_valid(new_url)
        while not valid:
            print_captions(valid=False)

            print_captions(mode=mode)
            new_url = get_url_from_input()

            if new_url == cancel:
                quit_program()
                return

            valid = url_is_valid(new_url)

        urls.add(new_url)
        print_captions(received=True)

        print_captions(mode=mode, e=True)
        new_url = get_url_from_input()
        while new_url != cancel:

            if new_url == exe:
                commit_updates_to_file()
                return

            else:
                valid = url_is_valid(new_url)
                while not valid:
                    print_captions(valid=False)

                    print_captions(mode=mode, e=True)
                    new_url = get_url_from_input()

                    if new_url == exe:
                        commit_updates_to_file()
                        return

                    if new_url == cancel:
                        quit_program()
                        return

                    valid = url_is_valid(new_url)

                urls.add(new_url)
                print_captions(received=True)

            print_captions(mode=mode, e=True)
            new_url = get_url_from_input()

        if new_url == cancel:
            quit_program()
            return

    elif new_url == cancel:
        quit_program()
        return


add_link(s_p)
