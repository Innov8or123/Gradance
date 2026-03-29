import pandas as pd
import json
import re
import os

def update_co_mapping(xlsx_path, json_path, subject_name="Artificial Intelligence"):
    #check for file 
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            try:
                full_data = json.load(f)
            except json.JSONDecodeError:
                full_data = {"subjects": {}, "co_mappings": {}}
    else:
        full_data = {"subjects": {}, "co_mappings": {}}

    #read file
    df = pd.read_excel(xlsx_path, header=None, engine='xlrd')
    syllabus_rows = df[0].dropna().tolist()

    new_subject_cos = {}
    current_co_id = 0
    current_co_key = ""
    all_subject_keywords = set()

    #parsing of excel cells
    for row in syllabus_rows:
        row = str(row).strip()
        
        #find CO headers
        header_match = re.match(r"(\d+)\.0\s+(.*)", row)
        
        if header_match:
            current_co_id += 1
            current_co_key = f"CO{current_co_id}"
            co_name = header_match.group(2).strip()
            
            new_subject_cos[current_co_key] = {
                "name": co_name,
                "keywords": []
            }
        #clean
        elif current_co_key:
            clean_text = re.sub(r"(?i)Self-learning Topics:|\(SVD\)\.", "", row).strip()
            parts = [p.strip().lower() for p in clean_text.split(',') if p.strip()]
            
            for p in parts:
                p = p.rstrip('.,')
                if p:
                    new_subject_cos[current_co_key]["keywords"].append(p)
                    all_subject_keywords.add(p)

    #preserve the existing data 
    full_data["subjects"][subject_name] = {
        "keywords": sorted(list(all_subject_keywords))
    }
    full_data["co_mappings"][subject_name] = new_subject_cos

    #add and update the json file
    with open(json_path, 'w') as f:
        json.dump(full_data, f, indent=2)
    
    print(f" Successfully updated {json_path}")
    print(f"Added {len(new_subject_cos)} COs to subject: {subject_name}")


#paths
EXCEL_FILE = "/Users/vishruthshetty/Downloads/artificialintelligence.xls"
JSON_FILE = "data/co_mapping.json"

update_co_mapping(EXCEL_FILE, JSON_FILE)