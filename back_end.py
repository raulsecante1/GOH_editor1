import zipfile
import os
import re

start_idx = -1
end_idx = 0

def get_path(savefile, profile = "none"):
    """
    Gets the dynamic path to the .sav file.

    Args:
        savefile (str): Name of the save file (without extension).
        profile (str): Optional profile folder name if there are multiple.

    Returns:
        str: Full path to the .sav file.

    --------not used but kept just in case-----
    """

    parent_dir = r"C:\Users\aragr\Documents\My Games\gates of hell\profiles"
    profile_serie = [f for f in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, f))]
   
    if len(profile_serie) == 1:
        fu_path = os.path.join(parent_dir, profile_serie[0])
    else:
        fu_path = os.path.join(parent_dir, profile)
   
    ful_path = os.path.join(fu_path, "campaign")
   
    full_path = os.path.join(ful_path, savefile + ".sav")

    return os.path.abspath(full_path)

def unzip_sav(path):
    '''
    Unzip the .sav file to get the data
    
    Args:
        path (str): Path of the save file.
    
    Returns:
        str: Full path to the extracted archive path.
    '''
    extract_dir = os.path.splitext(path)[0] + " new"

    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(".sav extracted")
    return (extract_dir)

def read_armory(extract_dir, block_name = "CampaignSquads"):
    '''
    retrive all the squads from the CampaignSquads

    Args:
        text: the whole text from campaign.scn
        block_name (Str) : by default it should be CampaignSquads

    Returns:
        aux_list (list): list of lists of each unit, its stage and its address
        pre_content (str): string of the previous content before the campaignsquads
        nxt_content (str): string of the next content after the campaignsquads
    '''
    global start_idx, end_idx
    with open(extract_dir, "rb") as f:
        text = f.read().decode("utf-8", errors="ignore")

        start_token = f"{{{block_name}"
        start_idx = text.find(start_token)
        if start_idx == -1:
            raise ValueError(f"Block '{block_name}' not found")

        sub_text = text[start_idx:]

        brace_count = 0
        in_block = False

        for i, char in enumerate(sub_text):
            if char == "{":
                brace_count += 1
                in_block = True
            elif char == "}":
                brace_count -= 1
            if in_block and brace_count == 0:
                end_idx = i + 1
                break

        end_idx += start_idx
        aux_in_lines = text[start_idx:end_idx].splitlines()[1:-1]
        in_lines = list(map(lambda s: s.replace("\t\t", ""), aux_in_lines))

        pattern = r'"(.*?)"|\S+'
        aux_list = []
        for line in in_lines:
            aux_line = line.strip('{}')
            pattern = r'"(.*?)"|(\S+)'  # quoted string or non-whitespace
            matches = re.findall(pattern, aux_line)
            aux_list.append([m[0] if m[0] else m[1] for m in matches])

    return aux_list, text[:start_idx], text[end_idx:]

def modify_campaign_scn(scn_path, ordered_units, pre_con, nxt_con, block_name="CampaignSquads"):
    '''
    Write the changes of the order to the campaign.scn

    Args:
        scn_path (str): path to the campaign.scn
        ordered_units (list): list of the ordered squads
        pre_con (str): string of the previous content before the campaignsquads
        nxt_con (str): string of the next content after the campaignsquads
    '''


    # Build new block
    new_block = f"{{{block_name}\n"
    for unit in ordered_units:
        formatted = []
        for i, val in enumerate(unit):
            if i < 2:
                formatted.append(f'"{val}"')
            else:
                formatted.append(val)
        line = "\t\t{" + " ".join(formatted) + "}"
        new_block += line + "\n"
    new_block += "\t}"

    # Replace original block
    new_content = pre_con + new_block + nxt_con

    with open(scn_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("CampaignSquads modified and saved.")

def save_changes(path, mod_path, status_path):
    '''
    Save the changes

    Args:
        Path (str): Path to the .sav file
        Mod_path (str): Path to the modified campaign.scn file
        Status_path (str): Path to the modified status file
    '''
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as new_save:
        new_save.write(mod_path, arcname="campaign.scn")
        new_save.write(status_path, arcname="status")
    print("changes saved")


