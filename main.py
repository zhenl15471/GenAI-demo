import streamlit as st
import pandas as pd
from file_processing import process_pdf, log_file_details, update_review_status,display_output_table
import io


# Set page configuration with an icon and layout
st.set_page_config(page_title="Gen AI Demo", page_icon="📄", layout="wide")

# Display the title at the top of the page
st.markdown("""
    <h1 style='text-align: center; margin-top: 25px;'>Summary of File Processed</h1>
    <br>
    """, unsafe_allow_html=True)

# Use a theme for consistent styling
st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .spacer {
        margin-top: 50px;  /* Adjust the space size as needed */
    }
    </style>
    <div class="spacer"></div>
    """, unsafe_allow_html=True)



# Streamlit app
def run_app():

        # Initialize session states if they do not exist
    if 'file_logs' not in st.session_state:
        st.session_state.file_logs = pd.DataFrame(columns=["File Name", "Processed Date", "File Type", "Data Processed", "Review Pending"])
    if 'processing_finished' not in st.session_state:
        st.session_state.processing_finished = False
    if 'show_output_table' not in st.session_state:
        st.session_state.show_output_table = False
    if 'output_df' not in st.session_state:
        st.session_state.output_df = pd.DataFrame()
    if 'show_review_button' not in st.session_state:
        st.session_state.show_review_button = False
    if 'show_download_buttons' not in st.session_state:
        st.session_state.show_download_buttons = False
    if 'pdf_file_name' not in st.session_state:  # Initialize the pdf_file_name variable
        st.session_state.pdf_file_name = ""
          # Initialize selected_file in session state if not present
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = ""

  

    # Calculate the counts for "Files received", "Files processed", and "Files pending review"
    files_received_count = len(st.session_state.file_logs)
    files_processed_count = st.session_state.file_logs['Data Processed'].value_counts().get('Yes', 0)
    files_pending_review_count = st.session_state.file_logs['Review Pending'].value_counts().get('Yes', 0)

    # Display the counts above the log dataframe
    st.markdown(f"Files received: {files_received_count} | Files processed: {files_processed_count} | Files pending review: {files_pending_review_count}")

    custom_css = """
    <style>
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            min-width: 400px;
            width: 100%;
        }
        .styled-table th,
        .styled-table td {
            border: 1px solid #dddddd;
            padding: 12px 15px;
            text-align: left;
        }
        .styled-table th {
            background-color: #007bff; /* Blue background color */
            color: #ffffff; /* White font color */
        }
        .styled-table tr:nth-child(even) {
            background-color: #f3f3f3;
        }
        .styled-table tr:hover {
            background-color: #f1f1f1;
        }
    </style>
    """

    # Display the custom CSS using st.markdown
    st.markdown(custom_css, unsafe_allow_html=True)

    log_df_html = st.session_state.file_logs.to_html(index=False, classes="styled-table")
        # Display the markdown string using st.markdown
    st.markdown(log_df_html, unsafe_allow_html=True)



    # Section for reviewing files
    st.markdown('<p class="big-font">Upload/ Review Files</p>', unsafe_allow_html=True)
    
    # Input the map file
    mapping_df = pd.read_excel(r"C:\Users\QC683LW\GenAIdemo\Input\Mapping V.0.1.xlsx", sheet_name='Mapping')
    mapping_df = mapping_df[mapping_df['In Scope?'] == 'Y']


    # Upload PDF File
    uploaded_pdf_file = st.sidebar.file_uploader("Upload PDF Loss Run File", type=["pdf"])

    if uploaded_pdf_file is not None:
        if uploaded_pdf_file.name != st.session_state.get("pdf_file_name", ""):
            # Reset the processing_finished flag to allow reprocessing
            st.session_state.processing_finished = False
            st.session_state.show_output_table = False
            st.session_state.show_download_buttons = False
            st.session_state.show_review_button = False

            # Store the file name in a variable
            st.session_state.pdf_file_name = uploaded_pdf_file.name
            # Process the uploaded file
            process_pdf(uploaded_pdf_file, st.session_state.pdf_file_name, mapping_df)
            # Log file details
            log_file_details(st.session_state.pdf_file_name)
            # Indicate that processing is finished
            st.session_state.processing_finished = True
    
    
    if st.session_state.processing_finished:
            if st.button("Process Results", key="process_results"):
                st.session_state.show_review_button = True


    # Dropdown to select the processed file to review   
    if st.session_state.show_review_button:
        processed_files = st.session_state.file_logs[st.session_state.file_logs['Data Processed'] == 'Yes']['File Name'].tolist()
        # Display selectbox with the list of processed files
        st.selectbox("Select a file to review:", [""] + processed_files, key="selected_file")

       
        # Display the output dataframe if a file is selected
    if st.session_state.selected_file:
            # Retrieve the processed DataFrame from the session state using the unique key
            output_key = 'output_' + st.session_state.selected_file
            if output_key in st.session_state:
                output_df = st.session_state[output_key]
                # Update the review status in the logs using the selected file name
                update_review_status(st.session_state.selected_file)
                # Call the display_output_table function to show the table and download options
                display_output_table(output_df)


# Running the Streamlit App
if __name__ == "__main__":
    run_app()

