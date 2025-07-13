import datetime
import pandas as pd

# import mysql.connector  # pip install mysql-connector-python==8.0.31
import sqlite3
import plotly
import plotly.express as px
import json


# Use this function for SQLITE3
def connect_db():
    conn = sqlite3.connect("expense.db")
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS user_login (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(30) NOT NULL, 
        email VARCHAR(30) NOT NULL UNIQUE, password VARCHAR(20) NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS user_expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, pdate DATE NOT 
        NULL, expense VARCHAR(10) NOT NULL, amount INTEGER NOT NULL, pdescription VARCHAR(50), FOREIGN KEY (user_id) 
        REFERENCES user_login(user_id))"""
    )
    conn.commit()
    return conn, cur


# Use this function for mysql
# import mysql.connector  # pip install mysql-connector-python
# def connect_db(host="localhost", user="root", passwd="123456", port=3306, database='expense',
#                auth_plugin='mysql_native_password'):
#     """
#     Connect to database
#     :param host: host
#     :param user: username
#     :param passwd: password
#     :param port: port no
#     :param database: database name
#     :param auth_plugin: plugin
#     :return: connection, cursor
#     """
#     conn = mysql.connector.connect(host=host, user=user, passwd=passwd, port=port, database=database,
#                                    auth_plugin=auth_plugin)
#     cursor = conn.cursor()
#     return conn, cursor


def close_db(connection=None, cursor=None):
    """
    close database connection
    :param connection:
    :param cursor:
    :return: close connection
    """
    cursor.close()
    connection.close()


def execute_query(operation=None, query=None, params=None):
    """
    Execute Query
    :param operation: "search" or "insert"
    :param query: SQL query string with placeholders (?)
    :param params: tuple or list of parameters for the query
    :return: data in case of search query or None for write operations
    """
    connection, cursor = connect_db()
    try:
        if operation == "search":
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            return data
        elif operation == "insert":
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            connection.commit()
            cursor.close()
            connection.close()
            return None
    finally:
        # Ensure resources are closed in case of exceptions
        try:
            cursor.close()
        except:
            pass
        try:
            connection.close()
        except:
            pass


def generate_df(df):
    """
    create new features
    :param df:
    :return: df
    """
    df = df
    df["Date"] = pd.to_datetime(df["Date"])
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Year"] = df["Date"].dt.year
    df["Month_name"] = df["Date"].dt.month_name()
    df["Month"] = df["Date"].dt.month
    df["Day_name"] = df["Date"].dt.day_name()
    df["Day"] = df["Date"].dt.day
    df["Week"] = df["Date"].dt.isocalendar().week
    return df


def num2MB(num):
    """
    num: int, float
    it will return values like thousands(10K), Millions(10M),Billions(1B)
    """
    if num < 1000:
        return int(num)
    if 1000 <= num < 1000000:
        return f'{float("%.2f" % (num / 1000))}K'
    elif 1000000 <= num < 1000000000:
        return f'{float("%.2f" % (num / 1000000))}M'
    else:
        return f'{float("%.2f" % (num / 1000000000))}B'


def top_tiles(df=None):
    """
    Sum of total expenses
    :param df:
    :return: sum
    """
    if df is not None:
        tiles_data = df[["Expense", "Amount"]].groupby("Expense").sum()
        tiles = {"Earning": 0, "Investment": 0, "Saving": 0, "Spend": 0}
        for i in list(tiles_data.index):
            try:
                tiles[i] = num2MB(tiles_data.loc[i][0])
            except:
                pass
        return tiles["Earning"], tiles["Spend"], tiles["Investment"], tiles["Saving"]
    return


