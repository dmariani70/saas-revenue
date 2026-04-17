from babel import Locale

def get_iso_currencies() -> list[dict]:
    locale = Locale("en")
    return sorted(
        [{"code": code, "name": name}
         for code, name in locale.currencies.items()
         if len(code) == 3 and code.isalpha()],
        key=lambda x: x["code"],
    )
