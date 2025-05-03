import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.title("GFS Data Viewer")

try:
    # Load CSV
    df = pd.read_csv("Merged.csv")
    st.success("CSV loaded successfully!")

    # Avoid displaying available columns
    # st.write("Available columns:", list(df.columns))
    
    # Clean up the 'Item Description' column by trimming any leading/trailing spaces
    df['Item Description'] = df['Item Description'].str.strip()

    # Clean the 'Item Number' column as well to ensure proper matching
    df['Item Number'] = df['Item Number'].astype(str).str.strip()

    if 'df' in locals():
        st.header("Summary View")

        bad_items = []
        no_change_items = []  # New list for items with no price change
        graphs = []

        # Process all items
        grouped = df.groupby(['Item Number', 'Item Description'])

        for (item_num, item_desc), group in grouped:
            group = group.drop(columns=['Item Number', 'Item Description'], errors='ignore')
            group = group.T  # Transpose so dates are the index
            group.columns = ['Price']
            group['Price'] = pd.to_numeric(group['Price'], errors='coerce')
            group = group.dropna()
            group = group[group['Price'] > 0]

            if group.shape[0] < 2:
                bad_items.append(f"{item_desc} ({item_num})")
                continue

            price_change = (group['Price'].iloc[-1] - group['Price'].iloc[0]) / group['Price'].iloc[0]

            if price_change == 0:
                no_change_items.append(f"{item_desc} ({item_num})")
                continue

            graphs.append({
                'item': f"{item_desc} ({item_num})",
                'data': group,
                'delta': price_change
            })

        # Sort by greatest price increase
        graphs.sort(key=lambda x: x['delta'], reverse=True)

        if graphs:
            # Top item in full width
            top = graphs[0]
            st.subheader(f"Top Increasing Item: {top['item']}")
            fig = px.bar(
                x=top['data'].index,
                y=top['data']['Price'],
                labels={'x': 'Purchase Date', 'y': 'Item Price ($)'},
                title=top['item']
            )
            st.plotly_chart(fig, use_container_width=True)

            # Remaining in 2-column layout
            cols = st.columns(2)
            for i, g in enumerate(graphs[1:], start=1):
                fig = px.bar(
                    x=g['data'].index,
                    y=g['data']['Price'],
                    labels={'x': 'Purchase Date', 'y': 'Item Price ($)'},
                    title=g['item']
                )
                cols[i % 2].plotly_chart(fig, use_container_width=True)

        if bad_items:
            st.warning(f"Items not graphed due to insufficient or invalid data: {', '.join(bad_items)}")
        if no_change_items:
            st.info(f"Items not graphed due to no price change: {', '.join(no_change_items)}")

    # Dropdown to select item by description
    options = df[['Item Number', 'Item Description']].drop_duplicates().set_index('Item Description')
    description = st.selectbox("Select an Item", options.index)

    # Display selected description for debugging
    st.write("Selected Item Description:", description)

    selected_number = options.loc[description, 'Item Number']
    
    # Display selected number for debugging
    st.write("Corresponding Item Number:", selected_number)

    # Get corresponding row
    row = df[df['Item Number'] == selected_number]

    # If multiple rows are returned, choose the first one
    if row.shape[0] > 1:
        row = row.iloc[0]

    # Ensure the row is a pandas Series
    if isinstance(row, pd.DataFrame):
        row = row.squeeze()    

    # Exclude 'Item Number' and 'Item Description' from the row
    data_to_plot = row.drop(labels=['Item Number', 'Item Description'], errors='ignore')

    # Convert to numeric, coercing any non-numeric values to NaN and replacing them with 0
    data_to_plot = pd.to_numeric(data_to_plot, errors='coerce').fillna(0)

    # Check the data before plotting
    if data_to_plot.empty:
        st.warning("No valid numeric data to display for the selected item.")
    else:
        # Filter out None (NaN) and zero values before calculating trend line
        valid_data = data_to_plot[(data_to_plot.notna()) & (data_to_plot != 0)]
        x_values = np.arange(len(valid_data))
        y_values = valid_data.values
        trend_line = np.polyfit(x_values, y_values, 1)
        trend_line_values = np.polyval(trend_line, x_values)

        # Create the bar chart
        fig = px.bar(
            x=data_to_plot.index,
            y=data_to_plot.values,
            labels={'x': 'Purchase Date', 'y': 'Item Price ($)'},
            title=f"{row['Item Description']} ({row['Item Number']}) vs Time"
        )

        # Add trend line as a line trace over the bar chart
        fig.add_trace(go.Scatter(
            x=valid_data.index,
            y=trend_line_values,
            mode='lines',
            name='Trend Line',
            line=dict(color='red', width=2)
        ))

        # Update layout
        fig.update_layout(
            xaxis_tickangle=-45,  # Rotates x-axis labels for better visibility
            xaxis_title='Purchase Date',
            yaxis_title='Item Price ($)'
        )

        # Display the plot
        st.plotly_chart(fig)

        # Display row content under the graph
        st.write("Row content:", row)

except FileNotFoundError:
    st.error("CSV file 'merged.csv' not found. Please make sure it's in the same directory as this script.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")

# Version 1.0.0 - Initial version of the GFS Data Viewer
# Last modified: 2025-04-09