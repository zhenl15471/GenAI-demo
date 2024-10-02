import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import pdfplumber
import io
import json
from datetime import datetime
from llm_utils import extract_pdf_using_llm, prepare_prompt_to_infer_columns, prepare_prompt_to_infer_unmapped_columns, prepare_prompt_to_derive_values


# Load environment variables from .env file
load_dotenv()


def log_file_details(file_name):
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    # Check if the file is already in the log and update it
    existing_log = st.session_state.file_logs[st.session_state.file_logs['File Name'] == file_name]
    if not existing_log.empty:
        idx = existing_log.index[0]
        st.session_state.file_logs.at[idx, 'Processed Date'] = current_time
        st.session_state.file_logs.at[idx, 'Review Pending'] = "Yes"
    else:
        # If the file is not in the log, append a new entry
        new_log_entry = pd.DataFrame({
            "File Name": [file_name],
            "Processed Date": [current_time],
            "File Type": ["Loss Run"],
            "Data Processed": ["Yes"],
            "Review Pending": ["Yes"]
        })
        st.session_state.file_logs = pd.concat([st.session_state.file_logs, new_log_entry], ignore_index=True)


# Function to update the review status in the file logs
def update_review_status(file_name):
# Find the index of the file in the logs
    log_index = st.session_state.file_logs.index[st.session_state.file_logs['File Name'] == file_name].tolist()
    if log_index:
        # Update Review Pending to "No" for the found index
        st.session_state.file_logs.at[log_index[0], 'Review Pending'] = "No"



