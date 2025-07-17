# ----------------------------------------------- Relevant Librarires -----------------------------------------------

import streamlit as st
import plistlib
import pandas as pd
from bs4 import BeautifulSoup

from utils import divider_color, remove_emojis, order_processor, display_order, display_split

st.set_page_config(
    page_title="Grocery Splitter",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Remove whitespace from the top of the page and sidebar
st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 3rem;
                    padding-left: 6vw;
                    padding-right: 6vw;
                }
        </style>
        """,
    unsafe_allow_html=True,
)


# ----------------------------------------------- Main Page -----------------------------------------------


st.subheader("Grocery Splitter", divider=divider_color)
st.markdown(
    """
<p style="font-size: 13px; font-weight: 400;">
    Helping with the age-old problem of splitting grocery bills with friends and family.
</p>
""",
    unsafe_allow_html=True,
)
st.markdown("<br/>", unsafe_allow_html=True)

# Create a friends tags
st.write("👥 &nbsp; Add your friends / family to split the bill with:")
raw_names = st.text_input("Enter the names separated by commas ( , )")

names = []
if raw_names:
    st.markdown("<br/>", unsafe_allow_html=True)
    names = [
        remove_emojis(f).strip().capitalize()
        for f in raw_names.split(",")]
    
    st.write(f"Friends / Family found:")
    for f in names:
        st.write(f"👤 &nbsp; {f}")


# Tabs with custom logos
if raw_names:
    # check for duplicates
    if len(names) != len(set(names)):
        st.markdown("<br/>", unsafe_allow_html=True)
        st.warning(
            "&nbsp; &nbsp; &nbsp; Please remove duplicate names from the list. If you want to add a friend with the same name, please add an extra detail like a last name to differentiate them.",
            icon="⚠️",
        )
    
    elif len(names) > 0:
        st.markdown("<br/><br/>", unsafe_allow_html=True)

        stores = [
            "&nbsp; ![Asda Logo](https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Asda_logo.svg/250px-Asda_logo.svg.png) &nbsp; &nbsp;",
            "&nbsp; ![Tesco Logo](https://upload.wikimedia.org/wikipedia/commons/2/23/Tesco_logo.png) &nbsp; &nbsp;",
        ]

        store_choice = st.radio(
            "Select the store to upload your order",
            stores,
            horizontal=True,
        )
        
        st.markdown("<br/>", unsafe_allow_html=True)

        # File uploader
        uploaded_file = st.file_uploader(
            "Upload your file containing the orders from ASDA here",
            type=["html", "webarchive"],
        )

        st.markdown("<br/>", unsafe_allow_html=True)

        # Steps inside a toggle
        with st.expander("&nbsp; &nbsp; How to Download Your Order List", icon="📥"):
            st.divider()
            st.write("Follow the steps below to download your order list from ASDA:")
            steps = [
                "Go to the stores website and log in to your account.",
                "Navigate to the 'Orders' section.",
                "Select the latest order you want to split.",
                "Right-click on the page and select 'Save As'.",
                "Save the file as 'Webpage, HTML only' or 'Web Archive'.",
                "Upload the saved file using the file uploader below",
            ]

            for i, step in enumerate(steps, start=1):
                st.markdown(f"&nbsp; &nbsp; &nbsp; **Step {i}:** &nbsp; {step}")

        if uploaded_file:
            with st.spinner("Processing the uploaded file..."):
                # if the file is a webarchive file
                if uploaded_file.type == "application/x-webarchive":
                    webarchive = plistlib.load(uploaded_file)
                    data = webarchive.get("WebMainResource", {}).get("WebResourceData")

                    # Decode and print
                    html = data.decode("utf-8", errors="replace")
                    soup = BeautifulSoup(html, "html.parser")

                else:
                    soup = BeautifulSoup(uploaded_file, "html.parser")
                
                items = order_processor(store_choice, soup, stores)
                

            if items:
                items = pd.DataFrame(items)
                # ignore duplicate items
                items = items.drop_duplicates(subset=["name", "weight"], keep="first").reset_index(drop=True)
                
                st.markdown("<br/><br/>", unsafe_allow_html=True)
                split = display_order(items, names)
                display_split(split, items)

            else:
                st.info(
                    "&nbsp; No items found. Please upload a valid order receipt.",
                    icon="ℹ️",
                )