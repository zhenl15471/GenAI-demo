import streamlit as st
import requests
import json



# Function to call the LLM model
def extract_pdf_using_llm(prompt, incubator_endpoint, incubator_key, model, api_version):
    headers = {"api-key": incubator_key}
    query_params = {"api-version": api_version}
    body = {"messages": [{"role": "system", "content": prompt}]}
    full_path = incubator_endpoint + "/openai/deployments/" + model + "/chat/completions"
    response = requests.post(full_path, json=body, headers=headers, params=query_params)
    status_code = response.status_code
    response = response.json()

    if status_code == 200:
        return response["choices"][0]["message"]["content"]
    else:
        st.error(f"Error: {status_code}, Response: {response}")
        return None

# Prepare prompts functions
def prepare_prompt_to_infer_columns(mapping_df):
    prompt_lines = []
    for _, row in mapping_df.iterrows():
        column_name = row.get('Column Name', 'Unknown Column')
        possible_columns = row.get('Possible Source Columns', 'Not provided')
        prompt_line = f"- '{column_name}'\n-- Possible Source Columns: '{possible_columns}'\n"
        prompt_lines.append(prompt_line)
    output_columns = mapping_df['Column Name'].tolist()
    output_header_line = "### List of columns to be mapped:\n" + ", ".join(output_columns)
    full_prompt = output_header_line + "\n\n" + "\n\n".join(prompt_lines)
    return full_prompt

def prepare_prompt_to_infer_unmapped_columns(mapping_df):
    prompt_lines = []
    for _, row in mapping_df.iterrows():
        column_name = row.get('Column Name', 'Unknown Column')
        logic = row.get('Logic', 'Not provided')
        comments = row.get('Comments', 'No additional comments')
        prompt_line = f"- '{column_name}'\n-- Logic (if possible source columns not found in markdown data): '{logic}'\n-- Additional Information: '{comments}'"
        prompt_lines.append(prompt_line)
    output_columns = mapping_df['Column Name'].tolist()
    output_header_line = "### List of columns to be mapped:\n" + ", ".join(output_columns)
    full_prompt = output_header_line + "\n\n" + "\n\n".join(prompt_lines)
    return full_prompt

def prepare_prompt_to_derive_values(mapping_df):
    prompt_lines = []
    for _, row in mapping_df.iterrows():
        column_name = row.get('Column Name', 'Unknown Column')
        logic = row.get('Logic', 'Not provided')
        comments = row.get('Comments', 'No additional comments')
        datatype = row.get('Data Type', 'Text')
        prompt_line = f"- '{column_name}'\n-- Logic: '{logic}'\n-- Comments: '{comments}'\n-- Expected Datatype: '{datatype}'"
        prompt_lines.append(prompt_line)
    output_columns = mapping_df['Column Name'].tolist()
    output_header_line = "### List of columns to be derived:\n" + ", ".join(output_columns)
    full_prompt = output_header_line + "\n\n" + "\n\n".join(prompt_lines)
    return full_prompt
