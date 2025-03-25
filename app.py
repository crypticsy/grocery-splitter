# ----------------------------------------------- Relevant Librarires -----------------------------------------------

import re
import plistlib
import streamlit as st
import pandas as pd

from bs4 import BeautifulSoup
from collections import defaultdict

st.set_page_config(
    page_title="Grocery Splitter",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Remove whitespace from the top of the page and sidebar
st.markdown("""
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 3rem;
                    padding-left: 6vw;
                    padding-right: 6vw;
                }
        </style>
        """, unsafe_allow_html=True)

divider_color = "red"

# ----------------------------------------------- Main Page -----------------------------------------------

# Custom logos for the tabs
asda_logo = "![Asda Logo](https://brandlogos.net/wp-content/uploads/2016/11/asda-logo-preview-400x400.png)"

st.subheader("Grocery Splitter", divider = divider_color)
st.markdown("""
<p style="font-size: 13px; font-weight: 400;">
    Helping with the age-old problem of splitting grocery bills with friends and family.
</p>
""", unsafe_allow_html=True)


st.markdown("<br/>", unsafe_allow_html=True)

# Tabs with custom logos
asda_tab, future_tab = st.tabs([
    f"{asda_logo} &nbsp; **Asda** &nbsp; &nbsp; ",
    f"  "
])


# Helper function to display items
def display_item(index, name, quantity, price, friends):
    col1, col2, col3, col4 = st.columns([3, 1, 1, 3])
    st.divider()
    with col1:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"**{name}**")
    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"{quantity}")
    with col3:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"£{price:.2f}")
    with col4:
        selected = st.pills(
          "",
            options=friends,
            key=f"buyers_{index}",
            selection_mode="multi"
        )
        
    return selected



# ----------------------------------------------- Asda Tab -----------------------------------------------

with asda_tab:
    # Steps inside a toggle
    with st.expander("&nbsp; &nbsp; How to Download Your Order List", icon="📥"):
        st.divider()
        st.write("Follow the steps below to download your order list from ASDA:")
        
        steps = [
            "Go to the ASDA website and log in to your account.",
            "Navigate to the 'Orders' section.",
            "Select the latest order you want to split.",
            "Right-click on the page and select 'Save As'.",
            "Save the file as 'Webpage, Complete' or 'Web Archive'.",
            "Upload the saved file using the file uploader below"
        ]

        for i, step in enumerate(steps, start=1):
            st.markdown(f"&nbsp; &nbsp; &nbsp; **Step {i}:** {step}")

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Create a friends tags
    st.write("👥 &nbsp; Add your friends/family to split the bill with:")
    friends = st.text_input("Enter the names separated by commas")
    
    if friends:
        st.markdown("<br/>", unsafe_allow_html=True)
        friends = [f.strip().capitalize() for f in friends.split(",")]
        st.write(f"Friends/Family Found:")
        for f in friends:
            st.write(f"👤 &nbsp; {f}")
    
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)

    # File uploader
    uploaded_file = st.file_uploader("Upload your file containing the orders from ASDA here", type=["html", "webarchive"])

    if uploaded_file:
        with st.spinner("Processing the uploaded HTML file..."):
          # if the file is a webarchive file
          if uploaded_file.type == "application/x-webarchive":
                webarchive = plistlib.load(uploaded_file)
                data = webarchive.get("WebMainResource", {}).get("WebResourceData")

                # Decode and print
                html = data.decode("utf-8", errors="replace")
                soup = BeautifulSoup(html, 'html.parser')
          else:
              soup = BeautifulSoup(uploaded_file, 'html.parser')
              
          # Find product rows
          product_rows = soup.find_all("tr", class_="item-row__content")

          items = []
          for row in product_rows:
              # Product name
              title_tag = row.find("h4", class_="item-title__label")
              if not title_tag: continue
              title = title_tag.get_text(strip=True)

              # Quantity parsing (e.g. "2 x Something")
              match = re.match(r"(\d+)\s*x\s*(.+)", title)
              if match:
                  quantity = int(match.group(1))
                  name = match.group(2)
              else:
                  quantity = 1
                  name = title

              # Weight or unit size
              weight_tag = row.find("span", class_="item-title__weight")
              weight = weight_tag.get_text(strip=True) if weight_tag else ""

              # Sometimes there are additional quantities (e.g. 0.35kg + 0.37kg)
              extra_quantities = row.find_all("span", class_="item-title__quantity")
              if extra_quantities:
                  weights = [w.get_text(strip=True) for w in extra_quantities]
                  weight = ", ".join(weights)

              # Price
              price_tag = row.find("p", class_="item-price__label")
              price = price_tag.get_text(strip=True) if price_tag else ""

              items.append({
                  "name": name,
                  "quantity": quantity,
                  "weight": weight,
                  "price": price
              })

        if items:
          items = pd.DataFrame(items)
          # ignore duplicate items
          items = items.drop_duplicates(subset=['name', 'weight'], keep='first')

          # convert price to float
          items['price'] = items['price'].str.replace('£', '').astype(float)

          st.markdown("<br/>", unsafe_allow_html=True)
          st.markdown("<br/>", unsafe_allow_html=True)
          st.divider()

          # Store who bought what
          assignments = items.to_dict(orient="records")
          # read from the row of the dataframe
          for idx, row in items.iterrows():
              buyers = display_item(idx, row["name"], row["quantity"], row["price"], friends)
              assignments[idx]["bought_by"] = buyers

          # --- Calculate price split ---
          split = defaultdict(float)

          for item in assignments:
              buyers = item["bought_by"]
              price = item["price"]
              if buyers:
                  n = len(buyers)
                  if n == 1:
                      split[buyers[0]] += price
                  else:
                      share = round(price / n, 2)
                      total_assigned = 0
                      for i, person in enumerate(buyers):
                          if i == n - 1:
                              # Last person gets the remaining amount
                              split[person] += round(price - total_assigned, 2)
                          else:
                              split[person] += share
                              total_assigned += share

          # --- Show Summary Table ---
          st.markdown("---")

          if split:
              st.write("📝 &nbsp; **Split Summary**")
              col1, col2, col3, col4 = st.columns(4)
              with col1:
                  st.markdown("<br/>", unsafe_allow_html=True)
                  st.write("Total Amount: £{:.2f}".format(items.price.sum()))
                  st.write("Total Assigned: £{:.2f}".format(sum(split.values())))
                  st.write("Total Remaining: £{:.2f}".format((items.price.sum()) - sum(split.values())))
              
              with col2:
                  st.markdown("<br/>", unsafe_allow_html=True)
                  for person, amount in split.items():
                      st.write(f"👤  &nbsp; {person}")
              
              with col3:
                  st.markdown("<br/>", unsafe_allow_html=True)
                  for person, amount in split.items():
                      st.write(f"&nbsp; £ {amount:.2f}")
                
              with col4:
                st.markdown("<br/>", unsafe_allow_html=True)
                total = sum(split.values())
                for person, amount in split.items():
                    st.write(f"&nbsp; {amount/total:.2%}")
              
          else:
              st.info("&nbsp; No items have been assigned yet. Select who bought what to see the split.", icon="ℹ️")
              
        else:
          st.warning("No items found in the uploaded file. Please make sure you have uploaded the correct file.", icon="⚠️")