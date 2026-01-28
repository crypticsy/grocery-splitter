import streamlit as st
from collections import defaultdict
from typing import List, Dict, Union

from .constants import divider_color


def display_item(index: int, name: str, weight: str, quantity: int, price: float, image: str, names: List[str]) -> Dict[str, float]:
    """
    Display a single item with buyer selection and quantity allocation.

    Args:
        index: Item index for unique keys
        name: Item name
        weight: Item weight/size description
        quantity: Number of units
        price: Total price for all units
        image: Image URL
        names: List of people to split between

    Returns:
        Dict mapping person name to quantity allocated (e.g., {"Alice": 2, "Bob": 1})
        For equal splits, returns fractional quantities (e.g., {"Alice": 0.5, "Bob": 0.5})
    """
    col_index, col_image, col_item, col_quantity, col_price, col_bought_by = st.columns(
        [1, 3, 6, 3, 3, 6]
    )

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
            "Bought by",
            options=options,
            key=f"buyers_{index}",
            selection_mode="multi",
            label_visibility="collapsed",
        )

        if special_all in selected:
            selected = names.copy()

        # Return empty dict if no one selected
        if not selected:
            return {}

        # If only one person selected, they get all units
        if len(selected) == 1:
            return {selected[0]: quantity}

        # If quantity is 1 or less, split equally among selected people
        if quantity <= 1:
            share = 1.0 / len(selected)
            st.markdown("<br/>", unsafe_allow_html=True)
            return {person: share for person in selected}

        # Quantity > 1 and multiple people selected: show quantity allocation UI
        allocation = {}

        for i, person in enumerate(selected):
            # Default: distribute evenly, giving remainder to first person
            default_qty = quantity // len(selected)
            if i < quantity % len(selected):
                default_qty += 1

            # Each person on their own row: name + number input
            name_col, input_col = st.columns([2, 1])
            with name_col:
                st.markdown(
                    f"<p style='margin: 0; padding-top: 8px;'>{person}</p>",
                    unsafe_allow_html=True,
                )
            with input_col:
                qty = st.number_input(
                    f"Qty for {person}",
                    min_value=0,
                    max_value=quantity,
                    value=default_qty,
                    step=1,
                    key=f"qty_{index}_{person}",
                    label_visibility="collapsed",
                )
                allocation[person] = qty

        # Show total indicator
        total_allocated = sum(allocation.values())
        if total_allocated == quantity:
            st.markdown(
                f"<p style='color: green; margin: 4px 0;'>✓ {total_allocated}/{quantity}</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='color: orange; margin: 4px 0;'>⚠ {total_allocated}/{quantity}</p>",
                unsafe_allow_html=True,
            )

        # Remove people with 0 allocation
        allocation = {person: qty for person, qty in allocation.items() if qty > 0}

        st.markdown("<br/>", unsafe_allow_html=True)
    return allocation


def display_order(items, names: List[str]) -> Union[Dict[str, float], str]:
    """
    Display all order items and calculate price split.

    Args:
        items: DataFrame of items with columns: name, weight, quantity, price, image
        names: List of people to split between

    Returns:
        Dict mapping person name to total amount owed, or "no_order" if no items
    """
    if not items.empty:
        col_1, col_2 = st.columns([4, 1])

        with col_1:
            st.subheader("🧾 &nbsp; Items found", divider=divider_color)
            st.markdown("<br/>", unsafe_allow_html=True)

        with col_2:
            st.metric(
                "Order Total",
                f"£ {items['price'].sum():.2f}",
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
        
            st.divider()
            st.markdown("<br/>", unsafe_allow_html=True)

        # --- Calculate price split based on quantity allocation ---
        split = defaultdict(float)

        for item in assignments:
            buyers = item["bought_by"]  # Dict: {person: quantity_allocated}
            price = item["price"]

            if buyers:
                # Calculate total allocated quantity
                total_allocated = sum(buyers.values())

                if total_allocated > 0:
                    # Price per unit of allocation
                    price_per_unit = price / total_allocated

                    # Assign cost based on quantity allocation
                    total_assigned = 0.0
                    buyer_list = list(buyers.items())

                    for i, (person, qty_allocated) in enumerate(buyer_list):
                        if i == len(buyer_list) - 1:
                            # Last person gets remaining amount to avoid rounding errors
                            split[person] += round(price - total_assigned, 2)
                        else:
                            person_cost = round(price_per_unit * qty_allocated, 2)
                            split[person] += person_cost
                            total_assigned += person_cost

        return split

    else:
        st.info(
            "&nbsp; No items found. Please upload a valid order receipt.",
            icon="ℹ️",
        )
        return "no_order"


def display_split(split: Union[Dict[str, float], str], items) -> None:
    """
    Display the split summary showing how much each person owes.

    Args:
        split: Dict mapping person name to amount, or "no_order"
        items: DataFrame of items for calculating totals
    """
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
                    if total > 0:
                        st.write(f"&nbsp; {amount/total:.2%}")
                    else:
                        st.write("&nbsp; 0.00%")

                split_col.divider()

    else:
        st.info(
            "&nbsp; No items have been assigned yet. Select who bought what to see the split.",
            icon="ℹ️",
        )

    st.markdown("<br/>", unsafe_allow_html=True)