def generate_Graph(df=None):
    if df is None or df.empty:
        return None

    if not {"Expense", "Amount", "Note", "Date"}.issubset(df.columns):
        return None

    try:
        # Bar Chart
        bar_data = df.groupby("Expense")[["Amount"]].sum().reset_index()

        bar = px.bar(
            data_frame=bar_data,
            x="Expense",
            y="Amount",
            color="Expense",
            template="plotly_dark",
            labels={"Expense": "Expense", "Amount": "Amount"},
            height=287,
        )
        bar.update(layout_showlegend=False)
        bar.update_layout(
            margin=dict(l=2, r=2, t=60, b=2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        bar.update_xaxes(
            title_text="Expense",
            tickfont=dict(color="#222"),
            title_font=dict(color="#222"),
        )
        bar.update_yaxes(
            title_text="Amount",
            tickfont=dict(color="#222"),
            title_font=dict(color="#222"),
        )
        # Stacked Bar Chart
        s = df.groupby(["Note", "Expense"])[["Amount"]].sum().reset_index()
        stack = px.bar(
            s,
            x="Note",
            y="Amount",
            color="Expense",
            barmode="stack",
            template="plotly_dark",
            labels={"x": "Category", "y": "Balance (₹)"},
            height=290,
        )
        stack.update(layout_showlegend=False)
        stack.update_xaxes(tickangle=45)
        stack.update_layout(
            margin=dict(l=2, r=2, t=60, b=2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        stack.update_xaxes(
            title_text="Note",
            tickfont=dict(color="#222"),
            title_font=dict(color="#222"),
        )
        stack.update_yaxes(
            title_text="Amount",
            tickfont=dict(color="#222"),
            title_font=dict(color="#222"),
        )
        # Line Chart
        line = px.line(
            df, x="Date", y="Amount", color="Expense", template="plotly_dark"
        )
        line.update_xaxes(rangeslider_visible=True)
        line.update_layout(
            title_text="Track Record",
            title_x=0.0,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            margin=dict(l=2, r=2, t=30, b=2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        # Sunburst Chart
        pie = px.sunburst(
            df,
            path=["Expense", "Note"],
            values="Amount",
            height=280,
            template="plotly_dark",
        )
        pie.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        return (
            json.dumps(bar, cls=plotly.utils.PlotlyJSONEncoder),
            json.dumps(pie, cls=plotly.utils.PlotlyJSONEncoder),
            json.dumps(line, cls=plotly.utils.PlotlyJSONEncoder),
            json.dumps(stack, cls=plotly.utils.PlotlyJSONEncoder),
        )

    except Exception as e:
        # print("generate_Graph failed:", e)
        return None, None, None, None


def makePieChart(
    df=None,
    expense="Earning",
    names="Note",
    values="Amount",
    hole=0.5,
    color_discrete_sequence=None,
    size=300,
    textposition="inside",
    textinfo="percent+label",
    margin=2,
):
    # Use a vibrant, contrasting Material palette by default
    if color_discrete_sequence is None:
        color_discrete_sequence = [
            "#42a5f5",  # blue
            "#66bb6a",  # green
            "#ffa726",  # orange
            "#ab47bc",  # purple
            "#ef5350",  # red
            "#26c6da",  # teal
        ]

    try:
        dff = df[df["Expense"] == expense]
        if dff.empty or names not in dff.columns or values not in dff.columns:
            return None

        fig = px.pie(
            dff,
            names=names,
            values=values,
            hole=hole,
            color_discrete_sequence=color_discrete_sequence,
            height=size,
            width=size,
        )
        fig.update_traces(
            textposition=textposition,
            textinfo=textinfo,
            textfont_size=14,
            marker=dict(line=dict(color="#fff", width=2)),
        )
        fig.update_layout(
            margin=dict(l=margin, r=margin, t=margin, b=margin),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            annotations=[
                dict(
                    text=expense,
                    y=0.5,
                    font_size=16,
                    font_color="#0b2c38",
                    showarrow=False,
                )
            ],
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    except Exception as e:
        # print("makePieChart failed:", e)
        return None


def get_monthly_data(df, year=datetime.datetime.today().year, res="int"):
    """
    Prepare last 3 months of categorized expense data.

    :param df: DataFrame with 'Expense', 'Amount', 'Month', 'Year'
    :param year: Year to filter
    :param res: "int" or "str" format for values
    :return: list of dictionaries, one per month
    """
    if df is None or df.empty or "Year" not in df.columns or "Month" not in df.columns:
        return []

    if year not in df["Year"].unique():
        return []

    # Filter data for the given year
    d_year = df[df["Year"] == year][["Expense", "Amount", "Month"]]
    d_month = d_year.groupby("Month")
    recent_months = sorted(d_month.groups.keys(), reverse=True)[:3]

    rows = []
    for month in recent_months:
        grouped = (
            d_month.get_group(month).groupby("Expense")[["Amount"]].sum().reset_index()
        )
        for _, row in grouped.iterrows():
            rows.append(
                {"Expense": row["Expense"], "Amount": row["Amount"], "Month": month}
            )

    temp = pd.DataFrame(rows)

    # Month number to name map
    month_name = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }

    result = []
    for month in recent_months:
        m_data = temp[temp["Month"] == month]
        summary = {"Month": month_name.get(month, str(month))}
        for _, row in m_data.iterrows():
            if res == "int":
                summary[row["Expense"]] = int(row["Amount"])
            else:
                summary[row["Expense"]] = num2MB(int(row["Amount"]))
        result.append(summary)

    return result


def sort_summary(df):
    """
    Generate data for cards like highest earning month, average income/spending/saving/investing.
    :param df: DataFrame (must include columns created by generate_df)
    :return: list of summary dictionaries
    """
    if df is None or df.empty:
        return []

    datas = []

    # Highest monthly earning
    try:
        earning_df = df[df["Expense"] == "Earning"]
        if not earning_df.empty:
            grouped = earning_df.groupby(["Year", "Month_name"]).sum(numeric_only=True)[
                "Amount"
            ]
            top_month = grouped.idxmax()
            amount = grouped.max()
            datas.append(
                {
                    "head": "₹" + str(num2MB(amount)),
                    "main": f"{top_month[1]}'{str(top_month[0])[2:]}",
                    "msg": "Highest income in a month",
                }
            )
        else:
            datas.append(
                {
                    "head": "₹0",
                    "main": "N/A",
                    "msg": "No income data",
                }
            )
    except Exception:
        datas.append(
            {
                "head": "₹0",
                "main": "N/A",
                "msg": "Error finding income data",
            }
        )

    # Per day average income
    try:
        income_total = df[df["Expense"] == "Earning"]["Amount"].sum()
        unique_days = df["Date"].nunique()
        avg_income = income_total / unique_days if unique_days > 0 else 0
        datas.append(
            {
                "head": "Income",
                "main": "₹" + str(num2MB(avg_income)),
                "msg": "You earn everyday",
            }
        )
    except Exception:
        datas.append(
            {
                "head": "Income",
                "main": "₹0",
                "msg": "Data missing",
            }
        )

    # Weekly average saving
    try:
        saving_df = df[df["Expense"] == "Saving"]
        if not saving_df.empty:
            avg_weekly_saving = saving_df.groupby("Week")["Amount"].mean().mean()
            datas.append(
                {
                    "head": "Saving",
                    "main": "₹" + str(num2MB(avg_weekly_saving)),
                    "msg": "You save every week",
                }
            )
    except Exception:
        datas.append(
            {
                "head": "Saving",
                "main": "₹0",
                "msg": "No weekly savings",
            }
        )

    # Monthly spending %
    try:
        monthly_earning = (
            df[df["Expense"] == "Earning"].groupby("Month")["Amount"].sum().mean()
        )
        monthly_spend = (
            df[df["Expense"] == "Spend"].groupby("Month")["Amount"].sum().mean()
        )
        if monthly_earning > 0:
            spend_pct = round((monthly_spend / monthly_earning) * 100, 2)
        else:
            spend_pct = 0
        datas.append(
            {
                "head": "Spend",
                "main": f"{spend_pct}%",
                "msg": "You spend every month",
            }
        )
    except Exception:
        datas.append(
            {
                "head": "Spend",
                "main": "0%",
                "msg": "Spend data unavailable",
            }
        )

    # Per minute investment
    try:
        invest_per_min = df[df["Expense"] == "Investment"].groupby("Day")[
            "Amount"
        ].sum().mean() / (24 * 60)
        datas.append(
            {
                "head": "Invest",
                "main": f"₹{round(invest_per_min, 2)}",
                "msg": "You invest every minute",
            }
        )
    except Exception:
        datas.append(
            {
                "head": "Invest",
                "main": "₹0",
                "msg": "No investment data",
            }
        )

    return datas


def expense_goal(df):
    """
    Compare current vs previous month for each expense type.
    :param df: DataFrame
    :return: list of dictionaries showing increase/decrease
    """
    if df is None or df.empty:
        return []

    try:
        monthly_data = get_monthly_data(df, res="int")
        if len(monthly_data) < 2:
            return []

        current = monthly_data[0]
        previous = monthly_data[1]
        expense_types = ["Earning", "Spend", "Investment", "Saving"]

        goals = []
        for exp in expense_types:
            val_curr = current.get(exp, 0)
            val_prev = previous.get(exp, 1)  # avoid division by zero
            diff = val_curr - val_prev
            percent = round((diff / val_prev) * 100, 1) if val_prev != 0 else 0

            goals.append(
                {
                    "type": exp,
                    "status": "increased" if percent > 0 else "decreased",
                    "percent": abs(percent),
                    "value": "₹" + num2MB(val_curr),
                }
            )
        return goals

    except Exception:
        return []


# --------------- Analysis -----------------


def meraPie(
    df=None,
    names=None,
    values=None,
    color=None,
    width=None,
    height=None,
    hole=None,
    hole_text=None,
    margin=None,
    hole_font=10,
):
    fig = px.pie(
        data_frame=df,
        names=names,
        values=values,
        color=color,
        hole=hole,
        width=340,
        height=340,
        color_discrete_sequence=[
            "#42a5f5",
            "#66bb6a",
            "#ffa726",
            "#ab47bc",
            "#ef5350",
            "#26c6da",
        ],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=14,
        marker=dict(line=dict(color="#fff", width=2)),
    )
    fig.update_layout(
        annotations=[
            dict(
                text=hole_text,
                y=0.5,
                font_size=hole_font,
                font_color="#0b2c38",
                showarrow=False,
            )
        ],
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
        showlegend=False,
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def meraBarChart(
    df=None,
    x=None,
    y=None,
    color=None,
    x_label=None,
    y_label=None,
    height=None,
    width=None,
    show_legend=False,
    show_xtick=True,
    show_ytick=True,
    x_tickangle=0,
    y_tickangle=0,
    barmode="relative",
):
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        return None

    try:
        bar = px.bar(
            data_frame=df,
            x=x,
            y=y,
            color=color,
            barmode=barmode,
            labels={x: x_label or x, y: y_label or y},
            height=height,
            width=width,
            color_discrete_sequence=[
                "#42a5f5",
                "#66bb6a",
                "#ffa726",
                "#ab47bc",
                "#ef5350",
                "#26c6da",
            ],
        )
        bar.update(layout_showlegend=show_legend)
        bar.update_layout(
            margin=dict(l=2, r=2, t=2, b=2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#0b2c38",
        )
        bar.update_layout(
            xaxis=dict(
                showticklabels=show_xtick,
                tickangle=x_tickangle,
                title_font=dict(color="#0b2c38"),
                tickfont=dict(color="#0b2c38"),
                gridcolor="rgba(0,0,0,0.08)",
            ),
            yaxis=dict(
                showticklabels=show_ytick,
                tickangle=y_tickangle,
                title_font=dict(color="#0b2c38"),
                tickfont=dict(color="#0b2c38"),
                gridcolor="rgba(0,0,0,0.08)",
            ),
        )

        return json.dumps(bar, cls=plotly.utils.PlotlyJSONEncoder)

    except Exception as e:
        print("⚠️ meraBarChart failed:", e)
        return None


def meraLine(
    df=None,
    x=None,
    y=None,
    color=None,
    slider=True,
    title=None,
    height=180,
    width=None,
    show_legend=True,
):
    # Line Chart
    line = px.line(
        data_frame=df,
        x=x,
        y=y,
        color=color,
        height=height,
        width=width,
        color_discrete_sequence=[
            "#42a5f5",
            "#66bb6a",
            "#ffa726",
            "#ab47bc",
            "#ef5350",
            "#26c6da",
        ],
    )
    line.update_xaxes(rangeslider_visible=slider)
    line.update(layout_showlegend=show_legend)
    line.update_layout(
        title_text=title,
        title_x=0.0,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#0b2c38"),
        ),
        margin=dict(l=2, r=2, t=2, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
    )
    line.update_xaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    line.update_yaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    return json.dumps(line, cls=plotly.utils.PlotlyJSONEncoder)


def meraScatter(
    df=None,
    x=None,
    y=None,
    color=None,
    size=None,
    slider=True,
    title=None,
    height=180,
    width=None,
    legend=False,
):
    scatter = px.scatter(
        data_frame=df,
        x=x,
        y=y,
        color=color,
        size=size,
        height=height,
        width=width,
        color_discrete_sequence=[
            "#42a5f5",
            "#66bb6a",
            "#ffa726",
            "#ab47bc",
            "#ef5350",
            "#26c6da",
        ],
    )
    scatter.update_xaxes(rangeslider_visible=slider)
    scatter.update(layout_showlegend=legend)
    scatter.update_layout(
        title_text=title,
        title_x=0.5,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=1,
            font=dict(color="#0b2c38"),
        ),
        margin=dict(l=2, r=2, t=2, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
    )
    scatter.update_xaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    scatter.update_yaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    return json.dumps(scatter, cls=plotly.utils.PlotlyJSONEncoder)


def meraHeatmap(
    df=None,
    x=None,
    y=None,
    text_auto=True,
    aspect="auto",
    height=None,
    width=None,
    title=None,
):
    if df is None or x not in df.columns or y not in df.columns:
        return None
    if df[x].nunique() == 0 or df[y].nunique() == 0:
        return None

    cross_data = pd.crosstab(df[x], df[y])
    if cross_data.empty:
        return None

    fig = px.imshow(
        cross_data,
        text_auto=text_auto,
        aspect=aspect,
        height=height,
        width=width,
        color_continuous_scale="Plasma",
    )
    fig.update(layout_showlegend=False)
    fig.update_layout(
        title_text=title,
        title_x=0.5,
        margin=dict(l=2, r=2, t=30, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
    )
    fig.update_xaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
    )
    fig.update_yaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def month_bar(df=None, height=None, width=None):
    t = df.groupby(["Month", "Expense"])["Amount"].sum().reset_index()

    month = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    m = {i + 1: name for i, name in enumerate(month)}
    t["Month"] = t["Month"].apply(lambda x: m[x])

    fig = px.bar(
        t,
        x="Month",
        y="Amount",
        color="Expense",
        text_auto=True,
        height=height,
        width=width,
        color_discrete_sequence=[
            "#42a5f5",
            "#66bb6a",
            "#ffa726",
            "#ab47bc",
            "#ef5350",
            "#26c6da",
        ],
    )
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#0b2c38"),
        ),
        margin=dict(l=2, r=2, t=30, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
    )
    fig.update_xaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    fig.update_yaxes(
        title_font=dict(color="#0b2c38"),
        tickfont=dict(color="#0b2c38"),
        gridcolor="rgba(0,0,0,0.08)",
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def meraSunburst(df=None, height=None, width=None):
    fig = px.sunburst(
        df,
        path=["Year", "Expense", "Note"],
        values="Amount",
        height=height,
        width=width,
        color_discrete_sequence=[
            "#42a5f5",
            "#66bb6a",
            "#ffa726",
            "#ab47bc",
            "#ef5350",
            "#26c6da",
        ],
    )
    fig.update_layout(
        margin=dict(l=1, r=1, t=1, b=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#0b2c38",
    )
    fig.update(layout_showlegend=False)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
