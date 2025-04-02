import re
import streamlit as st

from collections import defaultdict


divider_color = "red"

def remove_emojis(data):
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', data)


def display_item(index, name, weight, quantity, price, image, names):
    col_index, col_image, col_item, col_quantity, col_price, col_bought_by = st.columns(
        [1, 3, 6, 3, 3, 6]
    )
    st.divider()

    special_all = "👥 &nbsp; All"
    # Add "All" option if more than one person
    options = names.copy()
    if len(names) > 1:
        options.insert(0, special_all)  # Insert "All" at the top for visibility

    with col_index:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(
            f"<center style='text-align: center; margin:0; padding:0; opacity:20%;'>{index+1}</center>",
            unsafe_allow_html=True,
        )

    with col_image:
        st.markdown(
            f"""
              <div style="display: flex; justify-content: center; margin:0; padding:0;">
                  <img src="{image}" alt="Item Image"
                      style="
                          width: 70px;
                          border-radius: 25%;
                          background-color: white;
                      "/>
              </div>
              """,
            unsafe_allow_html=True,
        )

    with col_item:
        st.markdown(f"**{name}**")
        st.markdown(
            """<p style="opacity:70%; padding:0; margin:0; ">""" + weight + "</p>",
            unsafe_allow_html=True,
        )

    with col_quantity:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"{quantity}")

    with col_price:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"£ {price:.2f}")

    with col_bought_by:
        selected = st.pills(
            "", options=options, key=f"buyers_{index}", selection_mode="multi"
        )

    if special_all in selected:
        selected = names.copy()

    return selected


def display_order(items, names):
    if not items.empty:
        st.subheader("🧾 &nbsp; Items found", divider=divider_color)
        st.markdown("<br/>", unsafe_allow_html=True)

        # Store who bought what
        assignments = items.to_dict(orient="records")
        
        # read from the row of the dataframe
        for idx, row in items.iterrows():
            buyers = display_item(
                idx,
                row["name"],
                row["weight"],
                row["quantity"],
                row["price"],
                row["image"],
                names,
            )
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
        return split

    else:
        st.info(
            "&nbsp; No items found. Please upload a valid order receipt.",
            icon="ℹ️",
        )
        return "no_order"


def display_split(split, items):
    st.markdown("<br/>", unsafe_allow_html=True)

    if split == "no_order":
        return

    if split:
        st.write("🧾 &nbsp; **Split Summary**")
        st.markdown("<br/>", unsafe_allow_html=True)

        metric_col, split_col = st.columns(2)

        with metric_col:
            sub_col1, sub_col2, sub_col3 = metric_col.columns(3)
            sub_col1.metric(
                label="Total Amount",
                value="£{:.2f}".format(items.price.sum()),
            )
            sub_col2.metric(
                label="Total Assigned",
                value="£{:.2f}".format(sum(split.values())),
            )
            sub_col3.metric(
                label="Total Remaining",
                value="£{:.2f}".format((items.price.sum()) - sum(split.values())),
            )

        with split_col:
            total = sum(split.values())
            for person, amount in split.items():
                name, price, share = split_col.columns([2, 1, 1])

                with name:
                    st.write(f"👤  &nbsp; {person}")

                with price:
                    st.write(f"&nbsp; £ {amount:.2f}")

                with share:
                    st.write(f"&nbsp; {amount/total:.2%}")

                split_col.divider()

    else:
        st.info(
            "&nbsp; No items have been assigned yet. Select who bought what to see the split.",
            icon="ℹ️",
        )

    st.markdown("<br/>", unsafe_allow_html=True)


def order_processor(choice, html, store_choices):
    items = []

    if choice == store_choices[0]:
        # Find product rows
        product_rows = html.find_all("tr", class_="item-row__content")

        for row in product_rows:
            # ignore if the item is unavailable
            if "item-row__content--unavailable" in row["class"]: continue
            
            # ignore if the items has been substituted
            if "item-row__content--subs-original" in row["class"]: continue
            
            # Product name
            title_tag = row.find("h4", class_="item-title__label")
            if not title_tag:
                continue
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

            item_image = row.find("img", class_="item-image__image")
            image_url = item_image["src"] if item_image else "https://cdn-icons-png.freepik.com/256/13701/13701566.png?semt=ais_hybrid"

            items.append(
                {
                    "name": name,
                    "quantity": quantity,
                    "weight": weight,
                    "price": float(price.replace("£", "")),
                    "image": image_url,
                }
            )
    
    elif choice == store_choices[1]:            
        # Find the "Rest of your items" section
        rest_of_items_header = html.find("h3", string="Rest of your items")
        rest_container = rest_of_items_header.find_parent("article") if rest_of_items_header else None

        if not rest_container:
            st.warning("No items found in the 'Rest of your items' section.")
            return []

        # Find product content blocks within this container
        product_blocks = rest_container.find_all("div", class_="styled__ProductContentWrapper-mfe-orders__sc-1hj3has-7")

        items = []
        for block in product_blocks:
            # Name
            title_div = block.find("div", {"data-testid": "product-title"})
            name_tag = title_div.find("a") if title_div else None
            name = name_tag.get_text(strip=True) if name_tag else ""

            # Quantity
            quantity = 1
            quantity_tag = block.find("div", class_="styled__SmallOnlyText-mfe-orders__sc-1hj3has-9")
            if quantity_tag and "Quantity" in quantity_tag.text:
                try:
                    quantity = int(quantity_tag.text.split(":")[1].strip())
                except:
                    pass

            # Image
            img_tag = block.find("img", {"data-testid": "product-image"})
            image_url = img_tag["src"] if img_tag else ""

            # Weight (optional, from image alt)
            weight = ""
            if img_tag and img_tag.has_attr("alt"):
                last_word = img_tag["alt"].strip().split()[-1]
                if any(char.isdigit() for char in last_word):
                    weight = last_word

            # Price
            price_tag = block.find("h4", {"data-testid": "receipt-total-price"})
            price = price_tag.get_text(strip=True) if price_tag else "£0.00"

            items.append({
                "name": name,
                "quantity": quantity,
                "weight": weight,
                "price": float(price.replace("£", "")),
                "image": image_url,
            })


    return items