# Function to process the PDF file
def process_pdf(uploaded_pdf_file, pdf_file_name, mapping_df):
    # Convert the uploaded file to a BytesIO object
    pdf_file = io.BytesIO(uploaded_pdf_file.read())

    # Load PDF file and extract tables
    with pdfplumber.open(pdf_file) as pdf:
        all_tables = []
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for table in tables:
                df = pd.DataFrame(table[1:], columns=table[0])
                df['Page Number'] = page_number
                df['File Name'] = pdf_file_name  # Use the stored file name here
                all_tables.append(df)

    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.columns = combined_df.columns.str.replace("\n", " ")
    combined_df = combined_df.replace("\n", " ", regex=True)


    # Prepare Prompt and Call LLM for initial mapping
    prompt_statement = prepare_prompt_to_infer_columns(mapping_df)
    top_5_rows_markdown = combined_df.head(5).to_markdown()

    # LLM API Settings
    incubator_endpoint = os.getenv('INCUBATOR_ENDPOINT')
    incubator_key = os.getenv('INCUBATOR_KEY')

    model = "gpt-4o"
    api_version = "2024-06-01"

    json_structure_prompt = """{
    "0":{ "Mapped_Column1": "source_col1", "Mapped_Column2": "source_col2" },
    "1":{ "Mapped_Column1": "source_col1", "Mapped_Column2": "source_col2" }}"""

    prompt = f'''Task Description:

    You are given a block of markdown data extracted from a PDF. Your objective is to extract key entities from the markdown data and derive the mappings to the output columns.

    For each required output column, map the corresponding source column from the markdown data. If a direct source column is not available, use "NA" in its place.\n\n

    Mappings to Extract:
    Below is the list of output columns that need to be mapped to source columns. Where specific logic or default values are required, they are noted.

    Columns to be Mapped:
    {prompt_statement}\n
    Instructions:
    1. Validate against the markdown data's column headers to check for available source columns.
    2. For each output column, if the corresponding source column is not present, apply the logic provided or fill it with "NA".
    3. Ensure the mapping is returned in the following JSON format with indexes
    {json_structure_prompt}\n
    4. Important! Ensure all JSON objects are indexed starting from 0.
    5. Return only the final JSON output; avoid any explanations or additional comments.
    6. Exclude ```json at the beginning of the response and ``` at the of the response
    7. Validate if the mapped column is present in the markdown data's column headers to ensure valid valid column names are mapped.\n
    Input Data:

    Markdown Data: \n{top_5_rows_markdown}\n\n

    Expected Output:

    A properly formatted JSON with mappings between the columns in the markdown data and the standard output schema. Where a source column is unavailable, "NA" should be used.
    '''

    column_mapping_str = extract_pdf_using_llm(prompt, incubator_endpoint, incubator_key, model, api_version)

    if column_mapping_str:
    
        # Now handle the unmapped columns with prompt_unmapped
        column_mapping = json.loads(column_mapping_str)["0"]
        unmapped_columns = [key for key, value in column_mapping.items() if value == 'NA']
        unmapped_mapping_df = mapping_df[mapping_df['Column Name'].isin(unmapped_columns)]

        prompt_statement_unmapped = prepare_prompt_to_infer_unmapped_columns(unmapped_mapping_df)

        prompt_unmapped = f'''
        Task Description:

        You are an expert in processing and extracting data from loss run files. Your objective is to derive mappings for output columns based on the provided data, where some columns may not have a direct match in the dataset.
        For each required output column, map the corresponding source column from the markdown data.

        Mappings to Extract: Below is the list of output columns that need to be mapped to source columns. In cases where a direct match is not found, use the corresponding logic or comments for deriving mappings.

        Columns to be Mapped:
        {prompt_statement_unmapped}\n

        Instructions:
        1. Apply Logic: If no corresponding source column is present, refer to the Logic and Additional Information below to infer the value and mapping. 
            For instance, if the column name refers to a date, infer it using the provided rules such as 
                "Can be Date of Loss/Date of Event/Loss Date. If loss/claim row related to a year, then enter 01-Jan-YY where YY is the year the row denotes".
        2. Output Format: Ensure the mapping is returned in the following JSON format with indexes: \n{json_structure_prompt}
        3. Indexing: Important! Ensure all JSON objects are indexed starting from 0.
        4. JSON Output Only: Return only the final JSON output; avoid any explanations or additional comments.
        5. Formatting: Exclude any formatting markers like ```json or ``` from the response. Only valid JSON is expected.
        6. Validation: Ensure that any mapped column is a valid column present in the markdown data's headers. If a valid column cannot be found, map the output column to "NA".

        Input Data:

        Markdown Data (first 5 rows for context):

        {top_5_rows_markdown}

        Expected Output:

        A properly formatted JSON with index and mappings between the columns in the markdown data and the standard output schema. 
        If no source column is found, use "NA".
        '''

        unmapped_columns_mapping_str = extract_pdf_using_llm(prompt_unmapped, incubator_endpoint, incubator_key, model, api_version)

        unmapped_columns_mapping = json.loads(unmapped_columns_mapping_str)["0"]


        # Step 5: Combine column mappings and apply to the original dataset
        final_column_mapping = {**column_mapping, **unmapped_columns_mapping}

        # Create a new dataframe with the mapped columns
        mapped_df = pd.DataFrame()

        for column_name, source_column in final_column_mapping.items():
            if source_column != 'NA' and source_column in combined_df.columns:
                mapped_df[column_name] = combined_df[source_column]
            else:
                mapped_df[column_name] = ''  # Leave blank if not mapped

        combined_df_markdown=combined_df.to_markdown()

        mapped_df_markdown = mapped_df.to_markdown()

        if unmapped_columns_mapping_str:
            
            # Handle the blanks now using prompt_blanks logic
            final_column_mapping = {**column_mapping, **json.loads(unmapped_columns_mapping_str)["0"]}

            # Generating a new prompt for blank derivation
            prompt_statement_blanks = prepare_prompt_to_derive_values(mapping_df)

            prompt_blanks= f'''
            Task Description:
            As an Insurance data expert, your goal is to analyze and extract values from loss run files.
            Your objective is to populate missing values in the output columns based on the provided input data and logic.

            Instructions:
            1.Apply Logic:

            For records containing blank values, use the corresponding logic or comments provided to derive the correct values.
            Example: For date columns, follow the rule like "Date of Loss/Event" or use "01-Jan-YY" if only a year is provided.
            For calculated fields, like concatenating client name with a serial date, calculate as instructed.

            2.Data Validation:

            Ensure derived values match the expected format (e.g., dates, numbers, text).
            If values can't be derived:
            Text columns: Leave blank.
            Numeric columns: Set to 0.

            3.Output Format:

            Return the result in a well-formatted markdown table.
            Any additional comments/explanations/examples or formatting markers like ``` should 'NOT' be included.

            4.Handle Missing or Unclear Logic:

            If the provided logic is insufficient, refer to comments for clarification or leave values as instructed.

            Columns to be dervied:
            {prompt_statement_blanks}\n

            Input Data:
            Markdown Data: \n{combined_df_markdown}

            Expected Output:
            A markdown table with derived values, blanks, or 0 for missing data. Do not include comments/explanations/examples.
            '''
            derived_batch_df_str = extract_pdf_using_llm(prompt_blanks, incubator_endpoint, incubator_key, model, api_version)

        if derived_batch_df_str:

            #dervied_batch_df = pd.read_csv(io.StringIO(derived_batch_df_str), sep='|', skipinitialspace=True).dropna(how="all")
            derived_batch_df_raw = pd.read_csv(io.StringIO(derived_batch_df_str), sep='|', skipinitialspace=True)

            # Check if the first row contains hyphens ('---') across all columns and drop it
            if derived_batch_df_raw.iloc[0].str.contains('---').all():
                derived_batch_df = derived_batch_df_raw.drop(index=0).reset_index(drop=True)
            else:
                derived_batch_df = derived_batch_df_raw.copy()

            # Remove 'Unnamed' columns
            derived_batch_df = derived_batch_df.loc[:, ~derived_batch_df.columns.str.contains('^Unnamed')]

            # Strip leading/trailing whitespaces from column names
            derived_batch_df.columns = derived_batch_df.columns.str.strip()

            # Align columns between LLM response and the chunk
            columns_to_update = derived_batch_df.columns.intersection(mapped_df.columns)

            # Filter out the matching columns from the LLM response (derived_batch_df)
            filtered_llm_df = derived_batch_df[columns_to_update]

            # Update the matching columns in mapped_df using the values from derived_batch_df (filtered_llm_df)
            mapped_df.update(filtered_llm_df)


    st.session_state['output_' + pdf_file_name]  = mapped_df  # where processed_df is the DataFrame you want to save
    # Store the output dataframe in session state
    st.session_state.output_df = mapped_df
    # Indicate that processing is finished
    st.session_state.processing_finished = True

    return mapped_df



# Function to display the output table and download options
def display_output_table(output_df):
    st.dataframe(output_df)

    # Dropdown to select the file format
    file_format = st.selectbox("Select file format for download:", ["Select format", "Excel", "JSON","CSV"], key="file_format")

    if file_format == "Excel":
        excel_output = io.BytesIO()
        with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
            st.session_state.output_df.to_excel(writer, index=False)
        excel_output.seek(0)
        st.download_button(
            label="Download as Excel",
            data=excel_output,
            file_name="output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif file_format == "JSON":
        json_output = io.StringIO()
        st.session_state.output_df.to_json(json_output, orient='records', lines=True)
        json_output.seek(0)
        st.download_button(
            label="Download as JSON",
            data=json_output.getvalue(),
            file_name="output.json",
            mime="application/json"
        )
    elif file_format == "CSV":
        csv_output = io.StringIO()
        st.session_state.output_df.to_csv(csv_output, index=False)
        csv_output.seek(0)
        st.download_button(
            label="Download as CSV",
            data=csv_output.getvalue(),
            file_name="output.csv",
            mime="text/csv"
        )







