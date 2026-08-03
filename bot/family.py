# bot/family.py — Family role definitions and lookup helpers

PARENTS = {
    "dad":  {"username": "TorieRingo", "id": 691976042910580767, "title": "Dad", "role": "Creator"},
    "mom":  {"username": "Nico",       "id": 816504106968940544, "title": "Mom", "role": "Co-Creator"},
}
COUSIN = {
    "cousin_stelle": {"username": "Stelle", "id": 993375226664591390,  "title": "Starry Cousin",  "role": "Purple Star"},
    "cousin_crois":  {"username": "Crois",  "id": 1276054519561846840, "title": "Bread Cousin",   "role": "Croissant"},
    "cousin_hyu":    {"username": "Hyuluk", "id": 1196640036465148035, "title": "Curious Cousin", "role": "Curiosity"},
    "cousin_mimi":   {"username": "Mimi",   "id": 1076407798809776138, "title": "Serious Cousin", "role": "Sekai"},
}
UNCLE = {
    "uncle_caco": {"username": "Cacolate", "id": 397563581111205892,  "title": "Goated Uncle",   "role": "Purple Star"},
    "uncle_vari": {"username": "Vari",     "id": 1213763202173632555, "title": "Baguette Uncle", "role": "Teto Kasane"},
}
SISTER = {
    "sister_abby": {"username": "Abby", "id": 1401144000311857316, "title": "AI Sister",     "role": "Cheesy AI"},
    "sister_kde":  {"username": "Kde",  "id": 1278625221078683670, "title": "Yearner Sister", "role": "KDE Plasma"},
    "sister_kio":  {"username": "Kio",  "id": 1477371709849075943, "title": "Singer Sister",  "role": "Singer"},
}
BROTHER_IN_LAW = {
    "broinlaw_haru": {"username": "Haru", "id": 800304284541124638, "title": "Brother in Law", "role": "In Law"},
}

_ID_TO_ROLE:   dict[int, str] = {}
_NAME_TO_ROLE: dict[str, str] = {}

for _group in (PARENTS, COUSIN, UNCLE, SISTER, BROTHER_IN_LAW):
    for _key, _data in _group.items():
        _ID_TO_ROLE[_data["id"]]                = _key
        _NAME_TO_ROLE[_data["username"].lower()] = _key


def get_role(user) -> str | None:
    return _ID_TO_ROLE.get(user.id) or _NAME_TO_ROLE.get(str(user.name).lower())

def get_parent_role(user)  -> str | None: r = get_role(user); return r if r in PARENTS        else None
def get_cousin_role(user)  -> str | None: r = get_role(user); return r if r in COUSIN         else None
def get_uncle_role(user)   -> str | None: r = get_role(user); return r if r in UNCLE          else None
def get_sister_role(user)  -> str | None: r = get_role(user); return r if r in SISTER         else None
def get_brother_role(user) -> str | None: r = get_role(user); return r if r in BROTHER_IN_LAW else None
