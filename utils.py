import re
import streamlit as st

from collections import defaultdict
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


divider_color = "red"


def remove_emojis(data):
    emoj = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002500-\U00002bef"  # chinese char
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2b55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        re.UNICODE,
    )
    return re.sub(emoj, "", data)


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
        col_1, col_2 = st.columns([4, 1])

        with col_1:
            st.subheader("🧾 &nbsp; Items found", divider=divider_color)
            st.markdown("<br/>", unsafe_allow_html=True)

        with col_2:
            st.metric(
                "Order Total",
                f"£ {items["price"].sum():.2f}",
                delta=None,
                delta_color="normal",
                border=True,
                help="Total amount of the order.",
            )

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


def order_processor(choice: str, html, store_choices: List[str]) -> List[Dict[str, Any]]:
    """
    Optimized order processor that handles multiple store formats
    
    Args:
        choice: Selected store choice
        html: BeautifulSoup HTML object
        store_choices: List of available store choices
        
    Returns:
        List of order items as dictionaries
    """
    DEFAULT_IMAGE = "https://cdn-icons-png.freepik.com/256/13701/13701566.png?semt=ais_hybrid"
    
    def parse_title_and_quantity(title: str) -> tuple[str, int]:
        """Parse title to extract name and quantity"""
        match = re.match(r"(\d+)\s*x\s*(.+)", title)
        if match:
            quantity = int(match.group(1))
            name = match.group(2).strip()
        else:
            quantity = 1
            name = title.strip()
        return name, quantity
    
    def clean_and_convert_price(price_text: str) -> Optional[float]:
        """Clean price text and convert to float"""
        try:
            cleaned = re.sub(r"[^\d.]", "", price_text)
            return float(cleaned) if cleaned else None
        except ValueError:
            logger.warning(f"Could not parse price: {price_text}")
            return None
    
    def safe_get_text(element, default: str = "") -> str:
        """Safely extract text from element"""
        return element.get_text(strip=True) if element else default
    
    def safe_get_attr(element, attr: str, default: str = "") -> str:
        """Safely extract attribute from element"""
        return element.get(attr, default) if element and element.has_attr(attr) else default
    
    # Input validation
    if not html:
        logger.warning("No HTML content provided")
        return []
    
    if not store_choices or choice not in store_choices:
        logger.error(f"Invalid choice: {choice}")
        return []
    
    items = []
    
    try:
        # STORE 1 PROCESSING
        if choice == store_choices[0]:
            # Try primary format first (table rows)
            product_rows = html.find_all("tr", class_="item-row__content")
            
            if product_rows:
                # PRIMARY FORMAT: Table-based layout
                for row in product_rows:
                    try:
                        # Skip unavailable or substituted items
                        row_classes = row.get("class", [])
                        if ("item-row__content--unavailable" in row_classes or 
                            "item-row__content--subs-original" in row_classes):
                            continue
                        
                        # Extract title
                        title_tag = row.find("h4", class_="item-title__label")
                        if not title_tag:
                            continue
                        
                        title = safe_get_text(title_tag)
                        name, quantity = parse_title_and_quantity(title)
                        
                        # Skip if quantity is 0
                        if quantity == 0:
                            continue
                        
                        # Extract weight
                        weight = ""
                        weight_tag = row.find("span", class_="item-title__weight")
                        if weight_tag:
                            weight = safe_get_text(weight_tag)
                        else:
                            # Check for additional quantities
                            extra_quantities = row.find_all("span", class_="item-title__quantity")
                            if extra_quantities:
                                weights = [safe_get_text(w) for w in extra_quantities]
                                weight = ", ".join(filter(None, weights))
                        
                        # Extract price
                        price_tag = row.find("p", class_="item-price__label")
                        if not price_tag:
                            continue
                        
                        price_text = safe_get_text(price_tag)
                        price = clean_and_convert_price(price_text)
                        if price is None:
                            continue
                        
                        # Extract image
                        item_image = row.find("img", class_="item-image__image")
                        image_url = safe_get_attr(item_image, "src", DEFAULT_IMAGE)
                        
                        items.append({
                            "name": name,
                            "quantity": quantity,
                            "weight": weight,
                            "price": price,
                            "image": image_url,
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error processing primary format row: {str(e)}")
                        continue
            
            else:
                # ALTERNATIVE FORMAT: Div-based layout
                product_rows = html.find_all("div", attrs={"data-testid": re.compile(r"^container-")})
                
                for row in product_rows:
                    try:
                        # Extract title and quantity
                        title_tag = row.find("p", string=re.compile(r"\d+\s*x\s+"))
                        if not title_tag:
                            continue
                        
                        title = safe_get_text(title_tag)
                        name, quantity = parse_title_and_quantity(title)
                        
                        if quantity == 0:
                            continue
                        
                        # Extract weight
                        weight = ""
                        detail_tags = row.find_all("p", class_="chakra-text css-0")
                        if len(detail_tags) > 1:
                            weight = safe_get_text(detail_tags[1])
                        
                        # Extract price
                        price_tag = row.find("p", attrs={"data-testid": re.compile(r"^totalCost-")})
                        if not price_tag:
                            continue
                        
                        price_text = safe_get_text(price_tag, "£0.00")
                        price = clean_and_convert_price(price_text)
                        
                        if not price or price == 0:
                            continue
                        
                        # Extract image
                        item_image = row.find("img")
                        image_url = safe_get_attr(item_image, "src", DEFAULT_IMAGE)
                        
                        items.append({
                            "name": name,
                            "quantity": quantity,
                            "weight": weight,
                            "price": price,
                            "image": image_url,
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error processing alternative format row: {str(e)}")
                        continue
        
        # STORE 2 PROCESSING
        elif choice == store_choices[1]:
            # Find the "Rest of your items" section
            rest_of_items_header = html.find("h3", string="Rest of your items")
            rest_container = rest_of_items_header.find_parent("article") if rest_of_items_header else None
            
            if not rest_container:
                logger.warning("No items found in the 'Rest of your items' section")
                return []
            
            # Find product content blocks
            product_blocks = rest_container.find_all(
                "div", class_="styled__ProductContentWrapper-mfe-orders__sc-1hj3has-7"
            )
            
            for block in product_blocks:
                try:
                    # Extract name
                    title_div = block.find("div", {"data-testid": "product-title"})
                    name_tag = title_div.find("a") if title_div else None
                    name = safe_get_text(name_tag)
                    
                    if not name:
                        continue
                    
                    # Extract quantity
                    quantity = 1
                    quantity_tag = block.find("div", class_="styled__SmallOnlyText-mfe-orders__sc-1hj3has-9")
                    if quantity_tag and "Quantity" in quantity_tag.text:
                        try:
                            quantity = int(quantity_tag.text.split(":")[1].strip())
                        except (IndexError, ValueError):
                            pass
                    
                    # Extract weight from image alt text
                    weight = ""
                    img_tag = block.find("img", {"data-testid": "product-image"})
                    if img_tag and img_tag.has_attr("alt"):
                        alt_text = img_tag["alt"].strip()
                        if alt_text:
                            last_word = alt_text.split()[-1]
                            if any(char.isdigit() for char in last_word):
                                weight = last_word
                    
                    # Extract price
                    price_tag = block.find("h4", {"data-testid": "receipt-total-price"})
                    if not price_tag:
                        continue
                    
                    price_text = safe_get_text(price_tag, "£0.00")
                    price = clean_and_convert_price(price_text)
                    if price is None:
                        continue
                    
                    # Extract image
                    image_url = safe_get_attr(img_tag, "src", DEFAULT_IMAGE)
                    
                    items.append({
                        "name": name,
                        "quantity": quantity,
                        "weight": weight,
                        "price": price,
                        "image": image_url,
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing store2 block: {str(e)}")
                    continue
        
        else:
            logger.error(f"Unknown store choice: {choice}")
            return []
        
        logger.info(f"Successfully processed {len(items)} items for {choice}")
        return items
        
    except Exception as e:
        logger.error(f"Critical error processing order: {str(e)}")
        return []