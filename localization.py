import os
import json
import re
from itertools import islice
from pathlib import Path

def get_name():
    localization_path = r"./localization"
    all_entries = os.listdir(localization_path)
    pattern = re.compile(r'^(msgctxt|msgid|msgstr)\b')
    
    aa_list = []
    for file in all_entries:
        aux_list = []
        path = os.path.join(localization_path, file)
        with open(path, "r", encoding="utf-8") as f:
            for line in islice(f, 3, None):
                if pattern.match(line):
                    aux_list.append(line.strip())

        for i in range(len(aux_list)//3):
            aa_list.append([aux_list[3*i][7:-1].split("/")[-1], aux_list[3*i+1][6+1:-1], aux_list[3*i+2][7+1:-1]])
        for i in range(len(aa_list) - 2, -1, -1):
            if aa_list[i][0] == aa_list[i+1][0]:
                aa_list.pop(i+1)
    print(aa_list[0])

    final_list = []
    portrait_path = r"./portrait_squad"
    portrait_names = [Path(f).stem for f in os.listdir(portrait_path) if os.path.isfile(os.path.join(portrait_path, f))]
    for f in aa_list:
        if f[0] in portrait_names:
            final_list.append(f)
    
    return final_list


def write_in():
    squads = {}
    final_list = get_name()
    for elem in final_list:
        squads[elem[0]] = {"name_cn": elem[2], "name_en": elem[1], "name_es": elem[1], "Cp": 0}
    with open("squads.json", "w", encoding="utf-8") as f:
        json.dump(squads, f, indent=4, ensure_ascii=False)

write_in()
